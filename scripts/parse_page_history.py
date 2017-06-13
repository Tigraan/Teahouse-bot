#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  parse_page_history.py
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
#  log
#  

#~ import json # note to self: shouldn't this be called somewhere?
import re

from utilities import api_call,UTC_timestamp_x_days_ago


def get_revisions_from_api(pagename,oldtimestamp,newtimestamp,apiurl='https://en.wikipedia.org/w/api.php'):
	'''Get all revisions to specific page since a given timestamp.'''
	
	params = {'action' : 'query',
			'prop' : 'revisions',
			'titles' : pagename,
			'format' : 'json',
			'rvprop' : 'timestamp|user|comment|ids',
			'rvdir' : 'older',
			'rvend' : oldtimestamp,
			'rvstart' : newtimestamp,
			'rvlimit' : 'max'
			}
	api_call_result = api_call(apiurl,params)
	
	
	return api_call_result
	

def revisions_since_x_days(pagename,ndays):
	'''Gets revision data for a given page for the last n days.
	
	'''
	

	
	#Per https://www.mediawiki.org/wiki/API:Revisions, rvstart is newer
	#than rvend if we list in reverse chronological order
	#(newer revisions first), i.e. "end" and "start" refer to the list.
	oldtimestamp = UTC_timestamp_x_days_ago(days_offset=ndays)
	currenttimestamp = UTC_timestamp_x_days_ago(days_offset=0)
	blob = get_revisions_from_api(pagename,oldtimestamp,currenttimestamp)
	
	#At that point we still have some hierarchy to traverse.
	#Example output for 'blob': (2 revisions of 'Lion' on en-wp)
		#{'batchcomplete': '',
		 #'query': {'pages': {'36896': {'ns': 0,
									   #'pageid': 36896,
									   #'revisions': [{'comment': 'we have enough '
																 #'images here',
													  #'parentid': 783432210,
													  #'revid': 783454040,
													  #'timestamp': '2017-06-02T12:07:21Z',
													  #'user': 'LittleJerry'},
													 #{'comment': '/* Cultural '
																 #'significance */ An '
																 #'old advert which '
																 #"depicts the lion's "
																 #'cultural '
																 #'significance in '
																 #'[[England]].',
													  #'parentid': 783139314,
													  #'revid': 783432210,
													  #'timestamp': '2017-06-02T07:38:02Z',
													  #'user': 'Leo1pard'}],
									   #'title': 'Lion'}}}}
	tmp = blob['query']['pages']
	tmp2 = list(tmp.keys()) # ['36896'] in the previous example, but it can change
	
	#Beware: if the blob contains no revisions, the following line will
	#fail with a KeyError because the key 'revisions' will not exist.
	revs = tmp[tmp2[0]]['revisions']
	
	return revs
	
def es_created_newsection(editsummary):
	'''Parses the given edit summary to see if a new section was created.
	
	The given string is matched to "/* %s */ new section"; if matched,
	we assume the corresponding edit created a section named %s.'''
	pattern = re.compile(r'(\/\* )(.*)( \*\/ new section)')
	match = pattern.match(editsummary)
	#Note: using pattern.search will pick up Sinebot's edit summaries of
	#"Signing comment by Foo - "/* Bar */: new section""
	#Instead, pattern.match enforces a match at the start of the string
	if match:
		output = {'flag' : True,
				'name' : match.group(2),
				}
	else:
		output = {'flag' : False}
	return output
	
	
	
	
	
def newsections_at_teahouse(ndays=10,thname='Wikipedia:Teahouse'):
	'''Gets the revisions and finds 'new section' creations.
	
	ndays is set to 10 by default: parses the last 10 days of Teahouse posts.'''
	
	rev_table = revisions_since_x_days(thname,ndays)
	
	output = []
	for rev in rev_table:
		editsummary = rev['comment']
		newsection_created = es_created_newsection(editsummary)
		if newsection_created['flag']:
			tosave = {'revid' : rev['revid'],
					'name' : newsection_created['name'],
					'user' : rev['user'],
					}
			output.append(tosave)
			
			
	return output
		
def last_archival_edit(maxdays=1,thname='Wikipedia:Teahouse',archiver='Lowercase sigmabot III'):
	'''Parses page history for last archival edit.
	
	'''
	
	rev_table = revisions_since_x_days(thname,maxdays)
	found_flag = False
	for rev in rev_table:
		if rev['user'] == archiver: #we found an archival edit
			es = rev['comment'] #extract edit summary
			#Beware! The edit summary may contain multiple wikilinks.
			#See for instance https://en.wikipedia.org/w/index.php?title=Wikipedia%3ATeahouse&type=revision&diff=783570477&oldid=783564581
			#We need to match non-greedily and find all such links.
			pattern = r'(\[\[.*?\]\])'
			links = re.findall(pattern,es)
			
			if not links: #sanity check that a match was found
				raise ValueError('Archival edit summary does not contain any wikilink.',es)
			
			# save relevant edit information
			output = {'after' : rev['revid'],
					'before' : rev['parentid'],
					'links' : links,
					'es' : es,				#should not be used, but it could help for debugging
					'archiver' : archiver,	#idem
					}
			found_flag=True
			break
	if not found_flag:
		raise ValueError('No edit by {arc} found in the last {n} days'.format(arc=archiver,n=maxdays), rev_table)
	return output
			
	
	
#~ # Tests
if __name__ == "__main__": # we are in a test run
	import pprint
	#~ # Read possible additional input arguments
	#~ import sys
	#~ args = sys.argv[1:]
	
	
	print('This is a test run of the revision table parser.\n')
	testpage='Wikipedia:Teahouse'
	revtesthours=2
	nstesthours=6
	print('Edits of {tp} since {h} hour(s):'.format(tp=testpage,h=revtesthours))
	pprint.pprint(revisions_since_x_days(testpage,revtesthours/24))
	
	print('New sections at Wikipedia:Teahouse since {h} hour(s):'.format(h=nstesthours))
	pprint.pprint(newsections_at_teahouse(ndays=nstesthours/24))
	print('Last archival edit at Wikipedia:Teahouse:')
	pprint.pprint(last_archival_edit(maxdays=1))


