#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  utc_timestamps.py
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

import datetime

def UTC_timestamp_x_days_ago(days_offset=0):
	'''Timestamp x days ago in Mediawiki format.
	
	Input is the number of days that will be substracted from the
	current timestamp.
	Format: cf. https://www.mediawiki.org/wiki/Manual:Timestamp'''
	
	current_time = datetime.datetime.utcnow()#UTC time on MediaWiki servers
	offset = datetime.timedelta(days=-days_offset)
	UTC_time_then = current_time + offset
	
	timestamp = UTC_time_then.strftime("%Y%m%d%H%M%S")
	return timestamp


	
	
#~ # Tests of individual subfunctions
a=UTC_timestamp_x_days_ago(0)
b=UTC_timestamp_x_days_ago(1)
c=UTC_timestamp_x_days_ago(30)
print(a)
print(b)
print(c)

