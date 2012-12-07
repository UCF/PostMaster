from django.db                import models
from django.conf              import settings
from datetime                 import datetime, timedelta
from django.db.models         import Q, F
from util                     import calc_url_mac, calc_open_mac, calc_unsubscribe_mac
from django.core.urlresolvers import reverse
from email.mime.multipart     import MIMEMultipart
from email.mime.text          import MIMEText
from django.http              import HttpResponseRedirect
from django.core.exceptions   import SuspiciousOperation
import hmac
import logging
import smtplib
import re
import urllib
import time
import Queue
import threading
import requests
import random

log = logging.getLogger(__name__)

class Recipient(models.Model):
	'''
		Describes the details of a recipient
	'''

	email_address   = models.CharField(max_length=255, unique=True)

	def save(self, *args, **kwargs):
		if self.pk is None:
			self.email_address = self.email_address.lower()
		super(Recipient, self).save(*args, **kwargs)

	def __getattr__(self, name):
		'''
			Try to lookup a missing attribute in RecipientAttribute if it's not defined.
		'''
		try:
			attribute = RecipientAttribute.objects.get(recipient=self.pk, name=name)
		except RecipientAttribute.DoesNotExist:
			raise AttributeError
		else:
			return attribute.value.encode('ascii', 'ignore')

	@property
	def hmac_hash(self):
		return hmac.new(settings.SECRET_KEY, self.email_address).hexdigest()
				
	@property
	def subscriptions(self, include_deactivated=False):
		'''
			What emails is this recipient set to receive.
		'''
		emails = []
		for group in self.groups.all():
			group_emails = group.emails.all() if include_deactivated is True else group.emails.filter(active=True)
			emails.extend(list(group_emails))
		return Email.objects.filter(pk__in=[e.pk for e in emails]).distinct()

	def set_groups(self, groups):
		if groups is not None:
			remove_groups = []

			for group in self.groups.all():
				if group not in groups:
					remove_groups.append(group)
			self.groups.remove(*remove_groups)
			self.groups.add(*groups)

	@property
	def unsubscribe_url(self):
		return '?'.join([
			settings.PROJECT_URL + reverse('manager-email-unsubscribe', kwargs={'pk':self.pk}),
			urllib.urlencode({
				'mac'      :calc_unsubscribe_mac(self.pk)
			})
		])

	def __str__(self):
		return self.email_address

class RecipientAttribute(models.Model):
	'''
		Describes an attribute of a recipient. The purpose of this class is 
		to allow a large amount of flexibility about what attributes are associated
		with a recipient (other than email address). The __getattr__ on Recipient
		is overriden to check for a RecipientAttribute of the same name and return
		it's value. This table is populated by the custom import script for each
		data source.
	'''
	recipient = models.ForeignKey(Recipient, related_name='attributes')
	name      = models.CharField(max_length=100)
	value     = models.CharField(max_length=1000,blank=True)

	class Meta:
		unique_together  = (('recipient', 'name'))

class RecipientGroup(models.Model):
	'''
		Describes a named group of recipients. Email objects are not associated with
		Recipient objects directly. They are associated to each other via RecipientGroup.
	'''
	name       = models.CharField(max_length=100, unique=True)
	recipients = models.ManyToManyField(Recipient, related_name='groups')

	def __str__(self):
		return self.name + ' (' +  str(self.recipients.count()) + ' recipients)'

