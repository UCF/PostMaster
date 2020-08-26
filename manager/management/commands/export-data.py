from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command

from manager.models import Email, Instance

import csv
from datetime import datetime

from tqdm import tqdm

class Command(BaseCommand):
    help = 'Exports email data to a csv'

    def add_arguments(self, parser):
        parser.add_argument(
            'output',
            type=str,
            help='The path to export the file to'
        )

        parser.add_argument(
            '--before-date',
            dest='before_date',
            type=lambda s: datetime.strptime(s, '%Y-%m-%d'),
            help='Filters results to emails with instances before this date',
            default=None
        )

    def handle(self, *args, **options):
        filename = options['output']
        before = options['before_date']

        records = self.get_records(before)
        self.write_records(records, filename, before)

    def get_records(self, before=None):
        retval = Email.objects.all()

        if before:
            retval = retval.filter(
                instances__end__lt=before
            )

        return retval.distinct()

    def write_records(self, records, filename, before=None):
        record_count = records.count()

        with open(filename, 'w') as file:
            fieldnames = [
                'Email ID',
                'Instance ID',
                'Title',
                'Subject',
                'URL',
                'From',
                'Friendly',
                'Start',
                'End',
                'Recipients',
                'Sent',
                'Opens',
                'Open Rate',
                'Clicks',
                'Recipients who clicked',
                'Click Rate'
            ]

            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()

            limit = 20
            offset = 0
            count = 0

            for record in tqdm(records):
                count += 1
                instances = record.instances.all()

                if before:
                    instances = instances.filter(end__lt=before)

                instance_count = instances.count()

                email_title = record.title

                for x in xrange(instances.count() / limit):
                    offset = x * limit
                    for instance in instances.all()[offset:offset + limit]:
                        line = {
                            'Email ID': record.id,
                            'Instance ID': instance.id,
                            'Title': email_title,
                            'Subject': instance.subject,
                            'URL': record.source_html_uri,
                            'From': record.from_email_address,
                            'Friendly': record.from_friendly_name,
                            'Start': instance.start,
                            'End': instance.end,
                            'Recipients': instance.recipients.count(),
                            'Sent': instance.sent_count,
                            'Opens': instance.initial_opens,
                            'Open Rate': instance.open_rate,
                            'Clicks': instance.click_count,
                            'Recipients who clicked': instance.click_recipient_count,
                            'Click Rate': instance.click_rate
                        }

                        writer.writerow(line)

