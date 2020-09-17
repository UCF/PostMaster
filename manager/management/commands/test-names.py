from django.core.management.base import BaseCommand, CommandError
from optparse                    import make_option
from manager.models               import Recipient, RecipientGroup

class Command(BaseCommand):

	def handle(self, *args, **kwargs):
		recipients = Recipient.objects.all()

		for recipient in recipients:
			print('\t\t\t\t'.join([recipient.preferred_first_name, recipient.preferred_name, recipient.first_name, recipient.last_name]))
