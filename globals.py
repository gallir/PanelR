'Base configuration for the project'
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext.webapp import template

import sys
import os.path
import datamodel
import re
import hashlib
import datetime
import logging

_DEBUG = True
email_allowed = {"test@example.com": True}


service_icons = {
			"twitxr": "http://www.twitxr.com/favicon.ico",
			"rss": "/static/icons/services/feed.png",
			"chat": "/static/icons/services/comment.png",
			}

sys.path.insert(1, os.path.dirname(__file__)+'/external/')
sys.path.insert(1, os.path.dirname(__file__)+'/modules/')

templates = os.path.dirname(__file__)+'/templates/'

user = None
now = None

# Add our custom Django template filters to the built in filters
template.register_template_library('templatefilters')


def service_icon(service):
	try: return '<img src="%s" alt="%s" title="%s" width="16" height="16"/>' % (service_icons[service], service_icons[service], service_icons[service])
	except: return service

def init():
	"Check if the user is already in the db, otherwise create basic entries"
	global user, now
	
	now = datetime.datetime.now()
	current_user = users.get_current_user()
	if current_user:
		query = db.Query(datamodel.User)
		query.filter('user =', current_user)
		user = query.get()
		if not user:
			user = datamodel.User(user = current_user)
			user.api_key = hashlib.md5(current_user.email()+current_user.nickname()).hexdigest()[0:5]
			user.nick = re.sub('@', '.', user.user.nickname())
			if datamodel.AllowedUser.is_allowed(current_user.email()):
				user.put()
				logging.info("Addind user %s" % user.user.email())
			else:
				pass
				"""
				print "Location: /\n\n"
				sys.exit()
				"""
	else:
		user = None