class EmailManager(models.Manager):
	'''
		A custom manager to determine when emails should be sent based on
		processing interval and preview lead time.
	'''
	processing_interval_duration = timedelta(seconds=settings.PROCESSING_INTERVAL_DURATION)

	def sending_today(self, now=None):
		if now is None:
			now = datetime.now()
		today = now.date()

		return Email.objects.filter(
			Q(
				# One-time
				Q(Q(recurrence=self.model.Recurs.never) & Q(start_date=today)) |
				# Daily
				Q(recurrence=self.model.Recurs.daily) |
				# Weekly
				Q(Q(recurrence=self.model.Recurs.weekly) & Q(start_date__week_day=today.isoweekday() % 7 + 1)) |
				# Monthly
				Q(Q(recurrence=self.model.Recurs.monthly) & Q(start_date__day=today.day))
			),
			active=True
		)

	def sending_now(self, now=None):
		if now is None:
			now = datetime.now()
		send_interval_start = now.time()
		send_interval_end   = (now + self.processing_interval_duration).time()
		
		# Exclude emails outside this sending interval
		# Exclude emails with instances that have the same requested_start or
		# or are in progress (end=None)
		email_pks = []
		for candidate in Email.objects.sending_today(now=now):
			if candidate.send_time >= send_interval_start and candidate.send_time <= send_interval_end:
				requested_start = datetime.combine(now.date(), candidate.send_time)
				if candidate.instances.filter(requested_start=requested_start).count() == 0:
					email_pks.append(candidate.pk)
		return Email.objects.filter(pk__in=email_pks)


	def previewing_now(self, now=None):
		if now is None:
			now = datetime.now()
		preview_lead_time           = timedelta(seconds=settings.PREVIEW_LEAD_TIME)
		preview_interval_start      = (now + preview_lead_time).time()
		preview_interval_end        = (now + preview_lead_time + self.processing_interval_duration).time()

		# Exclude emails outside this previewing interval
		# Exclude emails with instances that have the same requested_start or
		# or are in progress (end=None)
		email_pks = []
		for candidate in Email.objects.sending_today(now=now).filter(preview=True):
			if candidate.send_time >= preview_interval_start and candidate.send_time <= preview_interval_end:
				requested_start = datetime.combine(now.date(), candidate.send_time)
				if candidate.previews.filter(requested_start=requested_start).count() == 0:
					email_pks.append(candidate.pk)
		return Email.objects.filter(pk__in=email_pks)

