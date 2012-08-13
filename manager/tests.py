"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test    import TestCase
from manager.models import Recipient

class RecipientTestCase(TestCase):
	def setUp(self):
		self.recipient = Recipient.objects.create(email_address='christopher.conover@ucf.edu')

	def test_hmac_hash(self):
		'''
			Make sure the hmac has is not blank and is 32 chars in length.
		'''
		hmac = self.recipient.hmac_hash
		self.assertTrue(hmac != '')
		self.assertTrue(len(hmac) == 32)