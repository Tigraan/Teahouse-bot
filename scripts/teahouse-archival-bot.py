#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Archival bot v. 2.

Rewritten on 2018-03-18 (Tigraan) for multiple reasons.

First, to comply with some sane code guidelines:
- enforced by Flake8 linter (http://flake8.pycqa.org/en/latest/) on my machine
- uses the GPSG (https://google.github.io/styleguide/pyguide.html)

Second, for a bit of minor refactoring here and there. Outside behaviour should
not be changed although internally-passed types might. Also, let's try to put
all the functions in a single file rather than spreading across multiple
modules.

Third, to add automated unit tests via the doctest module:
https://docs.python.org/3/library/doctest.html#doctest.testmod

We ignore D301 ("a docstring that contains line continuations should be marked
raw") in a few places because doing so breaks the line continuation by
backslash when running the doctest. This is indicated by # noqa: D301 comments.


License:

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
MA 02110-1301, USA.
"""
import collections  # Stackexchange code for list utilities requires this
import datetime  # get current time, convert time string representations
import logging  # warning messages etc.
import requests  # http/https calls (for API calling)


def my_http_headers():
    """Give default user agent and other headers of the script.

    API calls to Mediawiki must include this, see
    https://www.mediawiki.org/wiki/API:Main_page#Identifying_your_client

    No input
    Output is a dict with fields 'User-Agent', 'Accept', 'Connection' and
    'Accept-Encoding'.

    Doctests:
    >>> my_http_headers()['User-Agent']
    'python-requests/2.9.1 - User:Tigraan'

    """
    headers = requests.utils.default_headers()
    def_ua = headers['User-Agent']  # 'python-requests/2.9.1' or similar
    my_ua = '{default} - {my_text}'.format(default=def_ua,
                                           my_text='User:Tigraan')
    headers.update(
        {
            'User-Agent': my_ua,
        }
    )
    return headers


def api_call(parameters, endpoint="https://en.wikipedia.org/w/api.php"):
    """Call the API.

    Original script by  Jtmorgan. User-agent added per
    https://www.mediawiki.org/wiki/API:Main_page#Identifying_your_client

    Inputs: parameters is a dict of API call key/value pairs, endpoint is a
    string (the API endpoint)
    Output: server response in dict format (converted from JSON).

    Doctests:
    >>> api_call({'action': 'query',
    ...           'list': 'blocks',
    ...           'bkprop': 'user',
    ...           'bkstart': '2018-03-03T23:00:00Z',
    ...           'bkend': '2018-03-03T22:00:00Z',
    ...           'bkdir': 'older',
    ...           'bkprop': 'by',
    ...           'format': 'json',
    ...           'formatversion': 2,
    ...           })['query']
    {'blocks': [{'by': 'Floquenbeam'}, {'by': 'ProcseeBot'}, {'by': 'Widr'}]}
    """
    headers = my_http_headers()
    try:
        call = requests.get(endpoint, params=parameters, headers=headers)
        response = call.json()
    except requests.exceptions.RequestException as e:
        logging.error("No useful response was given by the API.\n{}".format(e))
        logging.info("Parameters for failed call: {}".format(parameters))
        response = None
    return response


def whoami():
    """Check the currently logged-in user via the API."""
    rawoutput = api_call({'action': 'query',
                          'meta': 'userinfo',
                          'format': 'json',
                          'formatversion': 2,
                          })
    return rawoutput['query']['userinfo']


def UTC_timestamp_x_days_ago(days_offset=0):
    """Timestamp x days ago in Mediawiki format.

    Input is the number of days that will be substracted from the
    current timestamp.
    Format: cf. https://www.mediawiki.org/wiki/Manual:Timestamp
    """
    current_time = datetime.datetime.utcnow()  # MediaWiki servers use UTC time
    offset = datetime.timedelta(days=-days_offset)
    UTC_time_then = current_time + offset

    timestamp = UTC_time_then.strftime("%Y%m%d%H%M%S")  # MW format
    return timestamp


def safe_list_diff(listbefore, listafter):
    """Find elements that were removed from one list to another.

    Compared to a basic set diff, this takes care of the edge case
    where an element is present multiple times in the larger list
    by removing it altogether (and logging this fact).
    Also, it will raise an AssertionError if the second list is not
    included in the first one (which is expected for an archival diff).

    Warning: because a set diff is used, no order is guaranteed in the output
    list.

    Inputs: lists of strings (names of the threads from page history)
    Output: list of strings

    Doctests:

    Standard use:
    >>> safe_list_diff(['Hello','See you later'],['Hello'])
    ['See you later']

    Duplicate name: will be scrapped from output and log a warning
    >>> safe_list_diff(['Duplicate','Duplicate','Hello', 'Later'],['Hello'])
    ['Later']

    Erroneous input: listafter contains a thread name not in listbefore
    >>> safe_list_diff(['Hello','See you later'],['Hello', 'Abnormal name'])
    Traceback (most recent call last):
      (some traceback)
    AssertionError

    """
    setbefore = set(listbefore)
    setafter = set(listafter)
    # Sanity check that listafter <= listbefore (less threads after archiving)
    assert(not bool(setafter - setbefore))  # True iff. set diff is empty

    # Identify duplicate elements in listbefore and remove them. See
    # https://stackoverflow.com/questions/11236006/identify-duplicate-values-in-a-list-in-python
    duplicate_values = [k for k, v in collections.Counter(listbefore).items()
                        if v > 1]

    for val in duplicate_values:
        logging.warning('Multiple threads that share the same name will be '
                        + 'ignored. The name was '
                        + '"{nameofthread}".'.format(nameofthread=val))

    setdupes = set(duplicate_values)

    # Return threads that were removed and which are not duplicates
    return list(setbefore - setafter - setdupes)


def list_matching(ta, threadscreated):
    """Match string elements from two lists.

    We have on the one hand a list of threads that underwent the last
    archival, and on the other hand a list of created new sections.
    We want to match each of the archived threads to its creation.
    If a thread is matched multiple times or not at all, it must not be
    passed later on, but the event should be logged.

    ta is a list (it has been sanitized upstream to deal
    with name collisions). threadscreated is a list of dict; each dict
    contains at least 'name', the thread title to match.
    The output is a list of dict, the subset of threadscreated
    that have been matched exactly once in threadsarchived.

    Leading and trailing white spaces are discarded during the comparison
    because of some obscure false positive cases identified at test run.

    Inputs: list of strings and list of dict
    Output: list of dict

    Doctests:

    >>> list_matching(['Thread#1','Thread#3'],
    ...               [{'revid' : 1, 'name' : 'Thread#1','user' : 'User#1'},
    ...                {'revid' : 2, 'name' : 'Thread#2','user' : 'User#2'},
    ...                {'revid' : 3, 'name' : 'Thread#3','user' : 'User#3'},
    ...                {'revid' : 4, 'name' : 'Thread#4','user' : 'User#4'}
    ...                ]
    ...               ) == [{'revid': 1, 'name': 'Thread#1','user': 'User#1'},
    ...                     {'revid': 3, 'name': 'Thread#3','user': 'User#3'}]
    True
    """
    output = []

    for i in range(len(ta)):
        cur_str = ta[i].strip()
        matching_indices = [j for j, k in enumerate(threadscreated)
                            if k['name'].strip() == cur_str]

        if len(matching_indices) == 1:  # normal case, one single match
            output.append(threadscreated[matching_indices[0]])
            continue

        # exceptional cases
        if len(matching_indices) == 0:  # no matches
            logging.warning('No matches for the creation of the following'
                            + 'thread: "{tn}"'.format(tn=cur_str))
        else:  # more than one match
            logging.warning('Multiple matches (all will be ignored) for the'
                            + 'creation of the following thread: '
                            + '"{tn}"'.format(tn=cur_str))

    return output


def get_user_info(userlist, infotoget=['groups', 'editcount']):  # noqa: D301
    """Query the API for user info.

    Input:
    - userlist is a list of strings, each string being a username
    - infotoget is the list of user info to return, cf. API documentation
    Output: dict whose keys are exactly the strings from userinfo, each entry
    containing the user information returned by the API for said user.

    Doctests:
    >>> get_user_info(['Jimbo Wales','Sandbox for user warnings']
    ...              ).keys() == {'Jimbo Wales','Sandbox for user warnings'}
    True
    >>> get_user_info(['Jimbo Wales'])['Jimbo Wales']['groups'] ==\
    ['checkuser','founder','oversight','sysop','*','user','autoconfirmed']
    True
    >>> get_user_info(['Nonexisting username'])==\
    {'Nonexisting username': {'missing': True, 'name': 'Nonexisting username'}}
    True
    """
    API_user_string = '|'.join(userlist)
    API_info_string = '|'.join(infotoget)

    params = {'action': 'query',
              'list': 'users',
              'ususers': API_user_string,
              'usprop': API_info_string,
              'format': 'json',
              'formatversion': 2,
              }

    rawoutput = api_call(params)
    # Example (with users Tigraan, Jimbo Wales, Danadan and a dummy) for the
    # API raw output:
    # {'batchcomplete': True,
    # 'query': {'users': [{'invalid': True, 'name': '12.54.29.3'},
    #                  {'editcount': 3529,
    #                   'groups': ['extendedconfirmed',
    #                              '*',
    #                              'user',
    #                              'autoconfirmed'],
    #                   'name': 'Tigraan',
    #                   'userid': 18899359},
    #                  {'editcount': 13105,
    #                   'groups': ['checkuser',
    #                              'founder',
    #                              'oversight',
    #                              'sysop',
    #                              '*',
    #                              'user',
    #                              'autoconfirmed'],
    #                   'name': 'Jimbo Wales',
    #                   'userid': 24},
    #                  {'blockedby': 'Dougweller',
    #                   'blockedbyid': 1304678,
    #                   'blockedtimestamp': '2009-07-02T08:37:58Z',
    #                   'blockexpiry': 'infinity',
    #                   'blockid': 1505586,
    #                   'blockreason':'[[WP:Spam|Spamming]] links to external '
    #                                 'sites: disguising links as news links, '
    #                                 'using multiple identities',
    #                   'editcount': 2,
    #                   'groups': ['*', 'user'],
    #                   'name': 'Dananadan',
    #                   'userid': 9977555},
    #                  {'missing': True,
    #                   'name': 'This username does not exist'}]}}

    # traverse the first two levels
    resultlist = rawoutput['query']['users']

    # transform into a dictionary whose keys are the usernames
    resultdict = dict()
    for entry in resultlist:
        resultdict[entry['name']] = entry
    return resultdict


def get_block_info(userlist):
    """Query the API for block info.

    Input: a list of strings, each string being a username.
    Output: a dictionary of bool such that dict[user] is True if the user
    currently (1) exists and (2) is blocked; dict keys match the input.

    Although get_user_info could be used to check for a current block on logged
    accounts, it is not possible on IP accounts, hence the need for this other
    subfunction. See also
    - https://www.mediawiki.org/wiki/API:Users
    - https://www.mediawiki.org/w/index.php?title=Topic:Tspl9p7oiyzzm19w

    Doctests:
    >>> get_block_info(['Tigraan', '85.17.92.13', 'Nonexisting username']
    ...                ) == {'Tigraan': False,
    ...                      '85.17.92.13': True,
    ...                      'Nonexisting username': False}
    True
    """
    user_string = '|'.join(userlist)

    params = {'action': 'query',
              'list': 'blocks',
              'bkusers': user_string,
              'bkprop': 'user',
              'format': 'json',
              'formatversion': 2,
              }

    rawoutput = api_call(params)

    # traverse the first two levels
    resultlist = rawoutput['query']['blocks']

    # transform result into a dict of bool
    resultdict = dict()
    for user in userlist:
        resultdict[user] = ({'user': user} in resultlist)
    return resultdict


def isnotifiable(users):
    """Check if specified users can be notified.

    Input: list of strings (usernames).
    Output is a dict of booleans, keys match input (True = can be notified).

    This takes care of the policy aspect (who gets notified, in general)
    but NOT of bot exclusion compliance, which must be handled elsewhere.
    For instance pywikibot's scripts should take care of it, per
    https://en.wikipedia.org/wiki/Template:Bots#Implementation

    Current policy is to notify anyone regardless of 'age' (edit count) or
    groups (autoconfirmed etc.) but to not notify blocked users.

    Doctests:
    >>> isnotifiable(['Tigraan', '85.17.92.13', 'Nonexisting username']
    ...              ) == {'Tigraan': True,
    ...                    '85.17.92.13': False,
    ...                    'Nonexisting username': False}
    True
    """
    # Block information
    isblocked = get_block_info(users)

    # Other general user information
    # WARNING! For IP editors, all we get is the 'invalid' key.
    # Do not rely on this to get (e.g.) the edit count of an IP editor!
    userinfo = get_user_info(users, infotoget=['groups'])

    is_notifiable = dict()
    no_notif_str = 'No notification will be sent.'
    unknown_user_str = 'User "{un}" does not seem to exist. ' + no_notif_str
    blocked_user_str = 'User "{un}" is currently blocked. ' + no_notif_str
    for u in users:
        info = userinfo[u]
        # NOTIFICATION POLICY APPLIES HERE

        # If username does not exist (renamed user?) do not notify
        if 'missing' in info:
            is_notifiable[u] = False
            logging.info(unknown_user_str.format(un=u))
            continue

        # Do not notify currently-blocked users
        if isblocked[u]:
            is_notifiable[u] = False
            logging.info(blocked_user_str.format(un=u))
            continue

        # # Further policy options, inactive as of 2018-03-18
        # # Do not notify users with more than x edits
        # maxedits = 1000
        # if info['editcount']>maxedits:
        #     is_notifiable[u] = False
        #     logging.info('User "{un}" performed more than {nedits} edits and will not be notified.'.format(un=u,nedits=maxedits))  # noqa: E501
        #
        # # Do not notify users with the ECP flag
        # if 'extendedconfirmed' in info['groups']:
        #     is_notifiable[u] = False
        #     logging.info('User "{un}" is extended confirmed and will not be notified.'.format(un=u))  # noqa: E501

        # By default, we should notify
        is_notifiable[u] = True

    return is_notifiable


if __name__ == "__main__":
    # Unit test run. See
    # https://docs.python.org/3/library/doctest.html#simple-usage-checking-examples-in-docstrings
    import doctest
    logging.basicConfig(level=logging.ERROR)  # ignore logging warnings
    doctest.testmod()