class Email(models.Model):
	'''
		Describes the details of an email. The details of what happens when
		an email is actual sent is recorded in an Instance object.
	'''

	objects = EmailManager()

	class EmailException(Exception):
		pass

	class AmazonConnectionException(EmailException):
		pass

	class EmailSendingException(EmailException):
		pass

	class TextContentMissingException(EmailException):
		pass

	class HTMLContentMissingException(EmailException):
		pass

	class Recurs:
		never, daily, weekly, biweekly, monthly = range(0,5)
		choices = (
			(never    , 'Never'),
			(daily    , 'Daily'),
			(weekly   , 'Weekly'),
			(biweekly , 'Biweekly'),
			(monthly  , 'Monthly'),
		)

	_HELP_TEXT = {
		'active'            : 'Whether the email is active or not. Inactive emails will not be sent',
		'title'             : 'Internal identifier of the email',
		'subject'           : 'Subject of the email',
		'source_html_uri'   : 'Source URI of the email HTML',
		'source_text_uri'   : 'Source URI of the email text',
		'start_date'        : 'Date that the email will first be sent.',
		'send_time'         : 'Format: %H:%M or %H:%M:%S. Time of day when the email will be sent. Times will be rounded to the nearest quarter hour.',
		'recurrence'        : 'If and how often the email will be resent.',
		'replace_delimiter' : 'Character(s) that replacement labels are wrapped in.',
		'recipient_groups'  : 'Which group(s) of recipients this email will go to.',
		'from_email_address': 'Email address from where the sent emails will originate',
		'from_friendly_name': 'A display name associated with the from email address',
		'track_urls'        : 'Rewrites all URLs in the email content to be recorded',
		'track_opens'       : 'Adds a tracking image to email content to track if and when an email is opened.',
		'preview'           : 'Send a preview to a specific set of individuals allowing them to proof the content.',
		'preview_recipients': 'A comma-separated list of preview recipient email addresses'
	}

	active             = models.BooleanField(default=False, help_text=_HELP_TEXT['active'])
	title              = models.CharField(max_length=100, help_text=_HELP_TEXT['title'])
	subject            = models.CharField(max_length=998, help_text=_HELP_TEXT['subject'])
	source_html_uri    = models.URLField(help_text=_HELP_TEXT['source_html_uri'])
	source_text_uri    = models.URLField(null=True, blank=True, help_text=_HELP_TEXT['source_text_uri'])
	start_date         = models.DateField(help_text=_HELP_TEXT['start_date'])
	send_time          = models.TimeField(help_text=_HELP_TEXT['send_time'])
	recurrence         = models.SmallIntegerField(null=True, blank=True, default=Recurs.never, choices=Recurs.choices, help_text=_HELP_TEXT['recurrence'])
	from_email_address = models.CharField(max_length=256, help_text=_HELP_TEXT['from_email_address'])
	from_friendly_name = models.CharField(max_length=100, blank=True, null=True, help_text=_HELP_TEXT['from_friendly_name'])
	replace_delimiter  = models.CharField(max_length=10, default='!@!', help_text=_HELP_TEXT['replace_delimiter'])
	recipient_groups   = models.ManyToManyField(RecipientGroup, related_name='emails', help_text=_HELP_TEXT['recipient_groups'])
	track_urls         = models.BooleanField(default=False, help_text=_HELP_TEXT['track_urls'])
	track_opens        = models.BooleanField(default=False, help_text=_HELP_TEXT['track_opens'])
	preview            = models.BooleanField(default=True, help_text=_HELP_TEXT['preview'])
	preview_recipients = models.TextField(null=True, blank=True, help_text=_HELP_TEXT['preview_recipients'])
	unsubscriptions    = models.ManyToManyField(Recipient, related_name='unsubscriptions')
	
	@property
	def smtp_from_address(self):
		if self.from_friendly_name:
			return '"%s" <%s>' % (self.from_friendly_name, self.from_email_address)
		else:
			return self.from_email_address

	@property
	def total_sent(self):
		return sum(list(i.recipient_details.count() for i in self.instances.all()))

	@property
	def html(self):
		'''
			Fetch and decode the remote html.
		'''
		if self.source_html_uri == '':
			raise HTMLContentMissingException()
		else:
			try:
				request = requests.get(self.source_html_uri)
				return request.text.encode('ascii', 'ignore')
			except IOError, e:
				log.exception('Unable to fetch email html')
				raise self.EmailException()

	@property
	def text(self):
		'''
			Fetch and decode the remote text.
			Raise TextContentMissingException is the source_text_uri field is blank.
		'''
		if self.source_text_uri is None or self.source_text_uri == '':
			raise self.TextContentMissingException()
		else:
			try:
				page = urllib.urlopen(self.source_text_uri)
				content = page.read()
				return content.encode('ascii', 'ignore')
			except IOError, e:
				log.exception('Unable to fetch email text')
				raise self.EmailException()

	def send_preview(self):
		'''
			Send preview emails
		'''
		html = self.html

		try:
			text = self.text
		except self.TextContentMissingException:
			text = None

		# The recipients for the preview emails aren't the same as regular
		# recipients. They are defined in the comma-separate field preview_recipients
		recipients = [r.strip() for r in self.preview_recipients.split(',')]

		# Prepend a message to the content explaining that this is a preview
		html_explanation = '''
			<div style="background-color:#000;color:#FFF;font-size:18px;padding:20px;">
				This is a preview of an email that will go out in one (1) hour.
				<br /><br />
				The content of the email when it is sent will be re-requested from 
				the source for the real delivery.
			</div>
		'''
		text_explanation = 'This is a preview of an email that will go out in one (1) hour.\n\nThe content of the email when it is sent will be re-requested from the source for the real delivery.'

		try:
			amazon = smtplib.SMTP_SSL(settings.AMAZON_SMTP['host'], settings.AMAZON_SMTP['port'])
			amazon.login(settings.AMAZON_SMTP['username'], settings.AMAZON_SMTP['password'])
		except smtplib.SMTPException, e:
			log.exception('Unable to connect to Amazon')
			raise self.AmazonConnectionException()
		else:
			preview_instance = PreviewInstance.objects.create(
				email           = self,
				recipients      = self.preview_recipients,
				requested_start = datetime.combine(datetime.now().today(), self.send_time)
			)

			for recipient in recipients:
				# Use alterantive subclass here so that both HTML and plain
				# versions can be attached
				msg            = MIMEMultipart('alternative')
				msg['subject'] = self.subject + ' **PREVIEW**'
				msg['From']    = self.smtp_from_address
				msg['To']      = recipient

				msg.attach(MIMEText(html_explanation + html, 'html', _charset='us-ascii'))

				if text is not None:
					msg.attach(MIMEText(text_explanation + text, 'plain', _charset='us-ascii' ))

				try:
					amazon.sendmail(self.from_email_address, recipient, msg.as_string())
				except smtplib.SMTPException, e:
					log.exception('Unable to send email.')
			amazon.quit()

	def send(self, additional_subject=''):
		'''
			Send an email instance.
			1. Fetch the content.
			2. Create the instance.
			3. Fetch recipients
			4. Connect to Amazon
			5. Create the InstanceRecipientDetails for each recipient
			6. Construct the customized message
			7. Send the message
			8. Cleanup

			Takes additional_subject for testing purposes
		'''

		class SendingThread(threading.Thread):
			
			_AMAZON_RECONNECT_THRESHOLD = 10
			_ERROR_THRESHOLD            = 20

			def run(self):
				amazon             = None
				reconnect          = False
				reconnect_counter  = 0
				error              = False
				error_counter      = 0
				rate_limit_counter = 0
				
				while True:
					if recipient_details_queue.empty():
						log.debug('%s queue empty, exiting.' % self.name)
						break

					recipient_details = recipient_details_queue.get()

					try:
						if amazon is None or reconnect:
							try:
								amazon = smtplib.SMTP_SSL(settings.AMAZON_SMTP['host'], settings.AMAZON_SMTP['port'])
								amazon.login(settings.AMAZON_SMTP['username'], settings.AMAZON_SMTP['password'])
							except:
								if reconnect_counter == SendingThread._AMAZON_RECONNECT_THRESHOLD:
									log.debug('%s, reached reconnect threshold, exiting')
									raise
								reconnect_counter += 1
								reconnect         = True
								continue
							else:
								reconnect = False

						# Customize the email for this recipient
						customized_html = recipient_details.instance.sent_html
						# Replace template placeholders
						delimiter = recipient_details.instance.email.replace_delimiter
						for placeholder in placeholders:
							replacement = ''
							if placeholder.lower() != 'unsubscribe':
								if recipient_attributes[recipient_details.recipient.pk][placeholder] is None:
									log.error('Recipient %s is missing attribute %s' % (str(recipient_details.recipient), placeholder))
								else:
									replacement = recipient_attributes[recipient_details.recipient.pk][placeholder]
								customized_html = customized_html.replace(delimiter + placeholder + delimiter, replacement)
						# URL Tracking
						if recipient_details.instance.urls_tracked:
							for url in tracking_urls:
								customized_html = customized_html.replace(
									url.name,
									'?'.join([
										settings.PROJECT_URL + reverse('manager-email-redirect'),
										urllib.urlencode({
											'instance'  :recipient_details.instance.pk,
											'recipient' :recipient_details.recipient.pk,
											'url'       :urllib.quote(url.name),
											'position'  :url.position,
											# The mac uniquely identifies the recipient and acts as a secure integrity check
											'mac'       :calc_url_mac(url.name, url.position, recipient_details.recipient.pk, recipient_details.instance.pk)
										})
									]),
									1
								)
						# Open Tracking
						if recipient_details.instance.opens_tracked:
							customized_html += '<img src="%s" />' % '?'.join([
								settings.PROJECT_URL + reverse('manager-email-open'),
								urllib.urlencode({
									'recipient':recipient_details.recipient.pk,
									'instance' :recipient_details.instance.pk,
									'mac'      :calc_open_mac(recipient_details.recipient.pk, recipient_details.instance.pk)
								})
							])
						# Unsubscribe link
						customized_html = re.sub(
							re.escape(delimiter) + 'UNSUBSCRIBE' + re.escape(delimiter),
							'<a href="%s" style="color:blue;text-decoration:none;">unsubscribe</a>' % recipient_details.recipient.unsubscribe_url,
							customized_html)

						# Construct the message
						msg            = MIMEMultipart('alternative')
						msg['subject'] = subject
						msg['From']    = display_from
						msg['To']      = recipient_details.recipient.email_address
						msg.attach(MIMEText(customized_html, 'html', _charset='us-ascii'))
						if text is not None:
							msg.attach(MIMEText(text, 'plain', _charset='us-ascii' ))

						log.debug('thread: %s, email: %s' % (self.name, recipient_details.recipient.email_address))
						try:
							amazon.sendmail(real_from, recipient_details.recipient.email_address, msg.as_string())
						except smtplib.SMTPResponseException, e:
							if e.smtp_error.find('Maximum sending rate exceeded') >= 0:
								recipient_details_queue.put(recipient_details)
								log.debug('thread %s, maximum sending rate exceeded, sleeping for a bit')
								time.sleep(float(1) + random.random())
							else:
								recipient_details.exception_msg = str(e)
						except smtplib.SMTPServerDisconnected:
							# Connection error
							log.debug('thread %s, connection error, sleeping for a bit')
							time.sleep(float(1) + random.random())
							recipient_details_queue.put(recipient_details)
							reconnect = True
						else:
							recipient_details.when = datetime.now()
						finally:
							recipient_details.save()
					except Exception, e:
						if error_counter == SendingThread._ERROR_THRESHOLD:
							recipient_details_queue.task_done()
							log.debug('%s, reached error threshold, exiting')
							with recipient_details_queue.mutex:
								recipient_details_queue.queue.clear()
								return
						error_counter += 1
						log.exception('%s exception' % self.name)

					recipient_details_queue.task_done()

		try:
			text = self.text
		except self.TextContentMissingException:
			text = None

		instance = Instance.objects.create(
			email           = self,
			sent_html       = self.html,
			requested_start = datetime.combine(datetime.now().today(), self.send_time),
			opens_tracked   = self.track_opens,
			urls_tracked    = self.track_urls
		)

		recipients = Recipient.objects.filter(
			groups__in = self.recipient_groups.all()).exclude(
				pk__in=self.unsubscriptions.all()).distinct()

		# The interval between ticks is one second. This is used to make
		# sure that the threads don't exceed the sending limit
		subject                 = self.subject + str(additional_subject)
		display_from            = self.smtp_from_address
		real_from               = self.from_email_address
		recipient_details_queue = Queue.Queue()
		success                 = True
		recipient_attributes    = {}
		placeholders            = instance.placeholders
		tracking_urls           = instance.tracking_urls

		# Create all the instancerecipientdetails before hand so in case sending
		# fails, we know who hasn't been sent too
		# Here, also, we want to lookup the recipients attributes that are used
		# in the template. Do this upfront because looking up each one in the 
		# sending loop is too slow
		log.debug('building recipients and recipient attributes...')
		for recipient in recipients:
			recipient_attributes[recipient.pk] = {}
			for placeholder in placeholders:
				try:
					recipient_attributes[recipient.pk][placeholder] = getattr(recipient, placeholder)
				except AttributeError:
					recipient_attributes[recipient.pk][placeholder] = None

			recipient_details_queue.put(
				InstanceRecipientDetails.objects.create(
					recipient = recipient,
					instance  = instance))

		log.debug('spin up sending threads...')
		html_lock        = threading.Lock()
		for i in xrange(0, settings.AMAZON_SMTP['rate'] - 1):
			sending_thread = SendingThread()
			sending_thread.start()

		# Block the main thread until the queue is empty
		recipient_details_queue.join()

		instance.end = datetime.now()
		instance.save()

	def __str__(self):
		return self.title

