#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  design_skeleton.py
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

#~ All Python function in this module are empty. This is used as design 
#~ notes to know what has to be coded.


def last_archival_edit(page='Wikipedia:Teahouse',archiver='Lowercase sigmabot III'):
	'''Finds last archival edit.

	Searches the target page for the last edit by the target user,
	returns the text of the edit (diff) and the edit summary.
	The latter should include links to the archival location.'''
	return text_diff, edit_summary

def archived_threads_list(archiving_diff):
	'''Splits archival edit in threads.
	
	Parses the input chunk of text to determine section headers.'''
	return list_of_section_headers
	
	
def check_ns_threads_in_page_history(page='Wikipedia:Teahouse',max_age_in_days=20):
	'''Returns the last "new section" threads in page history.
	
	Output list contains pairs (thread_title, OP).'''
	return list_of_threads


def match_archive_with_creation(list_of_archived_threads,list_of_created_sections):
	'''Matches thread names at creation and at archival.
	
	If uniquely matched, return thread name and OP in pairs.'''
	return list_of_matched_threads
	
	
def check_duplicate_OPs_in_archival(list_of_matched_threads):
	'''Checks for duplicate OPs to avoid multiple notifications.
	
	Returns a list of pairs OP/name of thread(s), the OP entries
	being unique.'''
	return tonotify_list
	
def check_user_should_be_notified(username):
	'''Checks whether a note can be left to a particular user.
	
	Criteria still to define, but should include not to notify IPs,
	blocked editors, editors with tenure (more than X edits /
	more than access level Y), editors who set up bot exclusion.
	Returns a boolean (true -> can be notified).'''
	return notifiable_flag
	
	
def read_archive_parameters(page='Wikipedia:Teahouse'):
	'''Read archival parameters.
	
	This is needed for the notice generation.'''
	return archive_maxage
	
def generate_notification(origin_page='Wikipedia:Teahouse',thread_names,archive_maxage,archive_lookup):
	'''Generate note to leave on talk page.
	
	Branch out depending of the length of thread_names.
	archive_maxage is used so that the user knows how old threads
	can get before archival.
	archive_lookup contains the information to find the archive URL,
	extracted from the archival edit summary.'''
	return notification_text

def post_notification(user,notification_text):
	'''Leave note on the talk page.
	
	This part should not be active before all the rest has been tested!'''
	

def main(args):
	#Still to be coded
    return None

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))
