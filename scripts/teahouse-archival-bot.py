#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Archival bot v. 2.

2.0 - 2018-03-18 (Tigraan): rewritten for multiple reasons.

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

2.1 - 2018-04-21 (Tigraan): change for PWB compat.

All the various API call stuff must be changed to use OAuth/PWB to log in, so
we just make the big switch to full-PWB.

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
import re  # regular expressions, used to match new section edit summaries

# Pywikibot and associated imports
import pywikibot


# Commands that directly call the API using PWB
def manual_API_call(site, **kwargs):  # noqa: D301
    """Make API request by giving parameters 'by hand'.

    Workaround to make direct API calls, because PWB does not (yet?) support
    all API syntax, including some stuff we need.

    Input:
    - site is an APISite, e.g. obtained by pywikibot.Site(); PWB should be able
    to read pages there (i.e. be logged with the appropriate permissions if
    needed)
    - **kwargs: will be passed unmodified to the API for Site

    Doctests:
    >>> manual_API_call(pywikibot.Site(), action='parse', prop='sections',\
            format='json', formatversion=2,\
            oldid=837538913)['parse']['sections'][:2] ==\
                [{'index': '1', 'anchor': 'Interesting_facts', 'toclevel': 1,\
                  'line': 'Interesting facts','byteoffset': 3282,'level': '2',\
                  'number': '1', 'fromtitle': 'Wikipedia:Teahouse'},\
                 {'index': '2', 'anchor': 'oclc', 'toclevel': 1,\
                  'line': 'oclc', 'byteoffset': 9831, 'number': '2',\
                  'fromtitle': 'Wikipedia:Teahouse', 'level': '2'}]
    True
    """
    request = pywikibot.data.api.Request.create_simple(site, **kwargs)
    return request.submit()


def whoami(site=pywikibot.Site()):
    """Check the currently logged-in user via the API."""
    return site.getuserinfo()['name']


def get_user_info(userlist, site=pywikibot.Site()):  # noqa:D301
    """Query the API for user info.

    Input:
    - userlist is a list of strings, each string being a username

    Output:
    - dict whose keys match the provided userlist; each entry contains user
    information as given by the API

    Doctests:
    >>> get_user_info(['Jimbo Wales','Sandbox for user warnings']
    ...              ).keys() == {'Jimbo Wales','Sandbox for user warnings'}
    True
    >>> get_user_info(['Jimbo Wales'])['Jimbo Wales']['registration']
    '2001-03-27T20:47:31Z'
    >>> get_user_info(['Nonexisting username'])==\
    {'Nonexisting username': {'missing': '', 'name': 'Nonexisting username'}}
    True
    """

    usersgen = site.users(userlist)

    # transform into a dictionary whose keys are the usernames
    resultdict = dict()
    for entry in usersgen:
        resultdict[entry['name']] = entry
    return resultdict


def get_block_info(userlist, site=pywikibot.Site()):
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
    blockgen = site.blocks(users=userlist)

    # transform result into a dict of bool
    resultdict = dict()
    for user in userlist:
        resultdict[user] = False
    for block in blockgen:
        resultdict[block['user']] = True

    return resultdict


def get_sections_from_revid(pageindicator, site=pywikibot.Site()):  # noqa: D301
    """Get list of sections from specific page revision.

    Input:
    - site: 
    - pageindicator: indicates which page to use.
        - if a str, uses the current revision of the page with that title
        - if an int, treated as a revision number via 'oldid' in
          https://www.mediawiki.org/wiki/API:Parsing_wikitext

    Doctests:
    >>> get_sections_from_revid(783718598)[:2]==\
    [{'anchor': 'Request:_World_Cafe',
    ...  'byteoffset': 3329,
    ...  'fromtitle': 'Wikipedia:Teahouse',
    ...  'index': '1',
    ...  'level': '2',
    ...  'line': 'Request: World Cafe',
    ...  'number': '1',
    ...  'toclevel': 1},
    ... {'anchor': 'How_to_publish_my_page',
    ...  'byteoffset': 8292,
    ...  'fromtitle': 'Wikipedia:Teahouse',
    ...  'index': '2',
    ...  'level': '2',
    ...  'line': 'How to publish my page',
    ...  'number': '2',
    ...  'toclevel': 1}
    ... ]
    True
    """
    params = {'action': 'parse',
              'prop': 'sections',
              'format': 'json',
              'formatversion': 2,
              }
    if isinstance(pageindicator, int):
        params['oldid'] = pageindicator
    else:
        params['page'] = pageindicator

    api_call_result = manual_API_call(site, **params)

    # Traverse two levels of the dictionary and return
    return api_call_result['parse']['sections']


