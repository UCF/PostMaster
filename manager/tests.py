"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test              import TestCase, Client
from manager.models           import *
from django.conf              import settings
from datetime                 import datetime, timedelta
from util                     import calc_url_mac, calc_open_mac, calc_unsubscribe_mac
from django.core.urlresolvers import reverse
from django.http              import HttpResponseRedirect
from django.core.exceptions   import SuspiciousOperation
import urllib

class RecipientTestCase(TestCase):
	def setUp(self):
		self.recipient = Recipient.objects.create(email_address=settings.TEST_EMAIL_RECIPIENT)
		self.attribute = RecipientAttribute.objects.create(
			recipient=self.recipient,
			name='first_name',
			value='Test Recipient')
		self.group     = RecipientGroup.objects.create(name='Test Group')
		self.group.recipients.add(self.recipient)

	def test_hmac_hash(self):
		'''
			Make sure the hmac has is not blank and is 32 chars in length.
		'''
		hmac = self.recipient.hmac_hash
		self.assertTrue(hmac != '')
		self.assertTrue(len(hmac) == 32)

	def test_subscriptions(self):
		'''
			Should be zero here
		'''
		self.assertTrue(len(self.recipient.subscriptions) == 0)

	def test_existing_attribute(self):
		self.assertEqual(self.recipient.first_name, 'Test Recipient')

	def test_missing_attribute(self):
		with self.assertRaises(AttributeError):
			self.recipient.blah

class EmailTestCase(TestCase):
	def setUp(self):
		now = datetime.now()

		self.recipient = Recipient.objects.create(email_address=settings.TEST_EMAIL_RECIPIENT)
		self.attribute = RecipientAttribute.objects.create(
			recipient=self.recipient,
			name='First Name',
			value='Test Recipient')
		
		self.group     = RecipientGroup.objects.create(name='Test Group')
		self.group.recipients.add(self.recipient)

		self.second_group = RecipientGroup.objects.create(name='Test Group 1')
		self.group.recipients.add(self.recipient)

		self.email = Email.objects.create(
			active             = True,
			title              = 'Test Email',
			subject            = 'Test Email Subject',
			source_uri         = settings.TEST_EMAIL_SOURCE_URI,
			start_date         = now.date(),
			send_time          = (now + timedelta(5 * 60)).time(),
			recurrence         = 0, # Never
			from_email_address = 'webcom@ucf.edu',
			from_friendly_name = 'Web Communications Team',
			track_urls         = True,
			track_opens        = True,
			preview            = True,
			preview_recipients = settings.TEST_EMAIL_RECIPIENT
			)
		self.email.recipient_groups.add(self.group)
		self.email.recipient_groups.add(self.second_group)

	def _test_url_tracking(self, instance):
		'''
			Test the URL tracking. Must be called in the context of an email instance.
		'''
		# Is the URL Tracking working?
		urls = URL.objects.all()
		if urls.count() == 0:
			raise AssertionError('There must be at least 1 URL is the email content')
		else:
			client   = Client()

			# Make sure this is valid URL for redirection
			test_url = None
			for url in urls:
				try:
					HttpResponseRedirect(url.name)
				except SuspiciousOperation:
					continue
				else:
					test_url = url
			if test_url is None:
				raise AssertionError('No valid test URL found.')

			response = client.get('?'.join([
				reverse('manager-email-redirect'),
				urllib.urlencode({
					'instance'  :instance.pk,
					'recipient' :self.recipient.pk,
					'url'       :urllib.quote(test_url.name),
					'position'  :test_url.position,
					'mac'       :calc_url_mac(test_url.name, test_url.position, self.recipient.pk, instance.pk)
				})
			]))
			self.assertTrue(response.status_code == 302)

			clicks = URLClick.objects.all()
			self.assertTrue(clicks.count() == 1)

	def _test_open_tracking(self, instance):
		'''
			Test the open tracking. Must be called in the context of an email instance.
		'''
		client   = Client()
		response = client.get('?'.join([
			reverse('manager-email-open'),
			urllib.urlencode({
				'recipient':self.recipient.pk,
				'instance' :instance.pk,
				'mac'      :calc_open_mac(self.recipient.pk, instance.pk)
			})
		]))
		self.assertTrue(response.status_code == 200)
		opens = InstanceOpen.objects.all()
		self.assertTrue(opens.count() == 1)

	def _test_unsubscribe(self, instance):
		'''
			Test the unsubcribe functionality. Must be called in the context of an email instance.
		'''
		client   = Client()
		response = client.get('?'.join([
			reverse('manager-email-unsubscribe'),
			urllib.urlencode({
				'recipient':self.recipient.pk,
				'email'    :instance.email.pk,
				'mac'      :calc_unsubscribe_mac(self.recipient.pk, instance.email.pk)
			})
		]))
		self.assertTrue(response.status_code == 200)
		self.assertTrue(self.email.unsubscriptions.count() == 1)
		self.email.unsubscriptions.clear()

	def _test_email_send(self):
		'''
			Test sending the email.
		'''
		self.email.send()
		
		self.assertTrue(Instance.objects.count() == 1)
		self.assertTrue(URL.objects.count() > 0)
		self.assertTrue(InstanceRecipientDetails.objects.count() == 1)
		return Instance.objects.all()[0]

	def test_sending_urls_opens(self):
		'''
			Test sending the email, url tracking and open tracking.
		'''
		
		instance = self._test_email_send()
		self._test_url_tracking(instance)
		self._test_open_tracking(instance)
		self._test_unsubscribe(instance)
	def test_sending_url(self):
		'''
			Test sending the email with URL tracking only.
		'''
		instance = self._test_email_send()
		self._test_url_tracking(instance)
		self._test_unsubscribe(instance)

	def test_sending_open(self):
		'''
			Test sending the email with open tracking only.
		'''
		instance = self._test_email_send()
		self._test_open_tracking(instance)
		self._test_unsubscribe(instance)

	def test_sending(self):
		'''
			Test sending the email wit no tracking.
		'''
		instance = self._test_email_send()
		self._test_unsubscribe(instance)

	def test_preview(self):
		send_time = self.email.send_time
		self.email.send_time = (datetime.now() + timedelta(seconds=settings.PREVIEW_LEAD_TIME + 30)).time()
		self.email.save()
		self.email.send_preview()