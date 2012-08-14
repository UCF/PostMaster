from django.core.management.base import BaseCommand
from manager.models               import Email, Instance, RecipientGroup, Recipient, InstanceRecipientDetails, URL
from datetime                    import datetime, timedelta
from django.conf                 import settings
from util                        import calc_url_mac, calc_open_mac, calc_unsubscribe_mac
from django.core.urlresolvers    import reverse
from email.mime.multipart        import MIMEMultipart
from email.mime.text             import MIMEText
import calendar
import hashlib
import smtplib
import logging
import re
import urllib
import time
 
log = logging.getLogger(__name__)

#
# Email Sending Process
# 1. Which emails are being sent sometime today? Check all the Email
# object start dates taking into account recurrence.
# 2. Do any of the emails being sent today require previews and, if so, do
# those previews need to be sent during this script run (the next 15 minutes by default)? 
# Previews are sent 1 hour  before the actual email is sent. Check the Email object 
# send times to figure this out.
# 3. Construct email content taking into account template replacements and
# send previews.
# 4. Do any of the emails being sent today need to be sent in this script run 
# (the next 15 minutes by default)? Check the Email object send times to figure
# this out.
# 5. Construct email content taking into account template replacments, URL click
# tracking, and open tracking and send emails. 
# 6. Record sending details.

class SendingManager(object):
	'''
		Responsible for the overall supervision of sending the emails.
	'''

	class SendingManagerException(Exception):
		pass

	def __init__(self, *args, **kwargs):
		pass

class ContentResolver(object):
	 '''
	 	Responsible for resolving the content of an email including template
	 	replacement and tracking details.
	 '''

	 class ContentResolverException(Exception):
	 	pass

	 _content_cache = None

	 def __init__(self, email):
	 	self.email = emails

	 def resolve_preview_content(self):
	 	'''
	 		Fetch the email content and prepend the preview messages.
	 	'''
		return '''
			<div style="background-color:#999;color:#FFF;font-size:18px;padding:20px;">
				This is a preview of the %s email that will be sent in 1 hour.
			</div>
			<br />
			%s
		''' % (email.title, email.content)


	def resolve_content(self, instance, recipient):
		'''
			Replace template placeholders.
			Track URLs if neccessary.
			Track clicks if necessary.
		'''
		content = instance.content
		# Template placeholders
		delimiter    = self.email.replace_delimiter
		placeholders = re.findall(re.escape(delimiter) + '([^' + re.escape(delimiter) + ']+)', content)
		for placeholder in placeholders:
			replacement = ''
			if placeholder.lower() == 'unsubscribe':
				unsubscribe_url = '?'.join([
					settings.PROJECT_URL + reverse('manager-email-unsubscribe'),
					urllib.urlencode({
						'recipient':recipient.pk,
						'email'    :self.email.pk,
						'mac'      :calc_unsubscribe_mac(recipient.pk, self.email.pk)
					})
				])
				replacement = '<a style="color:blue;text-decoration:underline;" href="%s">Unsubscribe</a>' % unsubscribe_url
			else:
				try:
					replacement = getattr(recipient, placeholder)
				except AttributeError:
					log.error('Recipeint %s is missing attribute %s' % (str(recipient), placeholder))
			content = content.replace(delimiter + placeholder + delimiter, replacement)

		if instance.urls_tracked:
			def gen_tracking_url(match):
				url = match.groups(0)

				# The same URL might exist in more than one place in the content.
				# Use the position field to differentiate them
				previous_url_count = URL.objects.filter(instnace=instance, name=url).count()
				tracking_url       = URL.objects.create(instance=instance, name=url, position=previous_url_count)

				# The mac uniquely identifies the recipient and acts as a secure integrity check
				mac = calc_url_mac(url, previous_url_count, recipient.pk, instance.pk)

				return '?'.join([
					settings.PROJECT_UR + reverse('manager-email-redirect'),
					urllib.urlencode({
						'instance'  :instance.pk,
						'recipient' :recipient.pk,
						'url'       :urllib.quote(url),
						'position'  :previous_url_count
					})
				])

			content = re.sub('<a.*href="([^"]+)"', gen_tracking_url, content)

		if instance.opens_tracked:
			open_tracking_url = '?'.join([
				settings.PROJECT_URL + reverse('manager-email-open'),
				urllib.urlencode({
					'recipient':recipient.pk,
					'instance' :instance.pk,
					'mac'      :calc_open_mac(recipient.pk, instance.pk)
				})
			])
			content += '<img src="%s" />' % open_tracking_url

		return content

