#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simple test for cron jobs etc."""

import datetime
from scripts import login
import sys

print(datetime.datetime.utcnow(), ' - test executed')
print('Python PATH is:', sys.path)
print('I will attempt to login via PWB')
login.main()
print('login.main() did not freeze')
