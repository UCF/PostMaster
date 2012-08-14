"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test    import TestCase
from manager.models import Recipient, RecipientAttribute, RecipientGroup

class RecipientTestCase(TestCase):
	def setUp(self):
		self.recipient = Recipient.objects.create(email_address='christopher.conover@ucf.edu')
		self.attribute = RecipientAttribute.objects.create(
			recipient=self.recipient,
			name='first_name',
			value='Chris')
		self.group     = RecipientGroup.objects.create(name='Test Group')

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
		self.assertEqual(self.recipient.first_name, 'Chris')

	def test_missing_attribute(self):
		with self.assertRaises(AttributeError):
			self.recipient.blah