class Instance(models.Model):
	'''
		Describes what happens when an email is actual sent.
	'''
	email           = models.ForeignKey(Email, related_name='instances')
	sent_html       = models.TextField()
	requested_start = models.DateTimeField()
	start           = models.DateTimeField(auto_now_add=True)
	end             = models.DateTimeField(null=True)
	success         = models.NullBooleanField(default=None)
	recipients      = models.ManyToManyField(Recipient, through='InstanceRecipientDetails')
	opens_tracked   = models.BooleanField(default=False)
	urls_tracked    = models.BooleanField(default=False)
	
	@property
	def in_progress(self):
		if self.start is not None and self.end is None:
			return True
		else:
			return False

	@property
	def open_rate(self, significance=2):
		'''
			Open rate of this instance as a percent.
		'''
		opens = self.opens.count()
		return 0 if self.sent_count == 0 else round(float(opens)/float(self.sent_count)*100, significance)

	@property
	def sent_count(self):
		return self.recipient_details.exclude(when=None).count()

	@property
	def placeholders(self):
		delimiter    = self.email.replace_delimiter
		placeholders = re.findall(re.escape(delimiter) + '(.+)' + re.escape(delimiter), self.sent_html)
		return filter(lambda p: p.lower() != 'unsubscribe', placeholders)

	@property
	def tracking_urls(self):
		if not self.urls_tracked:
			return []

		hrefs = re.findall('<a(?:.*)href="([^"]+)"', self.sent_html)
		urls  = []

		for href in hrefs:
			# Check to see if this URL is trackable. Links that don't start
			# with http, https or ftp will raise a SuspiciousOperation exception
			# when you try to HttpResponseRedirect them.
			# See HttpResponseRedirectBase in django/http/__init__.py
			try:
				HttpResponseRedirect(href)
			except SuspiciousOperation:
				continue
			else:
				urls.append(URL.objects.get_or_create(
					instance = self,
					name     = href,
					position = URL.objects.filter(instance=self, name=href).count())[0])
		return urls

	class Meta:
		ordering = ('-start',)

