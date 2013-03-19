from django.core.management.base import BaseCommand, CommandError
from optparse                    import make_option
from util                        import LDAPHelper 
from django.conf                 import settings
from manager.models               import Recipient, RecipientAttribute, RecipientGroup
import csv

class Command(BaseCommand):
	option_list = BaseCommand.option_list + (
		make_option(
			'--group-name',
			action  ='store',
			dest    ='group_name',
			default ='',
		),
		make_option(
			'--column-order',
			action  ='store',
			dest    ='column_order',
			default ='first_name,last_name,email,preferred_name'
		),
		make_option(
			'--ignore-first-column',
			action  ='store_true',
			dest    ='ignore_first_column',
			default = False
		)
	)
	def handle(self, *args, **kwargs):

		if len(args) == 0 or len(args) > 1:
			print 'Usage: python manage.py import-emails [filename] [options]'
			print 'Options:'
			print '--group_name [group name]'
			print '\tWill add recipients to the specified recipient group.'
			print '\tThe group will be created if it does not exist.'
			print '\tIf not specified, recipients will not be added to any group.'
			print '--column-order [columns]'
			print '\tDefault: first_name,last_name,preferred_name'
			print '\tThe column order of the CSV. The first_name, last_name, and email'
			print '\tcolumn names must be present.'
			print '--ignore-first-column'
			print '\tIgnore the first column of the CSV. Useful if there are column'
			print '\theaders present.'
		else:
			filename            = args[0]
			group_name          = kwargs.get('group_name')
			columns             = list(col.strip() for col in kwargs.get('column_order').split(','))
			ignore_first_column = kwargs.get('ignore_first_column')

			if 'email' not in columns:
				print 'At least `email` must be specified in the column-order argument.'
			else:

				group = None
				if group_name != '':
					try:
						group = RecipientGroup.objects.get(name=group_name)
					except RecipientGroup.DoesNotExist:
						print 'Recipient group does not exist. Creating...'
						group = RecipientGroup(name=group_name)
						group.save()

				csv_reader = csv.reader(open(filename, 'rU'))

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
					if row_num == 1 and ignore_first_column:
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
						else:
							if email_address == '':
								print 'Empty email address at line %d' % row_num
							else:
								# Email is our primary key here
								created = False
								try:
									recipient = Recipient.objects.get(email_address=email_address)
								except Recipient.DoesNotExist:
									recipient = Recipient(
										email_address  = email_address
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
									except RecipientAttribute.DoesNotExist:
										attribute_first_name = RecipientAttribute(
											recipient = recipient,
											name      = 'First Name',
											value     = first_name
											)
									else:
										attribute_first_name.value = first_name

									try:
										attribute_first_name.save()
									except Exception, e:
										print 'Error saving recipient attribute First Name at line %d: %s' % (row_num, str(e))

								if last_name is not None:
									try:
										attribute_last_name = RecipientAttribute.objects.get(recipient=recipient.pk, name='Last Name')
									except RecipientAttribute.DoesNotExist:
										attribute_last_name = RecipientAttribute(
											recipient = recipient,
											name      = 'Last Name',
											value     = last_name
											)
									else:
										attribute_last_name.value = last_name

									try:
										attribute_last_name.save()
									except Exception, e:
										print 'Error saving recipient attribute Last Name at line %d: %s' % (row_num, str(e))

								if preferred_name is not None:
									try:
										attribute_preferred_name = RecipientAttribute.objects.get(recipient=recipient.pk, name='Preferred Name')
									except RecipientAttribute.DoesNotExist:
										attribute_preferred_name = RecipientAttribute(
											recipient = recipient,
											name      = 'Preferred Name',
											value     = preferred_name
											)
									else:
										attribute_preferred_name.value = preferred_name

									try:
										attribute_preferred_name.save()
									except Exception, e:
										print 'Error saving recipient attribute Preferred Name at line %d: %s' % (row_num, str(e))

								if group is not None:
									try:
										group.recipients.add(recipient)
									except Exception, e:
										print 'Failed to add %s to group %s at line %d: %s' % (email_address, group.name, row_num, str(e))
									else:
										print 'Recipient %s successfully added to group %s' % (email_address, group.name)
					row_num += 1