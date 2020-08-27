from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.utils.six.moves import input

from manager.models import Email, Instance, StaleRecord

class Command(BaseCommand):
    help = 'Removes stale records from the database'

    record_hash = None
    remove_emails = True

    def add_arguments(self, parser):
        parser.add_argument(
            'record_hash',
            type=str,
            help='The unique hash of the StaleRecord to remove',
            default=None
        )

        parser.add_argument(
            '--remove-empty-emails',
            dest='remove_empty_emails',
            type=bool,
            help='When true, will remove emails who have no instances after the stale instances are removed.',
            default=True
        )

        parser.add_argument(
            '--quiet',
            dest='quiet',
            type=bool,
            help='When true, does not prompt for confirmation before removing records',
            default=False
        )

    def handle(self, *args, **options):
        self.record_hash = options['record_hash']
        self.remove_emails = options['remove_empty_emails']
        self.quiet = options['quiet']

        self.clean()

    def clean(self):
        try:
            stale = StaleRecord.objects.get(removal_hash=self.record_hash)
        except StaleRecord.DoesNotExist:
            raise CommandError('A stale records object with the provided hash does not exist')

        instances = stale.instances.all()
        emails = Email.objects.filter(instances__in=instances)

        if not self.quiet:
            delete = self.confirm("Delete {0} instances? [Y/n]: ".format(instances.count()), True)

            if delete == False:
                return

        instances.delete()

        if self.remove_emails:
            emails = emails.filter(instances=0)

            if not self.quiet:
                delete = self.confirm("Delete {0} emails? [Y/n]: ".format(emails.count()), True)

                if delete == False:
                    return


            emails.delete()

    def confirm(self, message, default=None):
        result = input('%s ' % message)
        if not result and default is not None:
            return default
        while len(result) < 1 or result[0].lower() not in 'yn':
            result = input("Please answer yes or no: ")
        return result[0].lower() == 'y'