class Sender(object):
	'''
		Responsible for sending the emails.
	'''

	class SenderException(Exception):
		pass

	def __init__(self, email):
		self.email = email

	def create_email_instance(self):
		'''
			Create an email instance making sure to realize that the remote
			content might not be available/fail to be fetched.
		'''
		try:
			content = self.email.content
		except Exception, e:
			logging.exception('Unable to fetch email content')
			raise self.SenderException()
		else:
			self.instance = Instance.objects.create(
				email         = self.email,
				content       = content,
				in_progress   = True,
				opens_tracked = self.email.track_opens,
				urls_tracked  = self.email.track_urls
			)

	def generate_recipient_list(self):
		'''
			Generates a queryset of recipients based on the email recipient
			groups making sure to remove duplicated
		'''
		return Recipient.objects.fitler(groups__in = self.email.recipient_groups).distinct()


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
		for email in Email.objects.filter(active=True):
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
		
		# Previews - 1 hour before the email is supposed to go out
		preview_kwargs = {
			'id__in'                     : todays_email_ids,
			'send_times__send_time__gte' : (now_dt + timedelta(seconds=60 * 60)).time(),
			'send_times__send_time__lt'  : (later_dt + timedelta(seconds= 60 * 60)).time(),
			'active'                     : True,
			'preview'                    : True
		}
		preview_emails = Email.objects.filter(**preview_kwargs)

		log.debug('Emails being previewed in this run: ' + str(list(e.id for e in preview_emails)))

		for email in preview_emails:
			deactivate_uri = settings.PROJECT_URL + reverse('manager-email-deactivate', kwargs={'email_id':email.id})
			update_uri     = settings.PROJECT_URL + reverse('manager-email-update', kwargs={'email_id':email.id})
			deactivate_html = '''
				<div style="background-color:#000;color:#FFF;font-size:18px;padding:20px;">
					This is a preview of the %s email that will be sent in 1 hour.
					<br /><br />
					If it is not correct, you can either fix it before it is sent or <a style="color:blue;" href="%s">deactivate it</a> until it is fixed.
					It can be re-activated on the Change Settings screen <a style="color:blue;" href="%s">here</a>
				</div>
				<br />
			''' % (email.title, deactivate_uri, update_uri)

			content = deactivate_html + email.content.decode('ascii', 'ignore')

			amazon_ses = smtplib.SMTP_SSL(settings.AMAZON_SMTP['host'], settings.AMAZON_SMTP['port'])
			amazon_ses.login(settings.AMAZON_SMTP['username'], settings.AMAZON_SMTP['password'])
			for recipient in email.preview_recipients.split(','):
				recipeint = recipient.strip()
				smtp_headers = {
					'From: '         : email.smtp_from_address,
					'Subject: '      : email.subject + ' **PREVIEW**',
					'Content-type: ' : 'text/html; charset=us-ascii',
					'To: '           : recipient
				}
				msg = '\r\n'.join(list(k + v for k,v in smtp_headers.items())) + '\r\n\r\n' + content
				try:
					response = amazon_ses.sendmail(email.from_email_address, recipient, msg)
				except Exception, e:
					log.error('Error sending preview email for `%s`: %s' % (email.title, str(e)))
			amazon_ses.quit()

		# Fetch all the emails that are due to be sent in the next 15 minutes
		email_kwargs = {
			'id__in'                      :todays_email_ids,
			'send_times__send_time__gte'  :now_t,
			'send_times__send_time__lt'   :later_t,
			'active'                      :True}
		emails = Email.objects.filter(**email_kwargs)

		log.debug('Emails being sent in this run: ' + str(list(e.id for e in emails)))

		for email in emails:
			content = email.content.decode('us-ascii','ignore')
			subject = email.subject.decode('us-ascii', 'ignore')

			instance = Instance(email=email, sent_html=content, in_progress=True, opens_tracked=email.track_opens, urls_tracked=email.track_urls)
			instance.save()

			amazon_ses = smtplib.SMTP_SSL(settings.AMAZON_SMTP['host'], settings.AMAZON_SMTP['port'])
			amazon_ses.login(settings.AMAZON_SMTP['username'], settings.AMAZON_SMTP['password'])
			for group in email.recipient_groups.all():
				for recipient in group.recipients.exclude(id__in = email.unsubscriptions.all()):

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
									if replace is None:
										replace = ''
									customized_content = customized_content.replace(find, replace)
						
						# Tracking URLs
						if instance.urls_tracked:
							hrefs = re.findall('<a.*href="([^"]+)"', customized_content)

							positioned_urls = []
							for href in hrefs:
								# Records these URLs so they can be tracked
								try:
									url = URL.objects.get(instance=instance, name=href, position=positioned_urls.count(href))
								except URL.DoesNotExist:
									url = URL(instance=instance, name=href, position=positioned_urls.count(href))
									url.save()
								params = {
									'instance' :instance.id,
									'recipient':recipient.id,
									'url'      :urllib.quote(href),
									'position' :positioned_urls.count(href),
								}
								params['mac']      = calc_url_mac(href, params['position'], params['recipient'], params['instance'])
								tracked_url        = '?'.join([settings.PROJECT_URL + reverse('manager-email-redirect'), urllib.urlencode(params)])
								customized_content = customized_content.replace('href="' + href + '"', 'href="' + tracked_url + '"')
								positioned_urls.append(href)
						
						# Tracking opens
						if instance.opens_tracked:
							params = {
								'recipient':recipient.id,
								'instance' :instance.id
							}
							params['mac'] = calc_open_mac(params['recipient'], params['instance'])
							customized_content += '<img src="' + settings.PROJECT_URL + reverse('manager-email-open') + '?' + urllib.urlencode(params) + '" />'

						# Built-in mappings we don't want tracked
						## Unsubscribe
						customized_content = customized_content.replace('!@!UNSUBSCRIBE!@!', '<a style="color:blue;text-decoration:underline;" href="%s">Unsubscribe</a>' % recipient.unsubscribe_uri(email))


						msg = MIMEMultipart('alternative')
						msg['Subject'] = subject
						msg['From']    = email.smtp_from_address
						msg['To']      = recipient.smtp_address

						msg.attach(MIMEText(customized_content, 'html', _charset="us-ascii"))

						instance_details_kwargs = {
							'instance'  :instance,
							'recipient' :recipient,
						}

						try:
							log.debug('From: %s To: %s' % (email.from_email_address, recipient.email_address))
							response = amazon_ses.sendmail(email.from_email_address, recipient.email_address, msg.as_string())
							time.sleep(settings.AMAZON_SMTP['rate'])
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
			amazon_ses.quit()
			instance.in_progress = False
			instance.end = datetime.now()
			instance.save()
				
