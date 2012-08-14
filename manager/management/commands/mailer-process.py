from django.core.management.base import BaseCommand
from manager.models              import Email

log = logging.getLogger(__name__)


class Command(BaseCommand):
	'''
		Handles sending emails. Should be 
		set to run every 15 minutes
	'''

	def handle(self, *args, **options):
		pass
