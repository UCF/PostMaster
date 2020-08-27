from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.db.models import Count
from manager.models import Email, Instance, StaleRecord

import csv
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from StringIO import StringIO

from tqdm import tqdm

import settings

class Command(BaseCommand):
    help = 'Exports email data to a csv'

    filename = ''
    before = None
    prepare_removal = False
    exported = []

    def add_arguments(self, parser):
        parser.add_argument(
            '--filename',
            dest='filename',
            type=str,
            help='The path to export the file to',
            default=None
        )

        parser.add_argument(
            '--email',
            dest='email',
            type=str,
            help='The email to send the export to',
            default=None
        )

        parser.add_argument(
            '--before-date',
            dest='before_date',
            type=lambda s: datetime.strptime(s, '%Y-%m-%d'),
            help='Filters results to emails with instances before this date',
            default=None
        )

        parser.add_argument(
            '--prepare-removal',
            dest='prepare_removal',
            type=bool,
            help='Saves the records that are exported for future removal',
            default=False
        )

    def handle(self, *args, **options):
        """
        The main process of the command
        """
        self.filename = options['filename']
        self.email = options['email']
        self.before = options['before_date']
        self.prepare_removal = options['prepare_removal']

        if not self.filename and not self.email:
            raise CommandError('A filename or email must be provided in order to export')

        self.exported = []

        records = self.get_records()
        self.write_records(records)

        if self.prepare_removal:
            self.prepare_stale_record()

    def get_records(self):
        """
        Gets the records to be exported
        """
        retval = Email.objects.all()

        if self.before:
            retval = retval.filter(
                instances__end__lt=self.before
            )

        return retval.distinct()

    def write_records(self, records):
        """
        Prepares the record for export
        """
        record_count = records.count()

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

        file_handler = None
        email_handler = None

        if self.filename:
            file_handler = open(self.filename, 'w')
            try:
                file_writer = csv.DictWriter(file_handler, fieldnames=fieldnames)
                file_writer.writeheader()
            except:
                file_handler.close()

        if self.email:
            email_handler = StringIO()
            email_writer = csv.DictWriter(email_handler, fieldnames=fieldnames)
            email_writer.writeheader()

        total_instances = Instance.objects.filter(email__in=records).count()

        with tqdm(total=total_instances) as pbar:
            for record in records:
                instances = record.instances.all()

                if self.before:
                    instances = instances.filter(end__lt=self.before)

                email_title = record.title

                for instance in instances.all():
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

                    if file_handler and file_writer:
                        try:
                            file_writer.writerow(line)
                        except Exception as e:
                            file_writer.close()
                            raise e

                    if email_handler and email_writer:
                        email_writer.writerow(line)

                    self.exported.append(instance)

                    pbar.update(1)

        # Make sure we close the file since we're
        # handling this manually
        if file_handler:
            file_handler.close()

        if email_handler:
            self.send_email(email_handler)


    def send_email(self, io_stream=None):
        try:
            amazon = smtplib.SMTP_SSL(settings.AMAZON_SMTP['host'], settings.AMAZON_SMTP['port'])
            amazon.login(settings.AMAZON_SMTP['username'], settings.AMAZON_SMTP['password'])
        except:
            raise Exception("Unable to connect to amazon")
        else:
            text = '''
<html>
  <head></head>
  <body>
    <p>The attached export is all done!</p>
  </body>
</html>
            '''

            msg = MIMEMultipart('alternative')
            msg['subject'] = 'Data Export {0}'.format(datetime.now())
            msg['From'] = 'UCF Web Communications <webcom@ucf.edu>'
            msg['To'] = self.email
            msg.attach(
                MIMEText(
                    text,
                    'html',
                    _charset='us-ascii'
                )
            )

            attachment = MIMEText(io_stream.getvalue(), _subtype='csv')
            attachment.add_header('Content-Disposition', 'attachment', filename='instance-export-{0}.csv'.format(datetime.now()))

            # Close out our io_stream
            io_stream.close()

            msg.attach(attachment)

            try:
                amazon.sendmail('webcom@ucf.edu', self.email, msg.as_string())
            except:
                raise Exception('Unable to send email')

            amazon.quit()

    def prepare_stale_record(self):
        """
        Creates a stale record object
        """
        stale = StaleRecord()
        stale.save()

        stale.instances.add(*self.exported)