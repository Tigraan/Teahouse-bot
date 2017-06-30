#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  parse_page.py
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


import re #regular expressions
import logging # warning messages etc.
from utilities import api_call,UTC_timestamp_x_days_ago,safe_list_diff

# Functions that manipulate sections of particular page revisions

def get_sections_from_api(pageindicator,api_url='https://en.wikipedia.org/w/api.php'):
	'''Get list of sections from specific page revision.
	
	Adapted from code by User:Jtmorgan - http://paws-public.wmflabs.org/paws-public/User:Jtmorgan/API_calls.ipynb
	
	The page to parse can be specified either by a string (e.g.
	"Main Page") in which case the latest revision is used, or by an
	integer, in which case it is treated as a revision number (via
	'oldid', cf. https://www.mediawiki.org/wiki/API:Parsing_wikitext).
	
	'''
	
	# check format of input parameter and act accordingly
	
	if isinstance(pageindicator, str):
		
		params = {'action' : 'parse',
				'prop' : 'sections',
				'format' : 'json',
				'formatversion' : 2,
				'page' : pageindicator,
				}
		
	else:
	
		params = {'action' : 'parse',
				'prop' : 'sections',
				'format' : 'json',
				'formatversion' : 2,
				'oldid' : pageindicator,
				}
				
	api_call_result = api_call(api_url,params)
	
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
	
	
	sec_list_of_dict = api_call_result['parse']['sections']
	return sec_list_of_dict


def traverse_list_of_sections(inputlistofdict):
	'''Get list of sections from the API output.
	
	Removes the fluff (data offset etc.) from get_sections_from_api.'''
	
	
	output_list = []
	
	for item in inputlistofdict:
		output_list.append(item['line'])
	
	return output_list

def find_section_anchor(inputlistofdict,sectionname):
	'''Matches a section name to the output of get_sections_from_api.
	
	Returns a list of section anchors, corresponding to all unique
	sections that have the name sectionname. The normal case is for the
	list to have a single element, but returning a list allows easier
	testing later.'''
	
	outlist = []
	
	for item in inputlistofdict:
		if sectionname==item['line']:
			outlist.append(item['anchor'])
			
	return outlist
	
def search_archive_links_for_section(links_to_search,sectionnames):
	'''Finds links to archived threads.
	
	This checks the current content of multiple archive links for the
	desired section names, and ensure only a unique match is accepted
	for each. Otherwise, the fact is logged.'''
	
	# First, query the API for the content of the archive links
	
	archive_contents = dict()
	for archivelink in links_to_search:
		linkcontent = get_sections_from_api(archivelink)
		archive_contents[archivelink] = linkcontent #use links as keys because why not
	
	# Loop over the queried section names
	out_links = []
	
	for sectionname in sectionnames:
		matches = [] # will hold the matched section(s)
		
		for archivelink in links_to_search:
			linkmatches = find_section_anchor(archive_contents[archivelink],sectionname)
			if linkmatches: #found (at least) one good thread there
				candidatelink = archivelink
			
			matches += linkmatches # append current matches to old ones
		
		if len(matches)==1: # the good case: we found exactly one match
			fullarchivelink = candidatelink + "#" + matches[0]
			out_links.append(fullarchivelink)
			continue
			
		# If we did not continue, we are in the bad case, so we default
		# the link to an empty string
		out_links.append('')
		
		# Log the problem
		
		if len(matches)==0:
			logging.warning('''No thread "{tn}" found in the links "{links}"'''.format(tn=sectionname,links=links_to_search))
		else: # len(matches)>1
			logging.warning('''Multiple matches for thread "{tn}" in the links "{links}"'''.format(tn=sectionname,links=links_to_search))
			
		
	return out_links
		
		
	

# Functions that manipulate edit history

def sections_removed_by_diff(revid1,revid2):
	'''Puts together a diff of removed sections.
	
	Output is a set of sections that were removed in revid2 compared to
	revid1. The code does not check whether the page corresponding to
	the revision IDs is the same, or whether the diff contains
	intermediary edits. Because it calls safe_list_diff,
	it will probably throw an exception if a different page is used
	or if the diff is too far apart, but this should be ensured
	upstream (when generating the arguments revid1 and revid2).'''
	
	json1 = get_sections_from_api(revid1)
	sec_list_1 = traverse_list_of_sections(json1)
	
	json2 = get_sections_from_api(revid2)
	sec_list_2 = traverse_list_of_sections(json2)
	
	set_of_sections_removed = safe_list_diff(sec_list_1,sec_list_2)
	return set_of_sections_removed
	
	

	
