from google.appengine.ext import db
from google.appengine.ext import webapp

import wsgiref.handlers

import globals
import datamodel
import feedparser
import datetime
import time
import cgi
import re
import logging

from google.appengine.api import urlfetch
from xml.dom import minidom


class Delete(webapp.RequestHandler):
	def get(self, nick, key):
		if globals.user.nick != nick:
			self.response.out.write("Error: users does no match " + nick)
			return
		try:
			service = db.get(db.Key(key))
			if not service: return
			q = db.GqlQuery("SELECT * FROM Event WHERE service = :1", service)
			results = q.fetch(100)
			for r in results:
				r.delete()
			service.delete()
			self.response.out.write("OK")
		except Exception, e:
			self.response.out.write("Error (%s) deleting key %s" % (e, key))
		


class Check(webapp.RequestHandler):
	def get(self, nick, panel_key):
		if globals.user.nick != nick:
			self.response.out.write("Error: users does no match " + nick)
			return
		panel = datamodel.PanelList.get(panel_key)
		services = datamodel.UserService.get_panel_services(panel)
		counter = 0
		for s in services:
			if self.must_ignore(s): continue
			s.put()
			try:
				counter += Check.__dict__[s.type+'_check'](self, s)
			except Exception, e:
				logging.warning("Exception %s while executing %s" % (e, s.s_title))
			if counter > 0: return
		if counter == 0:
			"Delete old events"
			q = db.GqlQuery("SELECT * FROM Event WHERE date < :1", globals.now - datetime.timedelta(days=1))
			results = q.fetch(100)
			for r in results:
				r.delete()
			
	def must_ignore(self, service):
		if service.last_modified:
			since_last_check = globals.now-service.last_checked
			if since_last_check.seconds < 60: return True
			since_last_update = globals.now-service.last_modified
			if since_last_check.seconds < 300 and since_last_check.seconds < since_last_update.seconds // 10:
				return True
		return False

	def twitter_check(self, service):
		self.response.out.write("twitter called, %s %s" % (service.s_user, service.s_password))
		return 0

	def twitxr_check(self, service):
		now = datetime.datetime.now()
		events = []
		url = "http://twitxr.com/api/rest/getFriendsTimeline?user=%s" % service.s_user
		if service.last_modified:
			last_modified = service.last_modified
		else:
			last_modified = now - datetime.timedelta(hours=24)
		last_date = False
		order = 0
		timestamp = int(time.mktime(last_modified.timetuple()))
		url = "%s&since=%s" % (url, timestamp)
			#self.response.out.write(last_modified.isoformat(' ')+"\n")
		try:
			result = urlfetch.fetch(url)
			logging.info("Fetching: %s (%s)" % (url, datetime.datetime.fromtimestamp(timestamp)))
		except: pass
		if result.status_code == 200:
			doc = minidom.parseString(result.content)
			updates = doc.getElementsByTagName('update')
			for u in updates:
				try:
					user = u.getElementsByTagName('user')[0].firstChild.data
					text = u.getElementsByTagName('text')[0].firstChild.data
					url = u.getElementsByTagName('url')[0].firstChild.data
					date = datetime.datetime.fromtimestamp(int(u.getElementsByTagName('timestamp')[0].firstChild.data))
					avatar = u.getElementsByTagName('avatar')[0].firstChild.data
					try: picture = u.getElementsByTagName('picture')[0].firstChild.data
					except: picture = None
					if last_date:
						"Detect the date order -1 = descending, 1 = ascending"
						if date > last_date: order = 1
						elif date < last_date: order -1
					last_date = date
				except Exception, e:
					logging.warning("Exception %s while parsing twitxr" % e)
					continue
				if date > last_modified:
					last_modified = date
					event = datamodel.Event(parent=service, panel=service.panel, user=service.user, 
										service=service)
					event.type = 'twitxr'
					event.url = cgi.escape(url)
					event.icon = cgi.escape(avatar)
					if picture: event.image = cgi.escape(picture)
					event.author = cgi.escape(user)
					event.text = cgi.escape(text)
					try: event.date = now + datetime.timedelta(microseconds=(100+order))
					except:	event.date = now
					events.append(event)
					last_date = date
				if len(events) > 10: 
					break
			if not service.last_modified or len(events) > 0:
				for e in events:
					e.put()
				try: service.last_modified = last_modified
				except: service.last_modified = now
				service.put()
			return 1
		return 0


	def rss_check(self, service):
		now = datetime.datetime.now()
		if service.last_modified:
			last_modified = service.last_modified
		else:
			last_modified = now - datetime.timedelta(hours=2)
		last_date = False
		order = 0
		headers = {}
		events = []
		headers['If-Modified-Since'] = last_modified.isoformat(' ') + " UTC"
		logging.info("Fetching: %s (%s)" % (service.s_url, headers['If-Modified-Since']))
		result = urlfetch.fetch(service.s_url, headers=headers)
		if result.status_code == 200:
			result.content = re.sub('media:title', 'to_ignore', result.content)
			doc = feedparser.parse(result.content)
			for e in doc['entries']:
				#WARN: there is a bug somewhere in feedparser or rf822 or time.xxx
				#It works fine in Google
				#TODO: checkit later
				try:
					#Only fails in local
					#date = datetime.datetime.utcfromtimestamp(int(time.mktime(e.updated_parsed)-3600))
					
					date = datetime.datetime.utcfromtimestamp(int(time.mktime(e.updated_parsed)))
					if last_date:
						"Detect the date order -1 = descending, 1 = ascending"
						if date > last_date: order += 1
						elif date < last_date: order -= 1
					last_date = date
					text = cgi.escape(e.title)
					url = cgi.escape(e.link)
					try: author = cgi.escape(e.author)
					except: author = None
				except (AttributeError, TypeError, NameError, UndeclaredNamespace, ValueError), e: 
					logging.warning("Exception %s while parsing RSS" % e)
					continue

				#self.response.out.write("string: %s original: %s time: %s date: %s\n" %(e.updated, e.updated_parsed,time.mktime(e.updated_parsed), date ))
				if date > last_modified:
					last_modified = date

					event = datamodel.Event(parent=service, panel=service.panel, user=service.user, 
										service=service)
					event.type = 'rss'
					event.url = url
					event.author = author
					event.text = text
					try: event.date = now + datetime.timedelta(microseconds=(100+order))
					except:	event.date = now
					events.append(event)
				elif last_date and order < 0:
