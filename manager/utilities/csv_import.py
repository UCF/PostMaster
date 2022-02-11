import csv
from django.urls import reverse
import logging
import math
import os
import re
from io import StringIO

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
    def __init__(self, csv_file, recipient_group_name, skip_first_row, column_order, subprocess, remove_stale=False, stderr=None):
        if csv_file:
            self.csv_file = csv_file
        else:
            raise Exception('csv_file must not be null')

        if recipient_group_name:
            self.recipient_group_name = recipient_group_name
        else:
            raise Exception('Recipient Group Name is null or empty string')

        self.skip_first_row = skip_first_row if skip_first_row else False
        self.column_order = column_order if column_order else 'email,preferred_name'
        self.update_factor = 1
        self.remove_stale = remove_stale
        self.new_group = False

        self.subprocess = subprocess
        self.stderr = stderr

    def import_emails(self):

        columns = self.column_order

        if 'email' not in columns:
            print('email is a required column for import')
            raise Exception('email is a required column for import')

        group = None
        try:
            group = RecipientGroup.objects.get(name=self.recipient_group_name)
        except RecipientGroup.DoesNotExist:
            log.info('Recipient group does not exist. Creating...')
            self.new_group = True
            group = RecipientGroup(name=self.recipient_group_name)
            group.save()

        if self.remove_stale:
            group.recipients.clear()

        if self.subprocess:
            self.tracker = SubprocessStatus.objects.get(pk=self.subprocess)
            self.tracker.total_units = self.get_line_count()
            self.tracker.success_url = reverse('manager-recipientgroup-update', kwargs={'pk': group.pk})
            self.tracker.save()

            # Update the update_factor to prevent a save every time it loops through
            # By default we wait until 1% of the file has been processed before
            # writing to the database.
            if self.tracker.total_units < 25000:
                self.update_factor = math.ceil(self.tracker.total_units * .01)
            elif self.tracker.total_units < 100000:
                self.update_factor = math.ceil(self.tracker.total_units * .005)
            else:
                self.update_factor = math.ceil(self.tracker.total_units * .001)

        # Make sure the file is back at the beginning
        self.csv_file.seek(0)

        csv_string = self.csv_file.read()

        # Strips out all characters that would not be allowed in
        # an email address. This means these characters will also
        # be stripped from names or any other field within the CSV.
        csv_string = re.sub(r'[^\w\-_\s\",@\.\!#\$%&\'*+\-\/\=\?\^\`\{\|\}\~]*', '', csv_string)

        csv_stream = StringIO(csv_string)

        csv_reader = csv.DictReader(csv_stream, fieldnames=columns)

        # For duplication tracking
        processed_emails = []

        recipient_creates = []
        recipient_updates = []

        attribute_creates = []
        attribute_updates = []

        for idx, row in enumerate(csv_reader):
            if self.skip_first_row and idx == 0: continue

            row_num = idx + 1

            try:
                email_address = row['email'].lower().strip()
                first_name = row['first_name'].strip() if 'first_name' in csv_reader.fieldnames else None
                last_name = row['last_name'].strip() if 'last_name' in csv_reader.fieldnames else None
                preferred_name = row['preferred_name'].strip() if 'preferred_name' in csv_reader.fieldnames else None
            except (IndexError, AttributeError):
                self.update_status("Error", f'There is a malformed row at line {row_num} of the provided CSV. Please review your CSV file and try again.', row_num)
                raise Exception(f'There is a malformed row at line {row_num}')
            else:
                if email_address == '':
                    log.error(f'Skipping row with empty email address at line {row_num}')
                    continue
                else:
                    try:
                        recipient = Recipient.objects.get(email_address=email_address)
                        recipient_updates.append(recipient)
                        processed_emails.append(email_address)
                    except:
                        recipient = Recipient(
                            email_address=email_address
                        )

                        # Protect against dupe insert
                        if email_address not in processed_emails:
                            try:
                                recipient.save()
                            except Exception as e:
                                self.update_status("Error", f'Error saving recipient at line {row_num} of the provided CSV. Please review your CSV file and try again.', row_num)
                                raise Exception(f'Error saving recipient at line {row_num}: {str(e)}')

                            recipient_creates.append(recipient)
                            processed_emails.append(email_address)
                        else:
                            log.error(f'Skipping row with duplicate email address {email_address} at line {row_num}')
                            continue


                    if first_name is not None:
                        try:
                            attribute_first_name = RecipientAttribute.objects.get(recipient=recipient.pk, name='First Name')
                            if attribute_first_name.value != first_name:
                                attribute_first_name.value = first_name
                                attribute_updates.append(attribute_first_name)
                        except:
                            attribute_first_name = RecipientAttribute(
                                recipient = recipient,
                                name = 'First Name',
                                value = first_name
                            )
                            attribute_creates.append(attribute_first_name)


                    if last_name is not None:
                        try:
                            attribute_last_name = RecipientAttribute.objects.get(recipient=recipient.pk, name='Last Name')
                            if attribute_last_name.value != last_name:
                                attribute_last_name.value = last_name
                                attribute_updates.append(attribute_last_name)
                        except:
                            attribute_last_name = RecipientAttribute(
                                recipient = recipient,
                                name = 'Last Name',
                                value = last_name
                            )
                            attribute_creates.append(attribute_last_name)


                    if preferred_name is not None:
                        try:
                            attribute_preferred_name = RecipientAttribute.objects.get(recipient=recipient.pk, name='Preferred Name')
                            if attribute_preferred_name.value != preferred_name:
                                attribute_preferred_name.value = preferred_name
                                attribute_updates.append(attribute_preferred_name)
                        except:
                            log.debug('Preferred Name attribute does not exist')
                            attribute_preferred_name = RecipientAttribute(
                                recipient = recipient,
                                name = 'Preferred Name',
                                value = preferred_name
                            )
                            attribute_creates.append(attribute_preferred_name)

            # Increment
            self.update_status("In Progress", "", row_num)


        RecipientAttribute.objects.bulk_create(attribute_creates, batch_size=100)
        RecipientAttribute.objects.bulk_update(attribute_updates, ['value'], batch_size=100)

        try:
            all_objs = recipient_creates + recipient_updates
            group.recipients.add(*all_objs)
            self.update_status("Completed", "", self.tracker.total_units)
        except Exception as e:
            self.update_status("Error", f'Error adding recipients to recipient group. Please try again.', self.tracker.total_units)
            raise Exception(f'Error adding recipients to recipient group: {str(e)}')

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

            if status == "Error":
                self.tracker.success_url = reverse('manager-recipients-csv-import')

            self.tracker.save()

    def delete_file(self, filename):
        os.remove(filename)

    def remove_tracker(self, tracker_pk):
        self.tracker.delete()

    def get_line_count(self):
        return sum(1 for line in self.csv_file)
