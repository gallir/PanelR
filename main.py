import globals
import wsgiref.handlers
from google.appengine.ext.webapp import template
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.api import users


import datetime
import hashlib
import re
import time

import datamodel
import services



class MainPage(webapp.RequestHandler):
	def get(self):

		template_data = {}
		if globals.user:
			if not datamodel.AllowedUser.is_allowed(globals.user.user.email()):
				self.redirect("/login")
				return;
			template_data['greeting'] = 'Hi, ' + globals.user.nick
			template_data['user'] = globals.user
			template_data['logout_link'] = users.create_logout_url("/")
			events = db.GqlQuery("SELECT * FROM Event WHERE user=:1 ORDER BY date DESC LIMIT 5", globals.user)
			template_data['events'] = events
		else:
			template_data['greeting'] = 'Hi, anonymous'
			template_data['login_link'] = users.create_login_url("/login")
		self.response.out.write(template.render(globals.templates + 'main.html', template_data))

class UserPage(webapp.RequestHandler):
	def get(self, nick):

		template_data = {}
		services = {}
		if globals.user:
			if not datamodel.AllowedUser.is_allowed(globals.user.user.email()):
				self.redirect("/login")
				return;
			template_data['greeting'] = 'Hi, find below your own panels'
			template_data['user'] = globals.user
			template_data['logout_link'] = users.create_logout_url("/")
			panels = datamodel.PanelList.get_current_lists()
			template_data['panels'] = panels
			services = datamodel.UserService.get_services(globals.user)
			services.sort(key=lambda obj:obj.s_title)
			template_data['services'] = services
		else:
			template_data['login_link'] = users.create_login_url("/login")
		self.response.out.write(template.render(globals.templates + 'user.html', template_data))


class LoginPage(webapp.RequestHandler):
	"This is called when a user log-in"
	def get(self):
		template_data = {}
		if globals.user:
			if not datamodel.AllowedUser.is_allowed(globals.user.user.email()):
				template_data['user'] = globals.user
				template_data['greeting'] = 'Access denied for non authorized users'
				template_data['logout_link'] = users.create_logout_url("/")
				self.response.out.write(template.render(globals.templates + 'noauthorized.html', template_data))
			else:
				""" Check if it has basic info and first panel """
				query = db.Query(datamodel.User)
				query.filter('user =', globals.user.user)
				user = query.get()
				query = db.Query(datamodel.PanelList)
				query.filter('user =', user).filter('name =', 'main')
				panel = query.get()
				if not panel:
					panel = datamodel.PanelList(user=user, name='main')
					panel.put()
					membership = datamodel.PanelListMember(user=globals.user.user, panel_list=panel)
					membership.put()
				self.redirect('/' + globals.user.nick)
		else:
			template_data['greeting'] = 'Access denied for anonymous users'
			self.response.out.write(template.render(globals.templates + 'noauthorized.html', template_data))




def main():
	application = webapp.WSGIApplication(
										[
										('/*', MainPage),
										('/login', LoginPage),
										('/([\w\.]+)/*$', UserPage),
										('/([\w\.]+)/services/check', services.Check),
										('/([\w\.]+)/services/rss', services.Rss),
										('/([\w\.]+)/services/twitter', services.Twitter),
										],
										debug=True)

	#wsgiref.handlers.CGIHandler().run(application)
	run_wsgi_app(application)



if __name__ == "__main__":
	main()
