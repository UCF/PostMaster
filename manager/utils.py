import boto
from boto.s3.connection import OrdinaryCallingFormat
from boto.s3.connection import S3Connection
from boto.s3.key import Key
import csv
from datetime import datetime
from django.core.urlresolvers import reverse
import logging
import math
import os
import re
import smtplib
import urllib
import urlparse

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from django.db import transaction
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.db.models import Avg
from django.db.models import Func

from manager.models import Email
from manager.models import Instance
from manager.models import Recipient
from manager.models import RecipientGroup
from manager.models import RecipientAttribute
from manager.models import SubprocessStatus
from manager.models import URL


log = logging.getLogger(__name__)

class Round(Func):
    function = 'ROUND'
    arity = 2


class CSVImport:
    '''
        Provides functionality for importing csv files of emails/attributes
        into existing or new recipient groups.
    '''
    csv_file = ''
    recipient_group_name = ''
    skip_first_row = False
    column_order = 'email,preferred_name'
    subprocess = None
    update_factor = 1

    def __init__(self, csv_file, recipient_group_name, skip_first_row, column_order, subprocess):
        if csv_file:
            self.csv_file = csv_file
        else:
            print 'csv_file is null or empty string'
            raise Exception('csv_file must not be null')

        if recipient_group_name:
            self.recipient_group_name = recipient_group_name
        else:
            raise Exception('Receipient Group Name is null or empty string')
            return

        if skip_first_row:
            self.skip_first_row = skip_first_row

        if column_order:
            self.column_order = column_order

        self.subprocess = subprocess

    def import_emails(self):

        columns = self.column_order

        if 'email' not in columns:
            print 'email is a required column for import'
            return

        new_group = False
        group = None
        try:
            group = RecipientGroup.objects.get(name=self.recipient_group_name)
        except RecipientGroup.DoesNotExist:
            print 'Recipient group does not exist. Creating...'
            group = RecipientGroup(name=self.recipient_group_name)
            new_group = True
            group.save()

        if self.subprocess:
            self.tracker = SubprocessStatus.objects.get(pk=self.subprocess)
            self.tracker.total_units = self.get_line_count()
            if new_group:
                self.tracker.success_url = reverse('manager-recipientgroup-update', kwargs={'pk': group.pk})
            self.tracker.save()

            # Update the update_factor to prevent a save every time it loops through
            # By default we wait until 1% of the file has been processed before
            # writing to the database.
            self.update_factor = math.ceil( self.tracker.total_units * .01 )

        # Make sure the file is back at the beginning
        self.csv_file.seek(0)

        csv_reader = csv.reader(self.csv_file)
        email_adress_index = columns.index('email')
        try:
            first_name_index = columns.index('first_name')
        except ValueError:
            first_name_index = None
        try:
            last_name_index = columns.index('last_name')
        except ValueError:
            last_name_index = None
        try:
            preferred_name_index = columns.index('preferred_name')
        except ValueError:
            preferred_name_index = None

        row_num = 1
        for row in csv_reader:
            if row_num == 1 and self.skip_first_row:
                row_num = 2
                continue
            else:
                try:
                    email_address = row[email_adress_index]
                    if first_name_index is None:
                        first_name = None
                    else:
                        first_name = row[first_name_index]
                    if last_name_index is None:
                        last_name = None
                    else:
                        last_name = row[last_name_index]
                    if preferred_name_index is None:
                        preferred_name = None
                    else:
                        preferred_name = row[preferred_name_index]
                except IndexError:
                    print 'Malformed row at line %d' % row_num
                    self.revert()
                    self.update_status("Error", "There is a malformed row at line %d" % row_num, row_num)
                    raise Exception('There is a malformed row at line %d' % row_num)
                else:
                    if email_address == '':
                        print 'Empty email address at line %d' % row_num
                    else:
                        created = False
                        try:
                            recipient = Recipient.objects.get(email_address=email_address)
                        except:
                            recipient = Recipient(
                                    email_address=email_address
                            )

                            created = True
                        try:
                            recipient.save()
                        except Exception, e:
                            print 'Error saving recipient at line %d: %s' % (row_num, str(e))
                        else:
                            print 'Recipient %s successfully %s' % (email_address, 'created' if created else 'updated')

                        if first_name is not None:
                            try:
                                attribute_first_name = RecipientAttribute.objects.get(recipient=recipient.pk, name='First Name')
                            except:
                                attribute_first_name = RecipientAttribute(
                                    recipient = recipient,
                                    name = 'First Name',
                                    value = first_name
                                )
                            else:
                                attribute_first_name.value = first_name

                            try:
                                attribute_first_name.save()
                            except Exception, e:
                                print 'Error saving recipient attibute First Name at line %d, %s' % (row_num, str(e))

                        if last_name is not None:
                            try:
                                attribute_last_name = RecipientAttribute.objects.get(recipient=recipient.pk, name='Last Name')
                            except:
                                attribute_last_name = RecipientAttribute(
                                    recipient = recipient,
                                    name = 'Last Name',
                                    value = last_name
                                )
                            else:
                                attribute_last_name.value = last_name

                            try:
                                attribute_last_name.save()
                            except Exception, e:
                                print 'Error saving recipient attribute Last Name at line %d, %s' % (row_num, str(e))

                        if preferred_name is not None:
                            try:
                                attribute_preferred_name = RecipientAttribute.objects.get(recipient=recipient.pk, name='Preferred Name')
                            except:
                                print 'Preferred Name attribute does not exist'
                                attribute_preferred_name = RecipientAttribute(
                                    recipient = recipient,
                                    name = 'Preferred Name',
                                    value = preferred_name
                                )
                            else:
                                attribute_preferred_name.value = preferred_name

                            try:
                                attribute_preferred_name.save()
                            except Exception, e:
                                print 'Error saving recipient attribute Preferred Name at line %d, %s' % (row_num, str(e))

                        if group is not None:
                            try:
                                group.recipients.add(recipient)
                            except Exception, e:
                                print 'Failed to add %s group %s at line %d: %s' % (email_address, group.name, row_num, str(e))
            row_num += 1
            # Increment
            self.update_status("In Progress", "", row_num)

        self.update_status("Completed", "", row_num)

        if self.subprocess:
            self.delete_file(self.csv_file.name)

    def update_status(self, status, error, current_unit):
        if (self.subprocess and
            (current_unit % self.update_factor == 0
            or current_unit == self.tracker.total_units)
            or error != ""):
            self.tracker.status = status
            self.tracker.error = error
            self.tracker.current_unit = current_unit
            self.tracker.save()

    def delete_file(self, filename):
        os.remove(filename)

    def remove_tracker(self, tracker_pk):
        self.tracker.delete()

    def revert(self):
        try:
            recipient_group = RecipientAttribute.objects.get(name=self.recipient_group_name)
        except:
            return
        else:
            recipient_group.delete()

    def get_line_count(self):
        f = self.csv_file
        lines = 1
        buf_size = 1024 * 1024
        read_f = f.read

        buf = read_f(buf_size)
        while buf:
            lines += buf.count('\n')
            buf = read_f(buf_size)

        return lines

