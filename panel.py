# coding: utf-8

import globals
import logging

import wsgiref.handlers
from google.appengine.ext.webapp import template
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.api import users

import cgi
import time
import re
import gql_json

import datamodel
import services

class Panel(webapp.RequestHandler):
	def get(self, nick, panel_name='main'):
		user = datamodel.User.get_user(nick=nick)
		panel = datamodel.PanelList.get_panel(user=user, name=panel_name)
		#TODO: check access privileges
		template_data = {}
		template_data['panel_path'] = "/%s/panel/%s" % (nick, panel_name)
		template_data['panel_key'] = panel.key()
		if globals.user:
			if not datamodel.AllowedUser.is_allowed(globals.user.user.email()):
				self.redirect("/login")
			template_data['panel'] = panel
			template_data['owner'] = panel.user
			template_data['user'] = globals.user
			template_data['logout_link'] = users.create_logout_url("/")
			template_data['events'] = range(25)
			if globals.user == panel.user:
				template_data['check_service'] = True
			self.response.out.write(template.render(globals.templates+'panel.html', template_data))
		else:
			self.redirect(users.create_login_url(template_data['panel_path']))


class PanelJson(webapp.RequestHandler):
	def post(self, nick, panel_name='main', n=25):
		if n <=0 or n > 100: n = 25
		user = globals.user
		owner = datamodel.User.get_user(nick=nick)
		panel = datamodel.PanelList.get_panel(user=owner, name=panel_name)
		#TODO: check access privileges and that the panel is active
		""" Check reset command """
		if re.match('!reset', self.request.get('text')) and owner.nick == user.nick:
			q = db.GqlQuery("SELECT * FROM Event WHERE panel = :1", panel)
			results = q.fetch(1000)
			for r in results:
				r.delete()
			return
		event = datamodel.Event(panel=panel, user=user)
		#TODO: Check what's going on with accented and ñ's, it gives 
		# UnicodeDecodeError
		if self.request.charset: logging.info("Charset: " + self.request.charset)
		else: self.request.charset = 'utf8'
		try:
			event.text = db.Text(cgi.escape(self.request.get('text')))
		except UnicodeDecodeError:
			logging.info(cgi.escape(self.request.get('text')))
		event.type = 'chat'
		event.author = globals.user.nick
		event.put()
		self.write(user, panel, n)
		
	def get(self, nick, panel_name='main', n=25):
		if n <=0 or n > 100: n = 25
		user = datamodel.User.get_user(nick=nick)
		panel = datamodel.PanelList.get_panel(user=user, name=panel_name)
		#TODO: check access privileges and that the panel is active
		self.write(user, panel, n)

	def write(self, user, panel, n):
		events = datamodel.Event.get_events(panel, n=n, date=float(self.request.get('ts')))
		all = []
		for e in events:
			dict = {}
			dict['user'] = e.author
			#else: dict['user'] = e.user.nick
			dict['ts'] = float(time.mktime(e.date.timetuple()) + e.date.microsecond / 1000000.0)
			dict['text'] = e.text
			dict['url'] = e.url
			dict['icon'] = e.icon
			dict['type'] = globals.service_icon(e.type)
			try: dict['service'] = e.service.s_title
			except: pass
			all.append(dict)
		self.response.out.write(gql_json.encode(all))


class NewEvent(webapp.RequestHandler):
	def post(self, nick, panel_name = 'main'):
		self.get(nick, panel_name);
	def get(self, nick, panel_name = 'main'):
		user = datamodel.User.get_user(nick=nick)
		panel = datamodel.PanelList.get_panel(user=user, name=panel_name)
		#TODO: check access privileges and that the panel is active
		if globals.user:
			poster = globals.user
		else:
			poster = user

		if user and panel:
			event = datamodel.Event(panel=panel, user=user)
			event.text = cgi.escape(self.request.get('text'))
			type = cgi.escape(self.request.get('type'))
			icon = cgi.escape(self.request.get('icon'))
			url = cgi.escape(self.request.get('url'))
			if url:
				try: event.url = url
				except: self.response.out.write("error in url") 
			if icon:
				try: event.icon = icon
				except: self.response.out.write("error in icon") 
			if type:
				try: event.type = type
				except: self.response.out.write("error in type")
			event.put()
			if event.is_saved() and event.key():
				self.response.out.write("OK: " + str(event.key()) + "\n")
			else:
				self.response.out.write("KO: event not saved\n")
		else:
			self.response.out.write('KO: user or panel not found')


def main():
	application = webapp.WSGIApplication(
										[
										('/([\w\.]+)/panel/+(\w+)', Panel),
										('/([\w\.]+)/panel/+(\w+)/new', NewEvent),
										('/([\w\.]+)/panel/*(\w+)/json/*(\d*)', PanelJson),
										],
										debug=globals._DEBUG)
	globals.init()
	wsgiref.handlers.CGIHandler().run(application)


if __name__ == "__main__":
	main()
