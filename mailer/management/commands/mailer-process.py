from django.core.management.base import BaseCommand
from mailer.models               import Email, Instance, RecipientGroup
from datetime                    import datetime, timedelta
from django.conf                 import settings
import calendar
import hashlib
import smtplib
import logging

log = logging.getLogger(__name__)

class Command(BaseCommand):
	'''
		Handles sending emails. Should be 
		set to run every 15 minutes
	'''
	def handle(self, *args, **options):
		amazon_ses = smtplib.SMTP_SSL(settings.AMAZON_SMTP['host'], settings.AMAZON_SMTP['port'])
		amazon_ses.login(settings.AMAZON_SMTP['username'], settings.AMAZON_SMTP['password'])
		
		now_dt          = datetime.now()
		now_d           = now_dt.date()
		now_t           = now_dt.time()
		fifteen_minutes = timedelta(seconds=60*15)
		later_dt        = now_dt + fifteen_minutes
		later_t         = later_dt.time()

		# Figure out which emails need to be sent today
		todays_email_ids = []
		for email in Email.objects.all():
			start = email.start_date
			if email.recurrence == Email.Recurs.never and start == now_d:
				todays_email_ids.append(email.id)
			elif email.recurrence == Email.Recurs.daily:
				todays_email_ids.append(email_id)
			elif email.recurrence == Email.Recurs.weekly and ((now_d - start).days % 7) == 0:
				todays_email_ids.append(email_id)
			elif email.recurrence == Email.Recurs.monthly and now_d.day == start.day:
				todays_email_ids.append(email_id)
			elif email.recurrence == Email.Recurs.yearly and ((now_d - start).days % 365) == 0:
				today_emails_ids.append(email_id)
		
		# Fetch all the emails that are due to be sent in the next 15 minutes
		email_kwargs = {
			'id__in'          :todays_email_ids,
			'start_date__gte' :now_d,
			'send_time__gte'  :now_t,
			'send_time__lt'   :later_t}
		emails = Email.objects.filter(**email_kwargs)

		for email in emails:
			content      = email.content
			subject      = email.title
			# Which groups have already been sent to.
			# Used to avoid sending an email to the same person
			# more than once
			sent_groups  = [] 

			instance = Instance(email=email, sent_html=content, in_progress=True)
			instance.save()

			for group in email.recipient_groups.all():
				for recipient in group.recipients.all():
					# This user isn't in any previous groups
					if Recipient.objects.filter(groups__in=sent_groups, id=recipient.id).count() == 0:
						from_address = 'webcom@ucf.edu'
						to_address  = recipient.email_address
						msg = 'From: $s\r\nTo: %s\r\nSubject: %s\r\n\r\n%s' % ('webcom@ucf.edu', recipient.email_address, subject, content)
						#print amazon_ses.send_mail(from_address, to_address, msg)
				send_groups.append(group)
			instance.in_progress = False
			instance.end = datetime.now()
			instance.save()
		amazon_ses.quit()
