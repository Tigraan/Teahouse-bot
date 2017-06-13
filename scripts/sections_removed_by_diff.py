#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  sections_removed_by_diff.py
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

from utilities import api_call,safe_list_diff


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


def sections_removed_by_diff(revid1,revid2):
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
	
if __name__ == "__main__": # we are in a test run
	import pprint
	
	
	id1=783715718
	id2=783718598
	
	
	print('This is a test run of the section diff tool.\n')
	print('Permalink to just before an archival edit:')
	print('https://en.wikipedia.org/w/index.php?title=Wikipedia:Teahouse&oldid={id}'.format(id=id1))
	print('Permalink to just after an archival edit:')
	print('https://en.wikipedia.org/w/index.php?title=Wikipedia:Teahouse&oldid={id}\n'.format(id=id2))
	print('The following sections were removed by this edit:')
	pprint.pprint(sections_removed_by_diff(id1,id2))
	
