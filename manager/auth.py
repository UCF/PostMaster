from django.conf                  import settings
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models   import User
from django.core.exceptions       import ImproperlyConfigured
from util                         import LDAPHelper

import logging

class Backend(ModelBackend):

	def authenticate(self, request, username=None, password=None):

		if username not in settings.MANAGERS:
			return None

		try:
			ldap_helper = LDAPHelper()
			LDAPHelper.bind(ldap_helper.connection,username,password)
			ldap_user = LDAPHelper.search_single(ldap_helper.connection,username)
		except LDAPHelper.LDAPHelperException as e:
			logging.error('LDAP Error: %s' % e)
			return None
		else:
			try:
				user = User.objects.get(username=username)
			except User.DoesNotExist:
				user = User(username=username)

				# Try to extract some other details
				try:
					user.first_name = LDAPHelper.extract_firstname(ldap_user)
				except LDAPHelper.MissingAttribute:
					pass
				try:
					user.last_name = LDAPHelper.extract_lastname(ldap_user)
				except LDAPHelper.MissingAttribute:
					pass
				try:
					user.email = LDAPHelper.extract_email(ldap_user)
				except LDAPHelper.MissingAttribute:
					pass

				try:
					user.save()
				except Exception as e:
					logging.error('Unable to save user `%s`: %s' % (username,str(e)))
					return None
		return user

	def get_user(self, user_id):
		try:
			return User.objects.get(pk=user_id)
		except User.DoesNotExist:
			return None
