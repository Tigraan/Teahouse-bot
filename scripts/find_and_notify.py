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

from sections_removed_by_diff import sections_removed_by_diff
from parse_page_history import last_archival_edit,newsections_at_teahouse



def find_and_notify():
	# Get sections from last archival edit
	lae = last_archival_edit()
	idbefore = lae['before']
	idafter  = lae['after']
	archived_sections = sections_removed_by_diff(idbefore,idafter) #returns a set
	
	# Get new section creations from page history
	nscreated = newsections_at_teahouse() #returns a list of dict
	
	# Match the two
	thread_matched = 
	


def main(args):
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))