class EmailSender:
    '''
    This helper class will send an email without creating
    an Email Instance
    '''
    email = None
    recipients = None
    html = None
    status_code = None

    def __init__(self, email, recipients):
        self.email = email
        self.recipients = recipients
        self.status_code, self.html = self.email.html

    @property
    def placeholders(self):
        delimiter = self.email.replace_delimiter
        placeholders = re.findall(re.escape(delimiter) + '(.+)' + re.escape(delimiter), self.html)
        return filter(lambda p: p.lower() != 'unsubscribe', placeholders)

    def get_attributes(self, recipient):
        attributes = {}
        atts = RecipientAttribute.objects.filter(recipient=recipient)
        for att in atts:
            attributes[att.name] = att.value

        return attributes

    def send(self):

        try:
            amazon = smtplib.SMTP_SSL(settings.AMAZON_SMTP['host'], settings.AMAZON_SMTP['port'])
            amazon.login(settings.AMAZON_SMTP['username'], settings.AMAZON_SMTP['password'])
        except:
            log.exception('Unable to connect to amazon')
        else:
            for recipient in self.recipients:
                # Get recipient attributes
                attributes = self.get_attributes(recipient)
                # Customize the email for this recipient
                customized_html = self.html
                # Replace template placeholders
                delimiter = self.email.replace_delimiter
                for placeholder in self.placeholders:
                    replacement = ''
                    if placeholder.lower() != 'unsubscribe':
                        if attributes[placeholder] is None:
                            log.error('Recipient %s is missing attribute %s' % (str(recipient), placeholder))
                        else:
                            replacement = attributes[placeholder]
                        customized_html = customized_html.replace(delimiter + placeholder + delimiter, replacement)

                msg = MIMEMultipart('alternative')
                msg['subject'] = self.email.subject
                msg['From'] = self.email.smtp_from_address
                msg['To'] = recipient.email_address
                msg.attach(MIMEText(customized_html, 'html', _charset='us-ascii'))
                try:
                    amazon.sendmail(self.email.from_email_address, recipient.email_address, msg.as_string())
                except smtplib.SMTPException, e:
                    log.exception('Unable to send email.')
            amazon.quit()


