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

        parser.add_argument(
            '--subprocess',
            dest='subprocess',
            type=int,
            help='When provided, a subprocess record will be updated on each tick of the progress bar',
            default=None
        )

    def handle(self, *args, **options):
        self.record_hash = options['record_hash']
        self.remove_emails = options['remove_empty_emails']
        self.quiet = options['quiet']
        self.subprocess = options['subprocess']

        if self.subprocess:
            try:
                tracker = SubprocessStatus.objects.get(pk=self.subprocess)
                self.subprocess = tracker
            except SubprocessStatus.DoesNotExist:
                raise CommandError("The subprocess provided does not exist")


        self.clean()

    def clean(self):
        try:
            stale = StaleRecord.objects.get(removal_hash=self.record_hash)
        except StaleRecord.DoesNotExist:
            raise CommandError('A stale records object with the provided hash does not exist')

        instances = stale.instances.all()
        emails = Email.objects.filter(instances__in=instances)

        if self.subprocess:
            self.subprocess.total_units = instances.count()
            self.subprocess.status = 'In Progress'
            self.subprocess.status.save()

        if not self.quiet:
            delete = self.confirm("Delete {0} instances? [Y/n]: ".format(instances.count()), True)

            if delete == False:
                return

        for idx, instance in enumerate(instances.all()):
            instance.delete()
            self.update_status('In Progress', '', idx + 1)

        if self.remove_emails:
            emails = emails.filter(instances=0)

            if not self.quiet:
                delete = self.confirm("Delete {0} emails? [Y/n]: ".format(emails.count()), True)

                if delete == False:
                    return

        self.update_status('Complete', '')


    def update_status(self, status, error, current_unit):
        if (self.subprocess and status == "Completed") :
            self.tracker.status = "Completed"
            self.tracker.error = ""
            self.tracker.current_unit = self.tracker.total_units
            self.tracker.save()

        if (self.subprocess and
            (current_unit % self.update_factor == 0
            or current_unit == self.tracker.total_units)
            or error != ""):
            self.tracker.status = status
            self.tracker.error = error
            self.tracker.current_unit = current_unit
            self.tracker.save()

    def confirm(self, message, default=None):
        result = input('%s ' % message)
        if not result and default is not None:
            return default
        while len(result) < 1 or result[0].lower() not in 'yn':
            result = input("Please answer yes or no: ")
        return result[0].lower() == 'y'
