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

import logging, os, sys

from parse_page_content import last_archival_edit,sections_removed_by_diff,newsections_at_teahouse,search_archive_links_for_section
from utilities import list_matching, api_call, whoami
from userinfo import isnotifiable

# We need pywikibot and the add_text script
# Directory "core" from https://gerrit.wikimedia.org/r/pywikibot/core.git
# must be available on the Python path.
# We add it on the Python path at runtime.

# The problem with PWB is that at load time it tries to read a config file.
# This config file needs to be found at load time. For that, it needs to
# be either in the current working directory, or in $HOME/.pywikibot.
# It is NOT enough that it is in the directory from which PWB is imported.
# Cf. https://en.wikipedia.org/wiki/Wikipedia:Bots/Requests_for_approval/Tigraan-testbot

# Directory for 'core' package containing the PWB framework
path_to_PWB = os.path.expandvars('$HOME/.local/lib/python3.5/site-packages/core')

sys.path.append(path_to_PWB) # add path to pwb to find the modules11

import pywikibot
from scripts import add_text,login # the pieces of pywikibot that we need to call

#END OF HORRIBLE HACK#

def generate_notification_list():

	# Get last archival edit
	lae = last_archival_edit()
	idbefore = lae['before']
	idafter  = lae['after']
	# Sections from last archival edit
	archived_sections = sections_removed_by_diff(idbefore,idafter) #set
	
	# New section creations in recent days from page history
	maxpagestopull = 5
	nscreated = newsections_at_teahouse(maxcontinuenumber=maxpagestopull) #list of dict
	
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
	
	# Generate notification list
	N = len(list_of_archive_links)
	notification_list = list()
	for i in range(N):
		username = thread_matched_users[i]
		tn = thread_matched_names[i]
		al = list_of_archive_links[i]
		
		
		notif = {'user' : username,
			'thread' : tn,
			'invalid': False,
			}
		
		if al:
			notif['archivelink'] = al
			
		else:
			# skip if the archive link is empty, i.e. it was not found
			# previously (such an event was logged)
			notif['invalid']=True
			notif['reason']='archive link not found'
			
		
		if not is_notifiable[username]:
			notif['invalid']=True
			notif['reason']='user is not notifiable'
			#~ # The next warning is superfluous: this was already logged
			#~ # when generating the "notifiability" list
			#~ logging.warning('User "{un}" is ineligible to notifications.'.format(un=username))
		
		
		notification_list.append(notif)
		
	return notification_list



def notify(user,argstr,teststep):
	if teststep==1:
		
		site = pywikibot.Site('test','test')
		page = pywikibot.Page(site, 'User talk:Tigraan-testbot/THA log')
		section_name = 'Notification intended for [[:en:User talk:' + user + ']]'
		es = 'Notification intended for [[:en:User talk:' + user + ']]'
	
	elif teststep==2:
	
		site = pywikibot.Site('en','wikipedia')
		page = pywikibot.Page(site, 'User talk:Tigraan-testbot/THA log')
		section_name = 'Notification intended for [[:en:User talk:' + user + ']]'
		es = 'Notification intended for [[:en:User talk:' + user + ']]'
	
	elif teststep==3:
		site = pywikibot.Site('en','wikipedia')
		page = pywikibot.Page(site, 'User talk:' + user)
		section_name = 'Your thread has been archived'
		es = 'Automated notification of thread archival (test run)'
			
	elif teststep==0:
		#put production code here
		if False:			
			site = pywikibot.Site('en','wikipedia')
			page = pywikibot.Page(site, 'User talk:' + user)
			section_name = 'Your thread has been archived'
			es = 'Your thread has been archived'

	# 0 for production, all the rest creates a "this is in test phase" comment
	if teststep>0:
		test_comment = "</br><small>This functionality is currently being tested. If you received this notification by error, please [[User talk:Tigraan|notify the bot's maintainer]].</small>"
		text = '{{subst:User:Tigraan-testbot/Teahouse archival notification|' + argstr + '|additionaltext=' + test_comment + '}}'
	else:
		text = '{{subst:User:Tigraan-testbot/Teahouse archival notification|' + argstr + '}}'
		
	post_text = '=={sn}==\n{tta}'.format(sn=section_name,tta=text)
		
	#~ add_text.add_text(page, post_text, summary=section_name,
             #~ always=False, up=False, create=True)
	# Caution: will not ask for confirmation!
	add_text.add_text(page, post_text, summary=es,
             always=True, up=False, create=True)
	
	

def notify_all(notification_list,status,archive_from='[[Wikipedia:Teahouse]]',botname='Tigraan-testbot'):

	formatspec='pagelinked={pl}|threadname={tn}|archivelink={al}|botname={bn}|editorname={en}'
	warnmsg = 'Thread "{thread}" by user {user} will not cause notification: {reason}.'
	for item in notification_list:
		user = item['user']
		thread = item['thread']
		
		if item['invalid']:
			logging.warning(warnmsg.formatspec(thread=thread,user=user,reason=item['reason']))
			continue
		archivelink = item['archivelink']
		
		argstr = formatspec.format(pl=archive_from,tn=thread,al=archivelink,bn=botname,en=user)
				
		
		if status=='offlinetest':
			print('[[User talk:' + user + ']] -> {{subst:User:Tigraan-testbot/Teahouse archival notification|' + argstr + '}}')
		elif status=='test-1':
			notify(user,argstr,teststep=1)
		elif status=='test-2':
			notify(user,argstr,teststep=2)
		elif status=='test-3':
			notify(user,argstr,teststep=3)
		elif status=='prod':
			notify(user,argstr,teststep=0)
		else:
			raise ValueError('Option was not understood.', status)

def main():
	
	# log in
	login.main() #login as Tigraan-testbot
	
	notiflist = generate_notification_list()
	
	notify_all(notiflist,status='test-3')
	login.main('-logout') #logout
	print(whoami())
if __name__ == '__main__':
	main()
