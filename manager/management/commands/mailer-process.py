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
		log.info('The mailer-process command is starting...')

		now       = datetime.now()
		previews  = Email.objects.previewing_now(now=now)
		instances = Email.objects.sending_now(now=now)

		log.info('There is/are %d preview(s) to send.' % len(previews))
		for email in previews:
			log.info('Previewing the following email now: %s ' % email.title)
			email.send_preview()

		log.info('There is/are %d instance(s) to send.' % len(instances))
		for email in instances:
			log.info('Sending the following email now %s' % email.title)
			email.send()

		log.info('The mailer-process command is finished.')