def get_revisions_from_api(pagename, oldtimestamp, newtimestamp,
                           maxcontinuenumber=0, continuestring=None,
                           site=pywikibot.Site()):  # noqa: D301
    """Get all revisions to specific page since a given timestamp.

    Input:
    - pagename: string, title of the page for which to pull revisions
    - oldtimestamp, newtimestamp: strings, representing timestamps in Mediawiki
      format, between which to lookup the revisions
    Output: a list of dict, each corresponding to a single revision

    That function can also pull multiple pages with the rvcontinue API key.
    To do so, the function is called recursively with a continuenumber (counter
    describing the maximum number of page pulls left, to avoid infinite looping
    while requesting API resources) and a continuestring, cf. rvcontinue in
    https://www.mediawiki.org/wiki/API:Revisions

    Doctests:
    >>> get_revisions_from_api('Tiger','2018-03-01T00:00:00Z',
    ...                        '2018-03-05T00:00:00Z') ==\
    [{'timestamp': '2018-03-04T15:30:31Z',
    ...  'parentid': 828307448,
    ...  'comment': '/* Size */Journal cites: format page range,',
    ...  'user': 'Rjwilmsi',
    ...  'revid': 828751877},
    ... {'timestamp': '2018-03-01T20:11:02Z',
    ...  'parentid': 828233956,
    ...  'comment': '/* Reproduction */ hatnote',
    ...  'user': 'BDD',
    ...  'revid': 828307448},
    ... {'timestamp': '2018-03-01T10:08:52Z',
    ...  'parentid': 828032712,
    ...  'comment': '/* Taxonomy */ edited ref',
    ...  'user': 'BhagyaMani',
    ...  'revid': 828233956}]
    True
    """
    params = {'action': 'query',
              'prop': 'revisions',
              'titles': pagename,
              'format': 'json',
              'rvprop': 'timestamp|user|comment|ids',
              'rvdir': 'older',
              'rvend': oldtimestamp,
              'rvstart': newtimestamp,
              'rvlimit': 'max'
              }

    # Previous call may require to continue a call
    if continuestring:
        params['rvcontinue'] = continuestring

    api_call_result = manual_API_call(site, **params)

    tmp = api_call_result['query']['pages']
    tmp2 = list(tmp.keys())  # single-element list e.g. ['36896']
    revlist = tmp[tmp2[0]]['revisions']

    # Check if we need to pull more revisions
    # If so, recursively call itself and merge results
    if maxcontinuenumber > 0 and 'query-continue' in api_call_result:
        # 'batchcomplete' key present = no continue needed
        # maxcontinuenumber<=0 = we have reached the maximum of continues

        # toprint = api_call_result.copy()
        # toprint['query']['pages'] = '...some stuff...'
        # print(toprint)
        cs = api_call_result['query-continue']['revisions']['rvcontinue']
        rcl = get_revisions_from_api(pagename, oldtimestamp, newtimestamp,
                                     maxcontinuenumber=maxcontinuenumber - 1,
                                     continuestring=cs)
        full_list = revlist + rcl
        return full_list
    else:
        return revlist


# Other commands
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
    userinfo = get_user_info(users)

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
    >>> safe_list_diff(['Hello','See you later','Bye'],['Hello'])
    ['See you later', 'Bye']

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
    # Ensure we return them in the original order!
    final_list = []
    set_to_return = setbefore - setafter - setdupes
    for tn in listbefore:
        if tn in set_to_return:
            final_list.append(tn)

    return final_list


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


