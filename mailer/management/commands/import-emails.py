from django.core.management.base import BaseCommand, CommandError
from optparse                    import make_option
from util                        import LDAPHelper 
from django.conf                 import settings
from mailer.models                 import Recipient, RecipientGroup
import re
import csv

class Command(BaseCommand):
	#option_list = BaseCommand.option_list + (
	#	make_option(
	#		'--group_name',
	#		action  ='store',
	#		dest    ='group_name',
	#		default ='',
	#	),
	#	make_option(
	#		'--column-order',
	#		action  ='store',
	#		dest    ='column_order',
	#		default ='first_name,last_name,email'
	#	),
	#	make_option(
	#		'--ignore-first-column',
	#		action  ='store_true',
	#		dest    ='ignore_first_column',
	#		default = False
	#	)
	#)
	
	
	ldap = LDAPHelper()
	LDAPHelper.bind(ldap.connection, settings.LDAP_NET_SEARCH_USER, settings.LDAP_NET_SEARCH_PASS)

	def handle(self, *args, **kwargs):
		#user = LDAPHelper.search(self.ldap.connection, 'conover')
		#print type(user[0]);
		#print LDAPHelper.extract_guid(user)
		#print LDAPHelper._extract_attribute(user, 'directReports')
		smca_users =  self.build_hierarchy('aharms')

		#csv_writer = csv.writer(open('smca.csv', 'w'))
		#csv_writer.writerow(['First Name', 'Last Name', 'Display Name', 'Email Address', 'NID'])
		#for user in smca_users:
		#	csv_writer.writerow([user['first_name'], user['last_name'], user['display_name'], user['email'], user['nid']])

		group, created = RecipientGroup.objects.get_or_create(name='SMCA')

		for user in smca_users:
			if user['email'] != '':
				try:
					recipient = Recipient.objects.get(email_address=user['email'])
				except Recipient.DoesNotExist:
					recipient = Recipient(
						first_name=user['first_name'],
						last_name=user['last_name'],
						email_address=user['email'],
						preferred_name=['display_name'])
				else:
					recipient.first_name = user['first_name']
					recipient.last_name = user['last_name']
					recipient.preferred_name = user['display_name']

				recipient.save()
				group.recipients.add(recipient)

	def build_hierarchy(self, nid):
		users = []

		user = LDAPHelper.search(self.ldap.connection, nid)

		display_name = ''
		try:
			display_name = LDAPHelper._extract_attribute(user, 'displayName', single=True)
		except LDAPHelper.MissingAttribute:
			pass

		email = ''
		try:
			email = LDAPHelper.extract_email(user)
		except LDAPHelper.MissingAttribute:
			pass

		users.append({
			'first_name'   :LDAPHelper.extract_firstname(user),
			'last_name'    :LDAPHelper.extract_lastname(user),
			'email'        :email,
			'display_name' :display_name,
			'nid'          :LDAPHelper.extract_username(user)
		})

		try:
			direct_reports_dns = LDAPHelper._extract_attribute(user, 'directReports')
		except LDAPHelper.MissingAttribute:
			# this person has not direct reports
			pass
		else:
			direct_report_nids = Command.extract_direct_report_nids(direct_reports_dns)
			for nid in direct_report_nids:
				users.extend(self.build_hierarchy(nid))

		return users

	@classmethod
	def extract_direct_report_nids(cls, direct_reports):
		nids = []
		for report in direct_reports:
			match = re.match('CN=([^,]+),', report)
			if match is not None:
				nids.append(match.groups()[0])
		return nids