class AmazonS3Helper:
    """
    Provides basic helper functions for adding, removing and listing files in
    an S3 bucket.

    Uses the bucket and other S3 settings defined in settings_local.py.
    """
    connection = None
    bucket = None
    base_key_path = settings.AMAZON_S3['base_key_path']
    valid_extension_groups = settings.AMAZON_S3['valid_extension_groups']
    valid_protocols = ['//', 'http://', 'https://']

    class AmazonS3HelperException(Exception):
        def __init__(self, value='No additional information'):
            self.parameter = value
            logging.error(': '.join([str(self.__doc__), str(value)]))

        def __str__(self):
            return repr(self.parameter)

    class S3ConnectionError(AmazonS3HelperException):
        """self.connect failed"""
        pass

    class InvalidKeyError(AmazonS3HelperException):
        """A key could not be validated against the S3 bucket"""
        pass

    class KeyDeleteError(AmazonS3HelperException):
        """A key could not be deleted"""
        pass

    class KeyFetchError(AmazonS3HelperException):
        """bucket.get_key failed"""
        pass

    class KeyCreateError(AmazonS3HelperException):
        """A key couldn't be created"""
        pass

    class KeylistFetchError(AmazonS3HelperException):
        """bucket.list failed"""
        pass

    def __init__(self):
        self.connect()

    def connect(self):
        try:
            self.connection = S3Connection(
                settings.AMAZON_S3['aws_access_key_id'],
                settings.AMAZON_S3['aws_secret_access_key'],
                calling_format=OrdinaryCallingFormat()
            )
            self.bucket = self.connection.get_bucket(
                settings.AMAZON_S3['bucket']
            )
        except Exception, e:
            raise AmazonS3Helper.S3ConnectionError(e)

    def get_extensions_by_groupname(self, groupname):
        """
        Returns a list of file extension strings in
        self.valid_extension_groups, or None if the groupname does not exist
        """
        try:
            extensions = self.valid_extension_groups[groupname]
        except KeyError:
            extensions = None

        return extensions

    def get_base_key_path_url(self):
        try:
            keyobj = self.bucket.get_key(self.base_key_path, validate=True)
        except Exception, e:
            raise AmazonS3Helper.InvalidKeyError(e)

        url = keyobj.generate_url(
            0,
            query_auth=False,
            force_http=True
        )

        return url

    def get_file_list(self, file_prefix='', return_extension_groupname=None):
        """
        Returns a list of key objects in self.bucket (optionally prefixed by
        file_prefix arg).

        return_extension_group specifies an extension group of filetypes to
        filter by; e.g. 'images' group returns .png, .jpg, .gif file urls (see
        settings_local.py).  Returns all filetypes by default.
        """
        file_list_unfiltered = None
        file_list = []
        valid_extensions = None

        if not file_prefix:
            file_prefix = ''

        if return_extension_groupname:
            valid_extensions = self.get_extensions_by_groupname(
                return_extension_groupname
            )

        try:
            file_list_unfiltered = self.bucket.list(
                prefix=self.base_key_path + file_prefix
            )
        except Exception, e:
            raise AmazonS3Helper.KeylistFetchError(e)

        if file_list_unfiltered:
            for keyobj in file_list_unfiltered:
                filename, file_extension = os.path.splitext(keyobj.name)

                # Determine if the file extension is valid
                is_valid = False
                if file_extension != '':
                    if not valid_extensions:
                        is_valid = True
                    elif valid_extensions and file_extension in valid_extensions:
                        is_valid = True

                if is_valid:
                    file_list.append(keyobj)

        return file_list

    def upload_file(self, file, unique, file_prefix='', extension_groupname=None):
        """
        Uploads a file to S3 and returns its key (optionally prefixed by
        file_prefix arg).

        Setting unique=True appends a timestamp to the filename to prevent
        overwriting existing files.
        """
        keyobj = None

        if file_prefix is None:
            file_prefix = ''

        if file:
            filename, file_extension = os.path.splitext(file.name)

            if extension_groupname:
                valid_extensions = self.get_extensions_by_groupname(
                    extension_groupname
                )
            if (
                extension_groupname is not None and
                file_extension not in valid_extensions
            ):
                # The user doesn't have permission to upload this type of file
                raise PermissionDenied

            # Create a unique filename (so we don't accidentally overwrite an
            # existing file) if unique==True
            if unique is True:
                filename_unique = filename \
                    + '_'  \
                    + str(datetime.now().strftime('%Y%m%d%H%M%S')) \
                    + file_extension
                filename = filename_unique
            else:
                filename = file.name

            try:
                # Create a new key for the new object and upload it
                keyname = self.base_key_path + file_prefix + filename
                keyobj = Key(self.bucket)
                keyobj.key = keyname
                keyobj.set_contents_from_file(fp=file, policy='public-read')
            except Exception, e:
                raise AmazonS3Helper.KeyCreateError(e)

        return keyobj

    def delete_file(self, keyname):
        """
        Deletes a file by its key name.  Returns remaining key data.
        """
        # Find the existing key in the bucket
        try:
            keyobj = self.bucket.get_key(keyname, validate=True)
        except Exception, e:
            raise AmazonS3Helper.KeyFetchError(e)

        if keyobj is None:
            raise AmazonS3Helper.InvalidKeyError(
                'AmazonS3Helper could not be delete file: file does not exist.'
                ' Keyname: %s',
                keyname
            )
        else:
            try:
                keyobj = self.bucket.delete_key(keyobj)
            except Exception, e:
                raise AmazonS3Helper.KeyDeleteError(e)
        return keyobj

