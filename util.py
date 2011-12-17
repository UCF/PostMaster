from django.conf import settings
import json
try:
	import requests
except ImportError:
	print 'This script utilizes the `requests` package.'
	print 'Download and install it from http://pypi.python.org/pypi/requests'


class MailChimpSTS(object):
	'''
		Implements basic connectivity to the MailChimp STS API.

		https://apidocs.mailchimp.com/sts/1.0/
	'''

	API_KEY  = settings.MAILCHIMP.API_KEY
	ENDPOINT = settings.MAILCHIMP.END_POINT

	#class ServiceError(Exception):
	#	def __init__(self, message):
	#		self.message = message
	#	def __str__(self):
	#		return repr(self.message)

	def __init__(self, *args, **kwargs):
		pass
	
	# Utility
	@classmethod
	def send_request(cls, method, **params):
		action = '.'.join([method, 'json'])
		uri    = '/'.join([MailChimpSTS.ENDPOINT, action])
		params['apikey'] = MailChimpSTS.API_KEY
		return json.loads(requests.post(uri,data=params).content)

	# Email Verification
	@classmethod
	def delete_verified_email_address(cls, email):
		'''
			http://apidocs.mailchimp.com/sts/1.0/deleteverifiedemailaddress.func.php
		'''
		return MailChimpSTS.send_request('DeleteVerifiedEmailAddress', email=email)
	
	@classmethod
	def list_verified_email_addresses(cls):
		'''
			http://apidocs.mailchimp.com/sts/1.0/listverifiedemailaddresses.func.php
		'''
		return MailChimpSTS.send_request('ListVerifiedEmailAddresses')

	@classmethod
	def verify_email_address(cls, email):
		'''
			http://apidocs.mailchimp.com/sts/1.0/verifyemailaddress.func.php
		'''
		return MailChimpSTS.send_request('VerifyEmailAddress', email=email)
	
	# MailChimp Stats Methods
	@classmethod
	def get_bounces(cls, since=''):
		'''
			http://apidocs.mailchimp.com/sts/1.0/getbounces.func.php
		'''
		return MailChimpSTS.send_request('GetBounces', since=since)

	@classmethod
	def get_send_stats(cls, tag_id='_all', since=''):
		'''
			http://apidocs.mailchimp.com/sts/1.0/getsendstats.func.php
		'''
		return MailChimpSTS.send_request('GetSendStats', tag_id=tag_id, since=since)
		
	@classmethod
	def get_tags(cls):
		'''
			http://apidocs.mailchimp.com/sts/1.0/gettags.func.php
		'''
		return MailChimpSTS.send_request('GetTags')

	@classmethod
	def get_url_stats(cls, url_id='', since=''):
		'''
			http://apidocs.mailchimp.com/sts/1.0/geturlstats.func.php
		'''
		return MailChimpSTS.send_request('GetUrlStats', url_id=url_id,since=since)

	@classmethod
	def get_urls(cls):
		'''
			http://apidocs.mailchimp.com/sts/1.0/geturls.func.php
		'''
		return MailChimpSTS.send_request('GetUrls')
	
	# Sending
	@classmethod
	def send_email(cls, message, track_opens=False, track_clicks=False, tags=[]):
		'''
			http://apidocs.mailchimp.com/sts/1.0/sendemail.func.php
		'''
		# The message and tags parameters have to be converted into a 
		# index-based array like structure to  be processed correctly 
		# the MailChimp API
		encoded_params = {}
		message_array_params = (
			'reply_to',
			'to_email',
			'to_name',
			'cc_email',
			'cc_name',
			'bcc_email',
			'bcc_name'
		)
		for key,param in message.items():
			# Arrays
			if key in message_array_params:
				for index, value in zip(range(0, len(param)), param):
					encoded_params['message[' + key + '][' + str(index) + ']'] = value
			else:
				encoded_params['message[' + key + ']'] = param
		
		for index,value in zip(range(0,len(tags)), tags):
			encoded_params['tags[' + str(index) + ']'] = value

		encoded_params['track_opens']  = track_opens
		encoded_params['track_clicks'] = track_clicks
		
		return MailChimpSTS.send_request('SendEmail', **encoded_params)
	
	# Stats
	@classmethod
	def  get_send_quota(cls):
		'''
			http://apidocs.mailchimp.com/sts/1.0/getsendquota.func.php
		'''
		return MailChimpSTS.send_request('GetSendQuota')
	
	@classmethod
	def get_send_statistics(cls):
		'''
			http://apidocs.mailchimp.com/sts/1.0/getsendstatistics.func.php
		'''
		return MailChimpSTS.send_request('GetSendStatistics')
