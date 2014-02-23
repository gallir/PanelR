import globals
from google.appengine.ext import db
from google.appengine.api import users
import time
import datetime
import logging

class AllowedUser(db.Model):
	email = db.EmailProperty(required=True)
	
	@staticmethod
	def is_allowed(email):
		''' Allowed for all now'''
		return True
		try: return globals.email_allowed[email]
		except:
			query = db.Query(AllowedUser)
			query.filter('email =', email)
			return query.get()
	

class User(db.Model):
	user = db.UserProperty()
	nick = db.StringProperty()
	api_key = db.StringProperty()
	created = db.DateTimeProperty(auto_now_add = True)

	def __eq__(self, obj):
		return self.user == obj.user

	def __ne__(self, obj):
		return self.user != obj.user

	
	@staticmethod
	def get_user(**kwd):
		query = db.Query(User)
		for k in kwd:
			query.filter(k+' =', kwd[k])
		return query.get()

class PanelList(db.Model):
	user = db.Reference(User, required=True)
	name = db.StringProperty(default='main')
	created = db.DateTimeProperty(auto_now_add = True)
	modified = db.DateTimeProperty(auto_now = True)


	@staticmethod
	def get_current_lists():
		return PanelList.get_user_lists(users.GetCurrentUser())
	
	@staticmethod
	def get_user_lists(user):
		if not user: return []
		memberships = db.Query(PanelListMember).filter('user =', user)
		return [m.panel_list for m in memberships]

	@staticmethod
	def get_panel(**kwd):
		if not kwd.has_key('user'): return None
		if not kwd.has_key('name'): kwd['name'] = 'main'
		query = db.Query(PanelList)
		for k in kwd:
			query.filter(k+' =', kwd[k])
		return query.get()
	
	def current_user_has_access(self):
		return self.user_has_access(users.GetCurrentUser())
	
	def user_has_access(self, user):
		#TODO: check for anonymous
		if not user: return False
		query = db.Query(PanelListMember)
		query.filter('panel_list =', self).filter('user =', user)
		return query.get()

class PanelListMember(db.Model):
	user = db.UserProperty(required=True)
	panel_list = db.Reference(PanelList, required=True)
	created = db.DateTimeProperty(auto_now_add = True)


class UserService(db.Model):
	user = db.Reference(User, required=True)
	type = db.StringProperty(required=True)
	panel = db.Reference(PanelList, required=True)
	s_user = db.StringProperty()
	s_password = db.StringProperty()
	s_title = db.StringProperty()
	s_url = db.LinkProperty()
	last_checked = db.DateTimeProperty(auto_now = True)
	last_modified = db.DateTimeProperty()

	def put(self):
		if self._parent != self.panel:
			self._parent = self.panel
	 	super(UserService, self).put()
	save = put

	@staticmethod
	def get_services(user, **kwd):
		if not user: return []
		query = db.Query(UserService)
		query.filter('user =', user)
		for k in kwd:
			query.filter(k+' =', kwd[k])
		#query.order('s_title')
		return query.fetch(10)
	
	@staticmethod
	def get_panel_services(panel, **kwd):
		if not panel: return []
		query = db.Query(UserService)
		query.filter('panel =', panel)
		for k in kwd:
			query.filter(k+' =', kwd[k])
		query.order('last_checked')
		return query.fetch(10)


class Event(db.Model):
	panel = db.Reference(PanelList, required=True)
	date = db.DateTimeProperty(auto_now_add = True)
	user = db.Reference(User, required=True)
	service = db.Reference(UserService)
	type = db.StringProperty(default='chat')
	text = db.StringProperty()
	author = db.StringProperty()
	url = db.LinkProperty()
	icon = db.LinkProperty()
	image = db.LinkProperty()

	def put(self):
		if self._parent != self.panel:
			self._parent = self.panel
		super(Event, self).put()
	save = put
	
	"""
	def __setattr__(self, name, value):
		"It adds en epoch field (with microseconds) every time _date is modified"
		super(Event, self).__setattr__(name, value)
		if name == '_date':
			self.__dict__['epoch'] = float(time.mktime(value.timetuple()) + value.microsecond / 1000000.0)
	"""
	@staticmethod
	def get_events(panel, **kwd):
		if not panel: return []
		query = db.Query(Event)
		query.filter('panel =', panel)
		if kwd.has_key('date'):
			if kwd['date'].__class__ == float and kwd['date'] > 1000000:
				kwd['date'] = datetime.datetime.fromtimestamp(kwd['date'])
			if kwd['date'].__class__ == datetime.datetime:
				query.filter('date >', kwd['date'])
		if not kwd.has_key('n'):
			kwd['n'] = 50
		query.order('-date')
		results = query.fetch(kwd['n'])
		return results

class UserPrefs(db.Model):
	user = db.Reference(User, required=True)
	attr = db.StringProperty()
	value = db.StringProperty()
			