def traverse_list_of_sections(inputlistofdict):
    """Get list of sections from the API output.

    Remove the fluff (data offset etc.) from get_sections_from_revid to get
    only thread names (i.e. the 'line' key).
    """
    output_list = []

    for item in inputlistofdict:
        output_list.append(item['line'])

    return output_list


def find_section_anchor(inputlistofdict, sectionname):
    """Match a section name to the output of get_sections_from_revid.

    Input: inputlistofdict comes from get_sections_from_revid (list of dict),
    sectionname is a string (name of a thread).

    Output: a list of section anchors, corresponding to all unique
    sections that have the name sectionname. The normal case is for the
    list to have a single element, but returning a list allows easier
    testing for edge cases later.

    Leading and trailing spaces are removed for the comparison.

    Doctests:
    >>> find_section_anchor([{'anchor': 'Request:_World_Cafe',
    ...                       'byteoffset': 3329,
    ...                       'fromtitle': 'Wikipedia:Teahouse',
    ...                       'index': '1',
    ...                       'level': '2',
    ...                       'line': 'Request: World Cafe',
    ...                       'number': '1',
    ...                       'toclevel': 1},
    ...                      {'anchor': 'How_to_publish_my_page',
    ...                       'byteoffset': 8292,
    ...                       'fromtitle': 'Wikipedia:Teahouse',
    ...                       'index': '2',
    ...                       'level': '2',
    ...                       'line': 'How to publish my page',
    ...                       'number': '2',
    ...                       'toclevel': 1}
    ...                      ],
    ...                     'How to publish my page')
    ['How_to_publish_my_page']
    """
    outlist = []

    for item in inputlistofdict:
        if sectionname.strip() == item['line'].strip():
            outlist.append(item['anchor'])

    return outlist


def search_archives_for_section(links_to_search, sectionnames):
    """Find links to archived threads.

    This checks the current content of multiple archive links for the
    desired section names, and ensure only a unique match is accepted
    for each. Otherwise, failure to find a unique match is logged.

    Input: links_to_search is a list of strings, the names (shortened URL) of
    archive pages to search; sectionnames is a list of strings, the 'anchor's
    to match.

    Doctests:
    >>> search_archives_for_section(['Wikipedia:Teahouse/Questions/Archive_98',
    ...                              'Wikipedia:Teahouse/Questions/Archive_99'
    ...                              ],['Picture problem', 'Blog as reference?'])  # noqa: E501
    ['Wikipedia:Teahouse/Questions/Archive_98#Picture_problem', 'Wikipedia:Teahouse/Questions/Archive_99#Blog_as_reference?']
    """
    # First, query the API for the content of the archive links
    archive_contents = dict()
    for archivelink in links_to_search:
        linkcontent = get_sections_from_revid(archivelink)
        archive_contents[archivelink] = linkcontent  # links as keys, why not

        # print(linkcontent)
    # Loop over the queried section names
    out_links = []

    for sn in sectionnames:
        matches = []  # will hold the matched section(s)

        for arlink in links_to_search:
            linkmatches = find_section_anchor(archive_contents[arlink], sn)
            if linkmatches:  # found (at least) one good thread there
                candidatelink = arlink

            matches += linkmatches  # append current matches to old ones

        if len(matches) == 1:  # the good case: we found exactly one match
            fullarchivelink = candidatelink + "#" + matches[0]
            out_links.append(fullarchivelink)
            continue

        # If we did not continue, we are in the bad case, so we default
        # the link to an empty string
        out_links.append('')

        # Log the problem
        nomatch = 'No thread "{tn}" found in the links "{l}"'
        morematches = 'Multiple matches for thread "{tn}" in the links "{l}"'
        if len(matches) == 0:
            logging.warning(nomatch.format(tn=sn, l=links_to_search))
        else:  # len(matches)>1
            logging.warning(morematches.format(tn=sn, l=links_to_search))

    return out_links


