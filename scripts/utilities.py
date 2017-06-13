#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  utilities.py
#  
#  Copyright 2017 Tigraan <User:Tigraan>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  

import requests # http/https calls (for API calling)
import datetime # get current time, convert time string representations
import collections # Stackexchange code for list utilities requires this
import logging # warning messages etc.


#Utilities to call the Mediawiki API to get the info we will need.

def my_user_agent():
	'''Defines the default user agent of the script.
	
	API calls to Mediawiki must include this, see
	https://www.mediawiki.org/wiki/API:Main_page#Identifying_your_client'''
	headers = requests.utils.default_headers()
	def_ua = headers['User-Agent'] # 'python-requests/2.9.1' or similar
	my_ua = '{default} - {my_text}'.format(default=def_ua,my_text='User:Tigraan')
	headers.update(
		{
			'User-Agent': my_ua,
			'From': 'rienenvoyer@gmail.com',
		}
	)
	return headers
	

def api_call(endpoint, parameters):
	'''Small script by Jtmorgan to call the API.
	
	I added a User-agent, cf. above.'''
	
	#Adding my own user agent per https://www.mediawiki.org/wiki/API:Main_page#Identifying_your_client
	headers = my_user_agent()
	
	try:
		call = requests.get(endpoint, params=parameters, headers=headers)
		response = call.json()
	except:
		response = None
	return response

#Small tool to obtain and convert timestamps to Mediawiki format.

def UTC_timestamp_x_days_ago(days_offset=0):
	'''Timestamp x days ago in Mediawiki format.
	
	Input is the number of days that will be substracted from the
	current timestamp.
	Format: cf. https://www.mediawiki.org/wiki/Manual:Timestamp'''
	
	current_time = datetime.datetime.utcnow()#UTC time on MediaWiki servers
	offset = datetime.timedelta(days=-days_offset)
	UTC_time_then = current_time + offset
	
	timestamp = UTC_time_then.strftime("%Y%m%d%H%M%S")
	return timestamp
	
#List handling utilities

def safe_list_diff(listbefore,listafter):
	'''Find elements that were removed from one list to another.
	
	Compared to a basic set diff, this takes care of the edge case
	where an element is present multiple times in the larger list
	by removing it altogether (and logging this fact).
	Also, it will raise an exception if the second list is not
	included in the first one (which is expected for an archival diff).'''
	
	#Identify the duplicates elements in listbefore. This is needed to
	#avoid collisions later on. User is warned and duplicates are
	#removed in the final output.
	#For the method, see https://stackoverflow.com/questions/11236006/identify-duplicate-values-in-a-list-in-python
	duplicate_values = [k for k,v in collections.Counter(listbefore).items() if v>1]
	
	for val in duplicate_values:
		logging.warning('Multiple threads that share the same name will be ignored. The name was "{nameofthread}".'.format(nameofthread=val))
	
	setbefore= set(listbefore)
	setafter = set(listafter)
	setdupes = set(duplicate_values)
	
	#Sanity check that listafter <= listbefore (less threads after archiving)
	should_be_empty = setafter - setbefore
	#https://www.python.org/dev/peps/pep-0008/#programming-recommendations: "use the fact that empty sequences are false"
	if should_be_empty:
		raise ValueError('Not all elements of the second argument list are in the first argument list. Did you pass the correct section lists?', should_be_empty)
		
	#If all is well, get the set of threads that were removed and which
	#are not duplicates
	setdiff = setbefore - setafter - setdupes
	return setdiff

	
def list_matching(threadsarchived,threadscreated):
	'''Matches elements from two lists.
	
	We have on the one hand a list of threads that underwent the last
	archival, and on the other hand a list of created new sections.
	We want to match each of the archived threads to its creation.
	If a thread is matched multiple times or not at all, it must not be
	passed later on, but the event should be logged.
	
	threadsarchived is a set (it has been sanitized upstream to deal
	with name collisions). threadscreated is a list of dict; each dict
	contains at least 'name', the thread title to match.
	The output is a list of dict, the subset of threadscreated
	that have been matched exactly once in threadsarchived.'''
	
	output=[]
	ta=list(threadsarchived) # necessary for index addressing
	
	for i in range(len(ta)):
		cur_str = ta[i]
		matching_indices = [j for j,k in enumerate(threadscreated) if k['name'] == cur_str]
		if not matching_indices: #0 matches
			logging.warning('''No matches for the creation of the following thread: "{tn}"'''.format(tn=cur_str))
		else:
			if len(matching_indices)>1: #2 or more matches
				logging.warning('''Multiple matches (all will be ignored) for the creation of the following thread: "{tn}"'''.format(tn=cur_str))
			else: # the normal case
				output.append(threadscreated[matching_indices[0]])
	return output
	
	
	
if __name__ == "__main__": # we are in a test run
	#~ # Read possible additional input arguments
	#~ import sys
	#~ args = sys.argv[1:]
	from pprint import pprint
	
	cur_timestamp = UTC_timestamp_x_days_ago(0)
	uah=my_user_agent()
	ua = uah['User-Agent']
	s2p = '''
This is a test run of the utilities module.

The current timestamp is '{ct}'.
API calls will use the User-Agent '{ua}'.\n
		'''
	print(s2p.format(ct=cur_timestamp,ua=ua))
	
	threadarchived_test=set(['Thread#1','Thread#2','Thread#5'])
	threadcreated_test = [
		{'revid' : 1,
		'name' : 'Thread#1',
		'user' : 'User#1',
		},
		{'revid' : 2,
		'name' : 'Thread#2',
		'user' : 'User#2',
		},
		{'revid' : 3,
		'name' : 'Thread#3',
		'user' : 'User#3',
		},
		{'revid' : 4,
		'name' : 'Thread#4',
		'user' : 'User#4',
		}]
	print('If an archival edit consisted of the following threads:\n')
	pprint(threadarchived_test)
	print('\n...and the corresponding thread creations were found:\n')
	pprint(threadcreated_test)
	print('\nThen here is the session log of the thread matching process:\n')
	mt = list_matching(threadarchived_test,threadcreated_test)
	print('\n...and here is the end result (matched threads):\n')
	pprint(mt)
		
	
	
	
#~ else: # the module was simply loaded for later use
	#~ # do some stuff
