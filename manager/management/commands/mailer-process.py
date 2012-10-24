from django.core.management.base import BaseCommand
from manager.models              import Email
from datetime                    import datetime
import logging

log = logging.getLogger(__name__)


class Command(BaseCommand):
	'''
		Handles sending emails. Should be set to run according to the
		PROCESSING_INTERVAL_DURATION setting in settings_local.py
	'''

	def handle(self, *args, **options):
		now = datetime.now()

		for email in Email.objects.previewing_now(now=now):
			log.info('Previewing the following email now: %s ' % email.title)
			email.send_preview()

		for email in Email.objects.sending_now(now=now):
			log.info('Sending the following email now %s' % email.title)
			email.send()