def sections_removed_by_diff(revid1, revid2):
    """Get sections removed between two edits.

    Inputs: two revision IDs (integers). You should ensure that both revids
    refer to consecutive edits on the same page; this is not directly checked.
    That function makes a call to safe_list_diff, which will probably throw an
    exception if a different page is used or if the diff is too far apart, but
    you should not rely on that.

    Output: a list of strings, the names of removed threads.

    Doctests:
    (Cf. https://en.wikipedia.org/w/index.php?oldid=783715718&diff=783718598)
    >>> sections_removed_by_diff(783715718,783718598)[:2]
    ['Red links', 'how to undo a merge made 6 yrs ago']
    """
    json1 = get_sections_from_revid(revid1)
    sec_list_1 = traverse_list_of_sections(json1)

    json2 = get_sections_from_revid(revid2)
    sec_list_2 = traverse_list_of_sections(json2)

    set_of_sections_removed = safe_list_diff(sec_list_1, sec_list_2)
    return set_of_sections_removed


def revisions_since_x_days(pagename, ndays, maxcontinuenumber=0):
    """Get revision data for a given page for the last n days.

    Input:
    - pagename (string), the name of the page
    - ndays (int or float): lookup revisions of the last ndays days
    - maxcontinuenumber (int): recursion limit for API calls
    Output: a list of dict (cf. get_revisions_from_api).
    """
    # Per https://www.mediawiki.org/wiki/API:Revisions, rvstart is newer
    # than rvend if we list in reverse chronological order
    # (newer revisions first), i.e. "end" and "start" refer to the list.
    oldtimestamp = UTC_timestamp_x_days_ago(days_offset=ndays)
    currenttimestamp = UTC_timestamp_x_days_ago(days_offset=0)
    revs = get_revisions_from_api(pagename, oldtimestamp, currenttimestamp,
                                  maxcontinuenumber=maxcontinuenumber)

    return revs


def es_created_newsection(editsummary):  # noqa: D301
    """Parse the given edit summary to see if a new section was created.

    Input: a string of edit summary
    Output: a dict whose key 'flag' is True if a section was created and False
    otherwise; additionally, if 'flag' is True, the dict has the key 'name',
    containing the name of the thread.

    The given string is matched to "/* %s */ new section"; if matched,
    we assume the corresponding edit created a section named %s.

    Doctests:
    >>> es_created_newsection(r'/* Waiting for Godot */ new section') ==\
    {'flag': True, 'name': 'Waiting for Godot'}
    True
    """
    pattern = re.compile(r'(\/\* )(.*)( \*\/ new section)')
    match = pattern.match(editsummary)
    # Note: using pattern.search will pick up e.g. Sinebot's edit summaries of
    # "Signing comment by Foo - "/* Bar */: new section""
    # Instead, pattern.match enforces a match at the start of the string
    if match:
        output = {'flag': True,
                  'name': match.group(2),
                  }
    else:
        output = {'flag': False}
    return output


def newsections_at_teahouse(ndays=10, thname='Wikipedia:Teahouse',
                            maxcontinuenumber=0):
    """Get 'new section' creations at Teahouse in the last few days.

    Optional arguments:
    - ndays (10): (int or float) timeframe in days of revision to pull
    - thname: (string) name of the page whose revisions to pull
    - maxcontinuenumber: (int) recursion limit for API calls
    """
    rev_table = revisions_since_x_days(thname, ndays,
                                       maxcontinuenumber=maxcontinuenumber)
    output = []
    for rev in rev_table:
        editsummary = rev['comment']
        newsection_created = es_created_newsection(editsummary)
        if newsection_created['flag']:
            tosave = {'revid': rev['revid'],
                      'name': newsection_created['name'],
                      'user': rev['user'],
                      }
            output.append(tosave)

    return output


