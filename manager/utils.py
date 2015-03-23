from manager.models import Recipient
from manager.models import RecipientGroup
from manager.models import RecipientAttribute

import csv
import logging

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

	def __init__(self, csv_file, recipient_group_name, skip_first_row, column_order):
		if csv_file:
			self.csv_file = csv_file
		else:
			log.error('csv_file must not be null')
			raise Exception('csv_file must not be null')

		if recipient_group_name:
			self.recipient_group_name = recipient_group_name
		else:
			log.error('Receipient Group Name is null or empty string')
			raise Exception('Receipient Group Name is null or empty string')
			return

		if skip_first_row:
			self.skip_first_row = skip_first_row

		if column_order:
			self.column_order = column_order


	def import_emails(self):

		columns = self.column_order

		if 'email' not in columns:
			raise Exception('Email required for import')
			return

		group = None
		try:
			group = RecipientGroup.objects.get(name=self.recipient_group_name)
		except RecipientGroup.DoesNotExist:
			log.debug('Recipient group does not exist. Creating...')
			group = RecipientGroup(name=self.recipient_group_name)
			group.save()

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
					self.revert()
					log.error('There is a malformed row at line %d' % row_num)
					raise Exception('There is a malformed row at line %d' % row_num)
				else:
					if email_address == '':
						log.debug('Empty email address at line %d' % row_num)
					else:
						created = False
						try:
							recipient = Recipient.objects.get(email_address=email_address)
						except:
							recipient = Recipient(
									email_address=email_address
							)

							created	= True
						try:
							recipient.save()
						except Exception, e:
							log.error('Error saving recipient at line %d: %s' % (row_num, str(e)))
							raise Exception('Error saving recipient at line %d: %s' % (row_num, str(e)))
						else:
							log.debug('Recipient %s successfully %s' % (email_address, 'created' if created else 'updated'))

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
							except Exeception, e:
								log.debug('Error saving recipient attibute First Name at line %d, %s' % (row_num, str(e)))

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
								log.debug('Error saving recipient attribute Last Name at line %d, %s' % (row_num, str(e)))

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
								log.debug('Error saving recipient attribute Preferred Name at line %d, %s' % (row_num, str(e)))

						if group is not None:
							try:
								group.recipients.add(recipient)
							except Exception, e:
								log.error('Failed to add %s group %s at line %d: %s' % (email_address, group.name, row_num, str(e)))
								raise Exception('Failed to add %s group %s at line %d: %s' % (email_address, group.name, row_num, str(e)))
			row_num += 1

	def revert(self):
		try:
			recipient_group = RecipientAttribute.objects.get(name=self.recipient_group_name)
		except:
			return
		else:
			recipient_group.delete()