class PreviewInstance(models.Model):
	'''
		Record that a preview was sent
	'''
	email           = models.ForeignKey(Email, related_name='previews')
	recipients      = models.TextField()
	requested_start = models.DateTimeField()
	when            = models.DateTimeField(auto_now_add=True)

class InstanceRecipientDetails(models.Model):
	'''
		Describes what happens when an instance of an email is sent to specific
		recipient.
	'''

	recipient      = models.ForeignKey(Recipient, related_name='instance_receipts')
	instance       = models.ForeignKey(Instance, related_name='recipient_details')
	when           = models.DateTimeField(null=True)
	exception_msg  = models.TextField(null=True, blank=True)

class URL(models.Model):
	'''
		Describes a particular URL in email content
	'''
	instance = models.ForeignKey(Instance, related_name='urls')
	name     = models.CharField(max_length=2000)
	created  = models.DateTimeField(auto_now_add=True)

	# An email's content may have more than on link
	# to the same URL (e.g. multiple donate buttons
	# throughout an email).
	# Track these separately, ascending to descending
	# and left to right.
	position = models.PositiveIntegerField(default=0)

class URLClick(models.Model):
	'''
		Describes a recipient's clicking of a URL
	'''
	recipient = models.ForeignKey(Recipient, related_name='urls_clicked')
	url       = models.ForeignKey(URL, related_name='clicks')
	when      = models.DateTimeField(auto_now_add=True)

class InstanceOpen(models.Model):
	'''
		Describes a recipient's opening of an email
	'''
	recipient = models.ForeignKey(Recipient, related_name='instances_opened')
	instance  = models.ForeignKey(Instance, related_name='opens')
	when      = models.DateTimeField(auto_now_add=True)