def last_archival_edit(maxdays=1, thname='Wikipedia:Teahouse',
                       archiver='Lowercase sigmabot III'):
    """Parse page history for last archival edit.

    Input:
    - maxdays (int) the timeframe in days to look for an archival edit
    - thname (string) title of the page to look at
    - archiver (string) username of the archival bot

    Output: dict describing the last archival edit.
    """
    rev_table = revisions_since_x_days(thname, maxdays)
    found_flag = False
    for rev in rev_table:
        if rev['user'] == archiver:  # we found an archival edit
            es = rev['comment']  # extract edit summary
            # Determine archive locations from edit summary.
            # Beware! The edit summary may contain multiple wikilinks.
            # See for instance
            # https://en.wikipedia.org/w/index.php?title=Wikipedia%3ATeahouse&type=revision&diff=783570477&oldid=783564581
            # We need to match non-greedily and find all such links.
            pattern = r'(\[\[.*?\]\])'
            links = re.findall(pattern, es)

            if not links:  # sanity check that at least one match was found
                raise ValueError('Archival edit summary does not contain'
                                 + 'any wikilink.', es)

            # strip brackets in links
            strippedlinks = [l[2:-2] for l in links]

            # save relevant edit information
            output = {'after': rev['revid'],
                      'before': rev['parentid'],
                      'links': strippedlinks,
                      'es': es,                 # for debugging purposes
                      'archiver': archiver,  # same (not used as of 2018-03-18)
                      }
            found_flag = True
            break
    if not found_flag:
        raise ValueError('No edit by {arc} '.format(arc=archiver)
                         + 'found in the last {n} days'.format(n=maxdays),
                         rev_table)
    return output


def generate_notification_list():
    """Make list of notifications to make.

    This function makes all the API read calls necessary to determine which
    threads have been last archived, which users started them, and whether
    those users are eligible to receive a notification.

    The output is a list of dict, each containing the keys:
    - 'user'    - username of thread started
    - 'tn'      - thread name
    - 'invalid' - whether a notification can be sent
    Additionally, it can also contain:
    - 'archivelink' - a link to the archived thread (with anchor), if found
    - 'reason'      - if 'invalid' is True, explains why
    """
    # Get last archival edit
    lae = last_archival_edit()
    idbefore = lae['before']
    idafter = lae['after']
    # Sections from last archival edit
    archived_sections = sections_removed_by_diff(idbefore, idafter)

    # New section creations in recent days from page history
    maxpagestopull = 5
    nscreated = newsections_at_teahouse(maxcontinuenumber=maxpagestopull)

    # List of threads that were archived in last archival edit, which
    # could be matched to their creation in the last few days
    thread_matched = list_matching(archived_sections, nscreated)
    thread_matched_names = [thread['name'] for thread in thread_matched]
    thread_matched_users = [thread['user'] for thread in thread_matched]

    # For those, try and recover the corresponding archival link
    # (including anchor)
    possible_archive_links = lae['links']
    list_of_archive_links = search_archives_for_section(possible_archive_links,
                                                        thread_matched_names)

    # Check if user can be notified
    is_notifiable = isnotifiable(thread_matched_users)

    # Generate notification list
    N = len(list_of_archive_links)
    notification_list = list()
    for i in range(N):
        username = thread_matched_users[i]
        tn = thread_matched_names[i]
        al = list_of_archive_links[i]

        notif = {'user': username,
                 'thread': tn,
                 'invalid': False,
                 }

        if al:
            notif['archivelink'] = al
        else:
            # skip if the archive link is empty, i.e. it was not found
            # previously (such an event was logged)
            notif['invalid'] = True
            notif['reason'] = 'archive link not found'

        if not is_notifiable[username]:
            notif['invalid'] = True
            notif['reason'] = 'user is not notifiable'

        notification_list.append(notif)

    return notification_list