#					logging.info("Stopped due to date")
					break
				if len(events) > 10: 
#					logging.info("Stopped due to excess of items")
					break
			if not service.last_modified or len(events) > 0:
				for e in events:
					e.put()
				try: service.last_modified = last_modified
				except: service.last_modified = now
				service.put()
			return 1
		return 0


class Rss(webapp.RequestHandler):
	def post(self, nick):
		panel = datamodel.PanelList.get_panel(user=globals.user, name=self.request.get('panel'))
		if not panel:
			self.response.out.write("error reading panel")
			return
		form_nick = self.request.get('nick')
		form_title = self.request.get('title')
		form_url = self.request.get('url')
		if nick != globals.user.nick or form_nick != nick:
			self.response.out.write("users does not match %s - %s - %s" % (globals.user.nick, nick, form_nick))
			return
		q = db.GqlQuery("SELECT * FROM UserService WHERE user = :1 AND type = :2 AND s_url = :3", globals.user, 'rss', form_url)
		results = q.fetch(10)
		for r in results:
			r.delete()
		service = datamodel.UserService(user=globals.user, panel=panel, type='rss', s_title=form_title, s_url = form_url)
		service.put()
		if service.key():
			self.redirect('/'+nick)
		else:
			self.response.out.write("error saving")

class Twitxr(webapp.RequestHandler):
	def post(self, nick):
		panel = datamodel.PanelList.get_panel(user=globals.user, name=self.request.get('panel'))
		if not panel:
			self.response.out.write("error reading panel")
			return
		form_nick = self.request.get('nick')
		form_title = self.request.get('title')
		form_user = self.request.get('user')
		if nick != globals.user.nick or form_nick != nick:
			self.response.out.write("users does not match %s - %s - %s" % (globals.user.nick, nick, form_nick))
			return
		q = db.GqlQuery("SELECT * FROM UserService WHERE user = :1 AND type = :2 AND s_user = :3", globals.user, 'twitxr', form_user)
		results = q.fetch(10)
		for r in results:
			r.delete()
		service = datamodel.UserService(user=globals.user, panel=panel, type='twitxr', s_title='twitxr:'+form_user, s_user = form_user)
		service.put()
		if service.key():
			self.redirect('/'+nick)
		else:
			self.response.out.write("error saving")

class Twitter(webapp.RequestHandler):
	def post(self, nick):
		form_nick = self.request.get('nick')
		form_user = self.request.get('user')
		form_password = self.request.get('password')
		if nick != globals.user.nick or form_nick != nick:
			self.response.out.write("users does not match %s - %s - %s" % (globals.user.nick, nick, form_nick))
			return
		q = db.GqlQuery("SELECT * FROM UserService WHERE user = :1 AND type = :2 AND s_user = :3", globals.user, 'twitter', form_user)
		results = q.fetch(10)
		for r in results:
			r.delete()
		service = datamodel.UserService(user=globals.user, type='twitter', s_user=form_user, s_password=form_password)
		service.put()
		if service.key():
			self.redirect('/'+nick)
		else:
			self.response.out.write("error saving")


def main():
	application = webapp.WSGIApplication(
										[
										('/([\w\.]+)/services/op/delete/(.+)', Delete),
										('/([\w\.]+)/services/panel_check/(\w+)', Check),
										('/([\w\.]+)/services/rss', Rss),
										('/([\w\.]+)/services/twitter', Twitter),
										('/([\w\.]+)/services/twitxr', Twitxr),
										],
										debug=globals._DEBUG)
	globals.init()
	wsgiref.handlers.CGIHandler().run(application)


if __name__ == "__main__":
	main()
