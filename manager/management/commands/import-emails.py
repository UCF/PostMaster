from django.core.management.base import BaseCommand, CommandError
from util                        import LDAPHelper
from django.conf                 import settings
from manager.models               import Recipient, RecipientAttribute, RecipientGroup
from manager.utils               import CSVImport

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument(
            'csv',
            type=str,
            help='The csv file to import.'
        )

        parser.add_argument(
            '--group-name',
            dest='group_name',
            type=str,
            help='The name of the new or existing group to import the emails to.',
            default=''
        )

        parser.add_argument(
            '--column-order',
            dest='columns',
            type=str,
            help='The order of the columns in the csv.',
            default='first_name,last_name,email,preferred_name'
        )

        parser.add_argument(
            '--ignore-first-row',
            dest='ignore_first_row',
            action='store_true',
            help='If True, the first row will be skipped.'
        )

        parser.add_argument(
            '--remove-file',
            dest='remove_file',
            action='store_true',
            help='If True, the file will be removed after the emails are imported.'
        )

        parser.add_argument(
            '--subprocess',
            dest='subprocess',
            type=int,
            help='The primary key of the Subprocess to track. Do not use when calling this from a terminal.',
            default=None
        )

        parser.add_argument(
            '--remove-stale',
            dest='remove_stale',
            action='store_true',
            help='If True, will remove recipients not found in the file from an existing recipient group.'
        )

    def handle(self, *args, **options):
        filename = options['csv']
        group_name = options['group_name']
        columns = list(col.strip() for col in options['columns'].split(','))
        ignore_first_row = options['ignore_first_row']
        subprocess = options['subprocess']
        remove_file = options['remove_file']
        remove_stale = options['remove_stale']

        importer = CSVImport(open(filename, 'rU'), group_name, ignore_first_row, columns, subprocess, remove_stale, self.stderr)
        try:
            importer.import_emails()
        except Exception as e:
            print("Error importing recipients: %s" % str(e))
