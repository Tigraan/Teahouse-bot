#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  find_and_notify.py
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

from parse_page_content import last_archival_edit,sections_removed_by_diff,newsections_at_teahouse,search_archive_links_for_section
from utilities import list_matching
from userinfo import isnotifiable

def notify(user,tn,al,pl='Wikipedia:Teahouse',bn='Tigraan-testbot',istestrun=True):
	formatspec='pagelinked={pl}|threadname={tn}|archivelink={al}|botname={bn}'
	argstr=formatspec.format(pl=pl,tn=tn,al=al,bn=bn)
	if istestrun:
		print('[[User talk:' + user + ']] -> {{subst:User:Tigraan-testbot/Teahouse archival notification|' + argstr + '}}')
	#~ else:
		# Perform here the real notification
		# Do not activate until bot approval was run!

def find_and_notify():
	# Get last archival edit
	lae = last_archival_edit()
	idbefore = lae['before']
	idafter  = lae['after']
	# Sections from last archival edit
	archived_sections = sections_removed_by_diff(idbefore,idafter) #set
	
	# New section creations in recent days from page history
	nscreated = newsections_at_teahouse() #list of dict
	
	# List of threads that were archived in last archival edit, which
	# could be matched to their creation in the last few days
	thread_matched = list_matching(archived_sections,nscreated) # list of dict
	thread_matched_names = [thread['name'] for thread in thread_matched] # list of thread names
	thread_matched_users = [thread['user'] for thread in thread_matched] # list of thread OPs
	
	
	#~ print('Matched sections:')
	#~ print(thread_matched_names)
	
	# For those, try and recover the corresponding archival link
	# (including anchor)
	possible_archive_links = lae['links']
	list_of_archive_links = search_archive_links_for_section(possible_archive_links,thread_matched_names)# list of str
	
	# Check if user can be notified
	is_notifiable = isnotifiable(thread_matched_users)
	
	# Generate notifications
	N = len(list_of_archive_links)
	for i in range(N):
		al = list_of_archive_links[i]
		if not al:
			# skip if the archive link is empty, i.e. it was not found
			# previously (such an event was logged)
			continue
			
		username = thread_matched_users[i]
		tn = thread_matched_names[i]
		
		if not is_notifiable[username]:
			#~ # Already logged when generating the "notifiability" list
			#~ logging.warning('User "{un}" is ineligible to notifications.'.format(un=username))
			continue
		
		notify(username,tn,al,istestrun=True)



if __name__ == '__main__':
    find_and_notify()
