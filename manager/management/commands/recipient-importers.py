from django.core.management.base import BaseCommand, CommandError
from optparse                    import make_option
from manager.models              import Recipient, RecipientGroup
from django.conf                 import settings
from django.db                   import connections, transaction
import logging

log = logging.getLogger(__name__)


class Command(BaseCommand):
	'''
		Runs a specified recipient importer.
	'''

	args = '<importer>'
	help = 'Run a specific recipient importer.'

	# Recipient importers that are available.
	importers = (
		'GMUCFImporter',
	)


	def handle(self, *args, **kwargs):
		if len(args) != 1 or args[0] not in self.importers:
			print 'You must specify an importer to run. Example command:'
			print 'python manage.py recipient-importer <importer-name>'
			print 'Available importers are:'
			for importer in self.importers:
				print importer
		else:
			cls  = eval(args[0])
			inst = cls()
			inst.setup()
			inst.do_import()

class Importer(object):
	'''
		Base importer class. Any functionality that should be 
		shared between all importers should be implemented
		or stubbed here.
	'''
	id           = None
	display_name = None

	class ImporterException(Exception):
		pass

	def __init__(self, *args, **kwargs):
		pass

	def setup(self):
		pass

	def do_import(self):
		raise NotImplemented()

class GMUCFImporter(Importer):
	'''
		Importer for the Good Morning UCF email list.
	'''
	name         = 'gmucfimporter'
	display_name = 'Good Morning UCF Importer'

	gmucf_recipient_group_name = 'Good Morning UCF'

	def setup(self):

		# Check to see if the rds_wharehouse database is configured
		if 'rds_wharehouse' not in settings.DATABASES:
			raise self.ImporterException('The rds_wharehouse database is configured.')


		self.postmaster_db_name     = settings.DATABASES['default']['NAME']
		self.rds_wharehouse_db_name = settings.DATABASES['rds_wharehouse']['NAME']
		self.postmaster_cursor = connections['default'].cursor()

		# Check to see if the Good Morning UCF Group exists
		try:
			self.gmucf_recipient_group = RecipientGroup.objects.get(name=self.gmucf_recipient_group_name)
		except RecipientGroup.DoesNotExist:
			raise self.ImporterException('The Good Morning UCF recipient group doesn\'t exist. Please create it.')

		# Make sure there is an index on the smca_gmucf.email column
		self.postmaster_cursor.execute('SHOW INDEX FROM %s.smca_gmucf WHERE Key_name=\'email\'' % self.rds_wharehouse_db_name)
		results = self.postmaster_cursor.fetchall()
		if len(results) == 0:
			self.postmaster_cursor.execute('ALTER TABLE %s.smca_gmucf ADD INDEX `email` (`email`)' % self.rds_wharehouse_db_name)
			transaction.commit_unless_managed()

		# Make sure there is an index on the manager_recipient.email_address column
		self.postmaster_cursor.execute('SHOW INDEX FROM %s.manager_recipient WHERE Key_name=\'email_address\'' % self.postmaster_db_name)
		results = self.postmaster_cursor.fetchall()
		if len(results) == 0:
			self.postmaster_cursor.execute('ALTER TABLE %s.manager_recipient ADD INDEX `email_address` (`email_address`)' % self.postmaster_db_name)
			transaction.commit_unless_managed()
			
	def do_import(self):
		'''
			1. Remove any recipients from the Good Morning UCF group who are no longer
				in the RDS wharehouse data.
			2. Create any recipients who are in the the RDS wharehouse data but not
				in the recipients table.
			3. Update any Recipient attributes
			4. Add any newly created recipients to the Good Morning UCF group
		'''
		
		self.postmaster_cursor.execute('''
			DELETE FROM
				%s.manager_recipientgroup_recipients
			WHERE
				recipientgroup_id = %d  AND
				recipient_id IN (
					SELECT
						recipient.id
					FROM
						%s.manager_recipient recipient
					WHERE
						recipient.email_address NOT IN (
							SELECT LOWER(email) FROM %s.smca_gmucf
						)
				)''' % (
			self.postmaster_db_name,
			self.gmucf_recipient_group.id,
			self.postmaster_db_name,
			self.rds_wharehouse_db_name
		))
		transaction.commit_unless_managed()

		self.postmaster_cursor.execute('''
			INSERT IGNORE INTO
				%s.manager_recipient(email_address)
			(
				SELECT
					LOWER(email)
				FROM
					%s.smca_gmucf
				WHERE
					LOWER(email) NOT IN (
						SELECT email_address FROM %s.manager_recipient
					)
			)
		''' % (
			self.postmaster_db_name,
			self.rds_wharehouse_db_name,
			self.postmaster_db_name
		))
		transaction.commit_unless_managed()


		self.postmaster_cursor.execute('''
			INSERT INTO 
				%s.manager_recipientattribute(recipient_id, name, value)
			(
				SELECT 
					recipient.id AS recipient_id,
					'Preferred Name' AS name,
					gmucf.first_name AS value
				FROM
					%s.manager_recipient recipient
				JOIN
					%s.smca_gmucf AS gmucf
				ON
					recipient.email_address = LOWER(gmucf.email)
			)
			ON DUPLICATE KEY UPDATE value=value
		''' % (
			self.postmaster_db_name,
			self.postmaster_db_name,
			self.rds_wharehouse_db_name
		))
		transaction.commit_unless_managed()

		self.postmaster_cursor.execute('''
			INSERT INTO 
				%s.manager_recipientgroup_recipients(recipientgroup_id, recipient_id)
			(
				SELECT 
					%s AS recipientgroup_id,
					recipient.id
				FROM
					%s.manager_recipient recipient
				WHERE
					recipient.email_address IN (
						SELECT LOWER(email) FROM %s.smca_gmucf
					) AND
					recipient.id NOT IN (
						SELECT
							recipient_id
						FROM
							%s.manager_recipientgroup_recipients
						WHERE
							recipientgroup_id = %d
					)
			)
		''' % (
			self.postmaster_db_name,
			self.gmucf_recipient_group.id,
			self.postmaster_db_name,
			self.rds_wharehouse_db_name,
			self.postmaster_db_name,
			self.gmucf_recipient_group.id
		))
		transaction.commit_unless_managed()