@transaction.non_atomic_requests
def flush_transaction():
    """
    Flush the current transaction so we don't read stale data

    Use in long running processes to make sure fresh data is read from
    the database.  This is a problem with MySQL and the default
    transaction mode.  You can fix it by setting
    "transaction-isolation = READ-COMMITTED" in my.cnf or by calling
    this function at the appropriate moment
    """
    transaction.commit()


def get_report(name, **kwargs):
    """
    Returns report data

    :param name: The name of the report to run
    :param **kwargs: The reports keyword arguments
    :returns: A tuple of aggregated stat data and a QuerySet of data
    """
    if name == 'url_report':
        return url_report(**kwargs)

    return (None, None)

def url_report(**kwargs):
    """
    Returns aggregated instance data and a QuerySet of URLs

    :param **kwargs: A Dictionary of arguments for the report
    """
    urls = URL.objects.all()
    instances = Instance.objects.all()

    email_select = kwargs['email_select'] if 'email_select' in kwargs else None
    start_date = kwargs['start_date'] if 'start_date' in kwargs else None
    end_date = kwargs['end_date'] if 'end_date' in kwargs else None
    day_of_week = kwargs['day_of_week'] if 'day_of_week' in kwargs else None
    url_filter = kwargs['url_filter'] if 'url_filter' in kwargs else None
    email_domain = kwargs['email_domain'] if 'email_domain' in kwargs else None

    # Short curcuit the whole thing if required fields aren't set
    if email_select is None:
        return (None, None)

    # Get instance stats
    instances_stats = {}
    if email_select is not None:
        instances = instances.filter(email__id__in=email_select)

    if start_date and end_date is not None:
        instances = instances.filter(requested_start__range=[start_date, end_date])

    if day_of_week is not None:
        instances = instances.filter(requested_start__week_day=day_of_week)

    avg_recipients = instances.annotate(num_recipients=Count('recipients')).aggregate(avg_recipients=Round(Avg('num_recipients'), 0))
    avg_recipients = avg_recipients['avg_recipients']

    avg_opens = instances.annotate(num_opens=Count('opens')).aggregate(avg_opens=Round(Avg('num_opens'), 0))
    avg_opens = avg_opens['avg_opens']

    avg_open_rate = (avg_opens / avg_recipients) * 100

    instances_stats.update({
        'avg_recipients': avg_recipients,
        'avg_opens': avg_opens,
        'avg_open_rate': avg_open_rate
    })

    # Get URL Stats
    if email_select is not None:
        urls = urls.filter(instance__email__id__in=email_select)

    if start_date and end_date is not None:
        urls = urls.filter(instance__requested_start__range=[start_date, end_date])

    if day_of_week is not None:
        urls = urls.filter(instance__requested_start__week_day=day_of_week)

    if url_filter is not None:
        urls = urls.filter(name__contains=url_filter)

    if email_domain is not None:
        urls = urls.filter(clicks__recipient__email_address__contains=email_domain)

    # Add click count
    urls = urls.annotate(total_clicks=Count('clicks'))

    return (instances_stats, urls)
