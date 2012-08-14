"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test    import TestCase
from manager.models import Recipient, RecipientAttribute, RecipientGroup, Email
from django.conf    import settings
from datetime       import datetime, timedelta

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
		self.email = Email.objects.create(
			active             = True,
			title              = 'Test Email',
			subject            = 'Test Email Subject',
			source_uri         = settings.TEST_EMAIL_SOURCE_URI,
			start_date         = now.date(),
			send_time          = str((now + timedelta(5 * 60)).time()).split('.')[0],
			recurrence         = 0, # Never
			from_email_address = 'webcom@ucf.edu',
			from_friendly_name = 'Web Communications Team',
			track_urls         = True,
			track_opens        = True,
			preview            = True,
			preview_recipients = settings.TEST_EMAIL_RECIPIENT
			)
		self.email.recipient_groups.add(self.group)

	def test_sending(self):
		self.email.send()