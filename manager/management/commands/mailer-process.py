from django.core.management.base import BaseCommand
from manager.models              import Email
from datetime                    import datetime
log = logging.getLogger(__name__)


class Command(BaseCommand):
	'''
		Handles sending emails. Should be set to run according to the
		PROCESSING_INTERVAL_DURATION setting in settings_local.py
	'''

	def handle(self, *args, **options):
		now = datetime.now()

		for email in Email.objects.previewing_now(now=now):
			email.preview()

		for email in Email.objects.sending_now(now=now):
			email.send()
