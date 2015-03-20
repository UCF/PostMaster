from django.core.management.base import BaseCommand, CommandError
from optparse                    import make_option
from util                        import LDAPHelper 
from django.conf                 import settings
from manager.models               import Recipient, RecipientAttribute, RecipientGroup
from manager.utils               import CSVImport
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
			'--ignore-first-row',
			action  ='store_true',
			dest    ='ignore_first_row',
			default = False
		)
	)
	def handle(self, *args, **kwargs):

		if len(args) == 0 or len(args) > 1:
			print 'Usage: python manage.py import-emails [filename] [options]'
			print 'Options:'
			print '--group-name [group name]'
			print '\tWill add recipients to the specified recipient group.'
			print '\tThe group will be created if it does not exist.'
			print '\tIf not specified, recipients will not be added to any group.'
			print '--column-order [columns]'
			print '\tDefault: first_name,last_name,email,preferred_name'
			print '\tThe column order of the CSV. The first_name, last_name, and email'
			print '\tcolumn names must be present.'
			print '--ignore-first-row'
			print '\tIgnore the first row of the CSV. Useful if there are column'
			print '\theaders present.'
		else:
			filename            = args[0]
			group_name          = kwargs.get('group_name')
			columns             = list(col.strip() for col in kwargs.get('column_order').split(','))
			ignore_first_row = kwargs.get('ignore_first_row')

			importer = CSVImport(open(filename, 'rU'), group_name, ignore_first_row, columns)
			try:
				importer.import_emails()
			except Exception, e:
				print "Error importing recipients: %s" % str(e)
				