"""Django template filters for Panel."""

__author__ = 'Ricardo Galli'

import datetime
import time

from google.appengine.ext.webapp import template



def rfc3339date(date):
  """Formats the given date in RFC 3339 format for feeds."""
  if not date: return ''
  date = date + datetime.timedelta(seconds=-time.timezone)
  if time.daylight:
    date += datetime.timedelta(seconds=time.altzone)
  return date.strftime('%Y-%m-%dT%H:%M:%SZ')

def epochmicrodate(date):
	"""Formats the given date in epoch plus microseconds"""
	if not date: return ''
	return float(time.mktime(date.timetuple()) + date.microsecond / 1000000.0)

def epochdate(date):
	"""Formats the given date in epoch"""
	if not date: return ''
	return int(time.mktime(date.timetuple()))

def timedate(date):
  """Keep only time"""
  if not date: return ''
  date = date + datetime.timedelta(seconds=-time.timezone)
  if time.daylight:
    date += datetime.timedelta(seconds=time.altzone)
  return date.strftime('%H:%M:%S')


# Register the filter functions with Django
register = template.create_template_register()
register.filter(rfc3339date)
register.filter(epochmicrodate)
register.filter(epochdate)
register.filter(timedate)