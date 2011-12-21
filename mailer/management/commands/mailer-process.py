from django.core.management.base import BaseCommand
from mailer.models               import Email, Instance, RecipientGroup, Recipient, InstanceRecipientDetails, URL
from datetime                    import datetime, timedelta
from django.conf                 import settings
from util                        import calc_url_mac, calc_open_mac
from django.core.urlresolvers    import reverse
import calendar
import hashlib
import smtplib
import logging
import re
import urllib
import time
 
log = logging.getLogger(__name__)

class Command(BaseCommand):
	'''
		Handles sending emails. Should be 
		set to run every 15 minutes
	'''
	def handle(self, *args, **options):
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
				todays_email_ids.append(email.id)
			elif email.recurrence == Email.Recurs.weekly and ((now_d - start).days % 7) == 0:
				todays_email_ids.append(email.id)
			elif email.recurrence == Email.Recurs.monthly and now_d.day == start.day:
				todays_email_ids.append(email.id)
			elif email.recurrence == Email.Recurs.yearly and ((now_d - start).days % 365) == 0:
				today_emails_ids.append(email.id)

		log.debug('Emails occurring sometime today: ' + str(todays_email_ids))
		
		# Fetch all the emails that are due to be sent in the next 15 minutes
		email_kwargs = {
			'id__in'          :todays_email_ids,
			'send_time__gte'  :now_t,
			'send_time__lt'   :later_t}
		emails = Email.objects.filter(**email_kwargs)

		log.debug('Emails being sent in this run: ' + str(list(e.id for e in emails)))

		if len(emails) > 0:
			amazon_ses = smtplib.SMTP_SSL(settings.AMAZON_SMTP['host'], settings.AMAZON_SMTP['port'])
			amazon_ses.login(settings.AMAZON_SMTP['username'], settings.AMAZON_SMTP['password'])

			for email in emails:
				content      = email.content.decode('ascii', errors='ignore')
				subject      = email.title

				# These headers will be the same for every sent email
				smtp_headers = {
					'From: '         : email.smtp_from_address,
					'Subject: '      : subject,
					'Content-type: ' : 'text/html; charset=us-ascii',
				}

				instance = Instance(email=email, sent_html=content, in_progress=True)
				instance.save()

				for group in email.recipient_groups.all():
					for recipient in group.recipients.all():

						try:
							# Check to see if this email has already been
							# sent to this recipient
							InstanceRecipientDetails.objects.get(instance=instance, recipient=recipient)
						except InstanceRecipientDetails.DoesNotExist:

							# Customize the content for this recipient
							customized_content = content
							for mapping in email.mappings.all():
								if mapping.recipient_field is not None and mapping.recipient_field != '':
									find    = email.replace_delimiter + mapping.email_label + email.replace_delimiter
									try:
										replace = getattr(recipient, mapping.recipient_field) 
									except AttributeError:
										log.error('Invalid email label mapping from `%s` to `%s` on the recipient object' % (find, mapping.recipient_field))
									else:
										customized_content = customized_content.replace(find, replace)
							
							# Tracking URLs
							if email.track_urls:
								hrefs = re.findall('<a[^href]*href="([^"]+)"', customized_content)

								positioned_urls = []
								for href in hrefs:
									# Records these URLs so they can be tracked
									url = URL(instance=instance, name=href, position=positioned_urls.count(href))
									url.save()
									params = {
										'instance' :instance.id,
										'recipient':recipient.id,
										'url'      :urllib.quote(href),
										'position' :positioned_urls.count(href),
									}
									params['mac'] = calc_url_mac(href, params['position'], params['recipient'], params['instance'])
									tracked_url = '?'.join([settings.PROJECT_URL + reverse('mailer-email-redirect'), urllib.urlencode(params)])
									customized_content = customized_content.replace('href="' + href + '"', 'href="' + tracked_url + '"')
									positioned_urls.append(href)
							
							# Tracking opens
							if email.track_opens:
								params = {
									'recipient':recipient.id,
									'instance' :instance.id
								}
								params['mac'] = calc_open_mac(params['recipient'], params['instance'])
								customized_content += '<img src="' + settings.PROJECT_URL + reverse('mailer-email-open') + '?' + urllib.urlencode(params) + '" />'

							# Construct the final SMTP headers
							final_smtp_headers = smtp_headers.copy()
							final_smtp_headers['To: '] = recipient.smtp_address

							msg = '\r\n'.join(list(k + v for k,v in final_smtp_headers.items())) + '\r\n\r\n' + customized_content

							instance_details_kwargs = {
								'instance'  :instance,
								'recipient' :recipient,
							}

							try:
								log.debug('From: %s To: %s' % (email.from_email_address, recipient.email_address))
								response = amazon_ses.sendmail(email.from_email_address, recipient.email_address, msg)
								time.sleep(settings.AMAZON_SMTP.rate)
								log.debug(' '.join([recipient.email_address, str(response)]))	
							except smtplib.SMTPRecipientsRefused, e: # Exception Type 0
								instance_details_kwargs['exception_type'] = 0
								instance_details_kwargs['exception_msg']  = str(e)
								log.error(' '.join([recipient.email_address, str(e)]))
							except smtplib.SMTPHeloError, e:         # Exception type 1
								instance_details_kwargs['exception_type'] = 1
								log.error(' '.join([recipient.email_address, str(e)]))
							except smtplib.SMTPSenderRefused, e:     # Exception type 2
								instance_details_kwargs['exception_type'] = 2
								log.error(' '.join([recipient.email_address, str(e)]))
							except smtplib.SMTPDataError, e:         # Exception type 3
								instance_details_kwargs['exception_type'] = 3
								log.error(' '.join([recipient.email_address, str(e)]))
							instance_details = InstanceRecipientDetails(**instance_details_kwargs)
							instance_details.save()
				instance.in_progress = False
				instance.end = datetime.now()
				instance.save()
			amazon_ses.quit()