def get_revisions_from_api(pagename,oldtimestamp,newtimestamp,maxcontinuenumber=0,continuestring=None,apiurl='https://en.wikipedia.org/w/api.php'):
	'''Get all revisions to specific page since a given timestamp.
	
	This can also pull multiple pages with the rvcontinue API key. To do so,
	specify a continuenumber (maximum number of additional pages to pull).'''
	
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
			
			
	# Previous call may require to continue a call
	if continuestring:
		params['rvcontinue']=continuestring
			
	api_call_result = api_call(apiurl,params)
	
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
	
	tmp = api_call_result['query']['pages']
	tmp2 = list(tmp.keys()) # ['36896'] in the previous example, but it can change
	revlist = tmp[tmp2[0]]['revisions']
	
	# Check if we need to pull more revisions
	# If so, recursively call itself and merge results
	
	if maxcontinuenumber>0 and not 'batchcomplete' in api_call_result:
		#'batchcomplete' key present = no continue needed
		#maxcontinuenumber<=0 = we have reached the maximum of continues
		cs = api_call_result['continue']['rvcontinue']
		recursively_called_list = get_revisions_from_api(pagename,oldtimestamp,newtimestamp,maxcontinuenumber=maxcontinuenumber-1,continuestring=cs,apiurl=apiurl)
		full_list = revlist + recursively_called_list
		return full_list
	else:
		return revlist
	

def revisions_since_x_days(pagename,ndays,maxcontinuenumber=0):
	'''Gets revision data for a given page for the last n days.
	
	'''
	

	
	#Per https://www.mediawiki.org/wiki/API:Revisions, rvstart is newer
	#than rvend if we list in reverse chronological order
	#(newer revisions first), i.e. "end" and "start" refer to the list.
	oldtimestamp = UTC_timestamp_x_days_ago(days_offset=ndays)
	currenttimestamp = UTC_timestamp_x_days_ago(days_offset=0)
	revs = get_revisions_from_api(pagename,oldtimestamp,currenttimestamp,maxcontinuenumber=maxcontinuenumber)
	
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
	
	
	
	
	
def newsections_at_teahouse(ndays=10,thname='Wikipedia:Teahouse',maxcontinuenumber=0):
	'''Gets the revisions and finds 'new section' creations.
	
	ndays is set to 10 by default: parses the last 10 days of Teahouse posts.'''
	
	rev_table = revisions_since_x_days(thname,ndays,maxcontinuenumber=maxcontinuenumber)
	
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
			
			if not links: #sanity check that at least one match was found
				raise ValueError('Archival edit summary does not contain any wikilink.',es)
				
			
			# strip brackets
			strippedlinks = [l[2:-2] for l in links]
			
			# save relevant edit information
			output = {'after' : rev['revid'],
					'before' : rev['parentid'],
					'links' : strippedlinks,
					'es' : es,				#should not be used, but it could help for debugging
					'archiver' : archiver,	#idem
					}
			found_flag=True
			break
	if not found_flag:
		raise ValueError('No edit by {arc} found in the last {n} days'.format(arc=archiver,n=maxdays), rev_table)
	return output
			
	
	
# Test run
if __name__ == "__main__":
	import pprint
	
	print('This is a test run of the revision table parser.\n')
	testpage='Wikipedia:Teahouse'
	revtesthours=2
	print('Edits of {tp} since {h} hour(s):'.format(tp=testpage,h=revtesthours))
	pprint.pprint(revisions_since_x_days(testpage,revtesthours/24))
	
	nstesthours=600
	ncontinues=1
	print('\nNew sections at Wikipedia:Teahouse since {h} hour(s) (max {pp}*500revs):'.format(h=nstesthours,pp=ncontinues+1))
	pprint.pprint(newsections_at_teahouse(ndays=nstesthours/24,maxcontinuenumber=ncontinues))
	
	lae = last_archival_edit(maxdays=1)
	id1=lae['before']
	id2=lae['after']
	link = 'https://en.wikipedia.org/w/index.php?title=Wikipedia:Teahouse&type=revision&diff={id2}&oldid={id1}'.format(id1=id1,id2=id2)
	print('\nLast archival edit at Wikipedia:Teahouse: {link}'.format(link=link))
	pprint.pprint(lae)
	print('\nThe following sections were removed by this edit:')
	pprint.pprint(sections_removed_by_diff(id1,id2))
