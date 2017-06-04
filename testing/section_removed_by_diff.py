#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  section_removed_by_diff.py
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

import logging
import requests
import json
import pprint
import collections

def api_call(endpoint, parameters):
	'''Small script by Jtmorgan to call the API.
	
	I added a User-agent per https://www.mediawiki.org/wiki/API:Main_page#Identifying_your_client'''
	
	#Adding my own user agent per https://www.mediawiki.org/wiki/API:Main_page#Identifying_your_client
	headers = requests.utils.default_headers()
	def_ua = headers['User-Agent'] # 'python-requests/2.9.1' or similar
	my_ua = '{default} - {my_text}'.format(default=def_ua,my_text='User:Tigraan')
	headers.update(
		{
			'User-Agent': my_ua,
			'From': 'rienenvoyer@gmail.com',
		}
	)
	
	try:
		call = requests.get(endpoint, params=parameters, headers=headers)
		response = call.json()
	except:
		response = None
	return response

def get_sections_from_api(revid,api_url='https://en.wikipedia.org/w/api.php'):
	'''Get list of section from specific page revision.
	
	Adapted from code by User:Jtmorgan - http://paws-public.wmflabs.org/paws-public/User:Jtmorgan/API_calls.ipynb'''
	
	params = {'action' : 'parse',
            'prop' : 'sections',
            'format' : 'json',
            'formatversion' : 2,
			'oldid' : revid,
            }
	api_call_result = api_call(api_url,params)
	
	
	return api_call_result


def json_to_list_of_sections(json_output):
	'''Get set of sections from the API output.
	
	The output is a JSON-formatted string, but Python transforms it into
	a dictionary. We just extract the relevant parts (we don't care
	about byte offset etc.).'''
	
	
	# The output of get_sections_from_api looks like:
	
		# {'parse': {'pageid': 34745517,
			   # 'revid': 783718598,
			   # 'sections': [{'anchor': 'Request:_World_Cafe',
					# 'byteoffset': 3329,
					# 'fromtitle': 'Wikipedia:Teahouse',
					# 'index': '1',
					# 'level': '2',
					# 'line': 'Request: World Cafe',
					# 'number': '1',
					# 'toclevel': 1},
					# {'anchor': 'How_to_publish_my_page',
					# 'byteoffset': 8292,
					# 'fromtitle': 'Wikipedia:Teahouse',
					# 'index': '2',
					# 'level': '2',
					# 'line': 'How to publish my page',
					# 'number': '2',
					# 'toclevel': 1},
					 
					# ...snip...
					
					# ],
				# 'title': 'Wikipedia:Teahouse'}}
				
	# So, we need to traverse two levels of the dictionary to get to
	# a list of dictionaries; each of those corresponds to a section,
	# whose 'line' key is our object of interest.
	
	input_list=json_output['parse']['sections']
	
	#An edge case is when there are duplicates in the name of sections.
	#For later development, it should be possible to use a list (ordered)
	#instead of a set (unordered) to help discriminate between
	#possible collisions...
	
	output_list = []
	
	for item in input_list:
		output_list.append(item['line'])
	
	return output_list

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

def section_removed_by_diff(revid1,revid2):
	'''Puts together a diff of removed sections.
	
	Output is a set of sections that were removed in revid2 compared to
	revid1. The code does not check whether the page corresponding to
	the revision IDs is the same, or whether the diff contains
	intermediary edits. Because it calls safe_list_diff,
	it will probably throw an exception if a different page is used
	or if the diff is too far apart, but this should be ensured
	upstream (when generating the arguments revid1 and revid2).'''
	
	json1 = get_sections_from_api(revid=revid1)
	sec_list_1 = json_to_list_of_sections(json1)
	
	json2 = get_sections_from_api(revid=revid2)
	sec_list_2 = json_to_list_of_sections(json2)
	
	set_of_sections_removed = safe_list_diff(sec_list_1,sec_list_2)
	return set_of_sections_removed
	
	
	
	
def testcase():
	'''Putting together a "diff" (difference before/after archival).
	
	Uses lowercase sigmabot III's archival edit on 2017-06-04'''
	
	#Teahouse just before an archival edit (https://en.wikipedia.org/w/index.php?title=Wikipedia:Teahouse&oldid=783715718)
	id1=783715718
	#Teahouse just after an archival edit (https://en.wikipedia.org/w/index.php?title=Wikipedia:Teahouse&oldid=783718598)
	id2=783718598
	
	res=section_removed_by_diff(id1,id2)
	return res
	
	
	
#~ # Tests of individual subfunctions

#~ # safe_list_diff	
#~ list1=['a','b','b','c','d']
#~ list2=['a','c']
#~ #list2=['a','e'] #causes an exception because 'e' is not in list1
#~ a=safe_list_diff(list1,list2)
#~ print(a)


#Global test case
a=testcase()
print(a)