def notify(user, argstr, testlvl):
    """Post archival notification.

    Input:
    - user: (string) username, will post to User talk:<user>
    - argstr: (string) contains arguments to pass to template
    - testlvl: (int) 0 for production, >=1 for various test levels

    No output to stdout, since this will cause posts on WP.
    """
    if testlvl == 1:
        raise ValueError('Test level 1 no longer works.')
        site = pywikibot.Site('test', 'test')
        page = pywikibot.Page(site, 'User talk:Tigraan-testbot/THA log')
        sn = 'Notification intended for [[:en:User talk:' + user + ']]'
        es = 'Notification intended for [[:en:User talk:' + user + ']]'

    elif testlvl == 2:
        site = pywikibot.Site('en', 'wikipedia')
        page = pywikibot.Page(site, 'User talk:Muninnbot/THA log')
        sn = 'Notification intended for [[:en:User talk:' + user + ']]'
        es = 'Notification intended for [[:en:User talk:' + user + ']]'

    elif testlvl == 3:
        site = pywikibot.Site('en', 'wikipedia')
        page = pywikibot.Page(site, 'User talk:' + user)
        sn = 'Your thread has been archived'
        es = 'Automated notification of thread archival (test run)'

    elif testlvl == 0:
        # Production code goes here
        if False:  # remove this "test" once you go in production
            site = pywikibot.Site('en', 'wikipedia')
            page = pywikibot.Page(site, 'User talk:' + user)
            sn = 'Your thread has been archived'
            es = 'Your thread has been archived'

    # 0 for production, all the rest creates a "this is in test phase" comment
    if testlvl > 0:
        test_comment = "</br><small>This functionality is currently under "\
                       + "test. If you received this notification by error, "\
                       + "please [[User talk:Tigraan|notify the bot's"\
                       + " maintainer]].</small>"
        text = '{{subst:User:Tigraan-testbot/Teahouse archival notification|'\
               + argstr + '|additionaltext=' + test_comment + '}}'
    else:
        text = '{{subst:User:Tigraan-testbot/Teahouse archival notification|'\
               + argstr + '}}'

    page.save(text=text, summary=sn, section='new', minor=False, botflag=True)


def notify_all(notification_list, status,
               archive_from='[[Wikipedia:Teahouse]]',
               botname='Muninnbot'):
    """Execute notification list.

    Input:
    - notification_list: cf. generate_notification_list for format
    - status: 'offlinetest' for printing to stdout, 'test-X' for various
              testing levels, 'prod' for production use
    - archive_from: original page of the thread (only for notification
                    formatting, not actually checked)
    - botname: name of the bot who leaves the notification

    No output to stdout, but this will cause posts on WP.
    """
    formatspec = 'pagelinked={pl}|threadname={tn}|archivelink={al}|'\
                 + 'botname={bn}|editorname={en}'
    warnmsg = 'Thread "{thread}" by user {user} will not cause notification:'\
              + ' {reason}.'
    for item in notification_list:
        user = item['user']
        thread = item['thread']

        if item['invalid']:
            logging.warning(warnmsg.format(thread=thread, user=user,
                                           reason=item['reason']))
            continue
        archivelink = item['archivelink']

        argstr = formatspec.format(pl=archive_from, tn=thread, al=archivelink,
                                   bn=botname, en=user)

        if status == 'offlinetest':
            print('[[User talk:' + user + ']] -> {{subst:User:Tigraan-testbot/'
                  + 'Teahouse archival notification|' + argstr + '}}')
        elif status == 'test-1':
            notify(user, argstr, testlvl=1)
        elif status == 'test-2':
            notify(user, argstr, testlvl=2)
        elif status == 'test-3':
            notify(user, argstr, testlvl=3)
        elif status == 'prod':
            notify(user, argstr, testlvl=0)
        else:
            raise ValueError('Option was not understood.', status)


def main():
    """Run main procedure.

    Run once the full procedure:
    - find last archival edit and extract archived threads
    - lookup in the page history who created those threads
    - check for each user whether they can be sent a notification
    - send notifications for whoever can receive them

    With PWB/OAuth we should be logged in everytime.
    """
    # try to log in, fail if it does not work
    s = pywikibot.Site()
    s.login()
    assert s.logged_in()

    cur_user = whoami(site=s)
    logging.info('Currently logged as:' + cur_user)
    assert cur_user == 'Muninnbot'

    # place the notifications
    notiflist = generate_notification_list()
    notify_all(notiflist, status='test-2')

if __name__ == "__main__":
    # Unit test run. See
    # https://docs.python.org/3/library/doctest.html#simple-usage-checking-examples-in-docstrings
    import doctest
    logging.basicConfig(level=logging.ERROR)  # ignore logging warnings
    (failure_count, test_count) = doctest.testmod()

    if failure_count > 0:
        logging.error("I failed at least one unit test, and will stop here.")
    else:
        logging.basicConfig(level=logging.INFO)
        logging.info("Unit tests passed. Executing the full procedure...")
        main()
