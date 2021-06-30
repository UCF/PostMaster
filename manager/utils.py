import enum
import boto
from boto.s3.connection import OrdinaryCallingFormat
from boto.s3.connection import S3Connection
from boto.s3.key import Key
import csv
from datetime import datetime
from django.urls import reverse
import logging
import math
import os
import re
import smtplib
import urllib.request, urllib.parse, urllib.error
from urllib.parse import urlparse

from io import StringIO

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from django.db import transaction
from django.conf import settings
from django.core.exceptions import PermissionDenied

from manager.models import Email
from manager.models import Instance
from manager.models import Recipient
from manager.models import RecipientGroup
from manager.models import RecipientAttribute
from manager.models import SubprocessStatus


log = logging.getLogger(__name__)


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
    remove_stale = False

    def __init__(self, csv_file, recipient_group_name, skip_first_row, column_order, subprocess, remove_stale=False, stderr=None):
        if csv_file:
            self.csv_file = csv_file
        else:
            raise Exception('csv_file must not be null')

        if recipient_group_name:
            self.recipient_group_name = recipient_group_name
        else:
            raise Exception('Recipient Group Name is null or empty string')

        if skip_first_row:
            self.skip_first_row = skip_first_row

        if column_order:
            self.column_order = column_order

        self.remove_stale = remove_stale

        self.subprocess = subprocess
        self.stderr = stderr

    def import_emails(self):

        columns = self.column_order

        if 'email' not in columns:
            print('email is a required column for import')
            raise Exception('email is a required column for import')

        new_group = False
        group = None
        try:
            group = RecipientGroup.objects.get(name=self.recipient_group_name)
        except RecipientGroup.DoesNotExist:
            print('Recipient group does not exist. Creating...')
            group = RecipientGroup(name=self.recipient_group_name)
            new_group = True
            group.save()

        if self.remove_stale:
            group.recipients.clear()

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

        csv_string = self.csv_file.read()

        # Strips out all characters that would not be allowed in
        # an email address. This means these characters will also
        # be stripped from names or any other field within the CSV.
        csv_string = re.sub(r'[^\w\-_\s\",@\.\!#\$%&\'*+\-\/\=\?\^\`\{\|\}\~]*', '', csv_string)

        csv_stream = StringIO(csv_string)

        csv_reader = csv.reader(csv_stream)

        email_address_index = columns.index('email')
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

        for idx, row in enumerate(csv_reader):
            row_num = idx + 1

            if idx == 0 and self.skip_first_row == True:
                continue
            else:
                try:
                    email_address = row[email_address_index]
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
                    self.revert()
                    self.update_status("Error", f'There is a malformed row at line {row_num}')
                    raise Exception(f'There is a malformed row at line {row_num}')
                else:
                    if email_address == '':
                        print(('Empty email address at line %d' % row_num))
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
                        except Exception as e:
                            if self.stderr:
                                self.stderr.write(f'Error saving recipient at line {idx + 1}: {str(e)}')
                            else:
                                print(f'Error saving recipient at line {idx + 1}: {str(e)}')
                        else:
                            print(('Recipient %s successfully %s' % (email_address, 'created' if created else 'updated')))

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
                            except Exception as e:
                                if self.stderr:
                                    self.stderr.write(f'Error saving recipient attribute First Name at line {idx + 1}: {str(e)}')
                                else:
                                    print(f'Error saving recipient attribute First Name at line {idx + 1}: {str(e)}')

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
                            except Exception as e:
                                if self.stderr:
                                    self.stderr.write(f'Error saving recipient attribute Last Name at line {idx + 1}: {str(e)}')
                                else:
                                    print(f'Error saving recipient attribute Last Name at line {idx + 1}: {str(e)}')

                        if preferred_name is not None:
                            try:
                                attribute_preferred_name = RecipientAttribute.objects.get(recipient=recipient.pk, name='Preferred Name')
                            except:
                                print('Preferred Name attribute does not exist')
                                attribute_preferred_name = RecipientAttribute(
                                    recipient = recipient,
                                    name = 'Preferred Name',
                                    value = preferred_name
                                )
                            else:
                                attribute_preferred_name.value = preferred_name

                            try:
                                attribute_preferred_name.save()
                            except Exception as e:
                                if self.stderr:
                                    self.stderr.write(f'Error saving recipient attribute Preferred Name at line {idx + 1}: {str(e)}')
                                else:
                                    print(f'Error saving recipient attribute Preferred Name at line {idx + 1}: {str(e)}')

                        if group is not None:
                            try:
                                group.recipients.add(recipient)
                            except Exception as e:
                                if self.stderr:
                                    self.stderr.write(f'Failed to add {email_address} to group {group.name} at line {idx + 1}: {str(e)}')
                                else:
                                    print(f'Failed to add {email_address} to group {group.name} at line {idx + 1}: {str(e)}')
            # Increment
            self.update_status("In Progress", "", row_num)

        self.update_status("Completed", "", self.tracker.total_units)

        if self.subprocess:
            self.delete_file(self.csv_file.name)

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
        return sum(1 for line in self.csv_file)

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
        return [p for p in placeholders if p.lower() != 'unsubscribe']

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
                except smtplib.SMTPException as e:
                    log.exception('Unable to send email.')
            amazon.quit()

class SimpleEmailSender:
    '''
    Utility class for sending simple text
    emails.
    '''

    def __init__(self, subject, from_email, from_friendly, text, recipients):
        self.subject = subject
        self.from_email = from_email
        self.from_friendly = from_friendly
        self.text = text
        self.recipients = recipients

    def send(self):
        try:
            amazon = smtplib.SMTP_SSL(settings.AMAZON_SMTP['host'], settings.AMAZON_SMTP['port'])
            amazon.login(settings.AMAZON_SMTP['username'], settings.AMAZON_SMTP['password'])
        except:
            print('Unable to connect to amazon')
            log.exception('Unable to connect to amazon')
        else:
            for recipient in self.recipients:
                msg = MIMEText(self.text)
                msg['subject'] = self.subject
                msg['From'] = f"{self.from_friendly} <{self.from_email}>"
                msg['To'] = recipient

                try:
                    amazon.sendmail(self.from_email, recipient, msg.as_string())
                except smtplib.SMTPException as e:
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
        except Exception as e:
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
        except Exception as e:
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
        except Exception as e:
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
            except Exception as e:
                raise AmazonS3Helper.KeyCreateError(e)

        return keyobj

    def delete_file(self, keyname):
        """
        Deletes a file by its key name.  Returns remaining key data.
        """
        # Find the existing key in the bucket
        try:
            keyobj = self.bucket.get_key(keyname, validate=True)
        except Exception as e:
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
            except Exception as e:
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
