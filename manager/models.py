from django.db                import models
from django.conf              import settings
from datetime                 import datetime, timedelta
from django.db.models         import Q
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

log = logging.getLogger(__name__)

class Recipient(models.Model):
	'''
		Describes the details of a recipient
	'''

	email_address   = models.CharField(max_length=255, unique=True)

	def __getattr__(self, name):
		'''
			Try to lookup a missing attribute in RecipientAttribute if it's not defined.
		'''
		try:
			attribute = RecipientAttribute.objects.get(recipient=self.pk, name=name)
		except RecipientAttribute.DoesNotExist:
			raise AttributeError
		else:
			return attribute.value

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
			map(lambda e: emails.append(e), group_emails)
		return set(emails)

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

		# The day of the week integers are different between python and django
		# date.weekday() - Monday is 0 and Sunday is 6
		# date__week_day - Sunday is 1 and Saturday is 7
		week_day = today.weekday()
		if week_day == 6:
			week_day == 1
		else:
			week_day += 2

		return Email.objects.filter(
			Q(
				# One-time
				Q(Q(recurrence=self.model.Recurs.never) & Q(start_date=today)) |
				# Daily
				Q(recurrence=self.model.Recurs.daily) |
				# Weekly
				Q(Q(recurrence=self.model.Recurs.weekly) & Q(start_date__week_day=week_day)) |
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
		return Email.objects.sending_today(now=now).filter(
			active         = True,
			send_time__gte = send_interval_start,
			send_time__lte = send_interval_end)

	def previewing_now(self, now=None):
		if now is None:
			now = datetime.now()
		preview_lead_time           = timedelta(seconds=settings.PREVIEW_LEAD_TIME)
		preview_interval_start      = (now + preview_lead_time).time()
		preview_interval_end        = (now + preview_lead_time + self.processing_interval_duration).time()

		return Email.objects.sending_today(now=now).filter(
			active         = True,
			preview        = True,
			send_time__gte = preview_interval_start,
			send_time__lte = preview_interval_end)


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
		'source_uri'        : 'Source URI of the email content',
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
	source_uri         = models.URLField(help_text=_HELP_TEXT['source_uri'])
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
		try:
			page    = urllib.urlopen(self.source_uri)
			content = page.read()
			return content.decode('ascii', 'ignore')
		except Exception, e:
			logging.exception('Unable to fetch email html')
			raise self.EmailException()

	def send_preview(self):
		'''
			Send preview emails
		'''
		html = self.html

		# The recipients for the preview emails aren't the same as regular
		# recipients. They are defined in the comma-separate field preview_recipients
		recipients = [r.strip() for r in self.preview_recipients.split(',')]

		# Prepend a message to the content explaining that this is a preview
		explanation = '''
			<div style="background-color:#000;color:#FFF;font-size:18px;padding:20px;">
				This is a preview of an email that will go out in one (1) hour.
				<br /><br />
				The content of the email when it is sent will be re-requested from 
				the source for the real delivery.
			</div>
		'''
		try:
			amazon = smtplib.SMTP_SSL(settings.AMAZON_SMTP['host'], settings.AMAZON_SMTP['port'])
			amazon.login(settings.AMAZON_SMTP['username'], settings.AMAZON_SMTP['password'])
		except smtplib.SMTPException, e:
			logging.exception('Unable to connect to Amazon')
			raise self.AmazonConnectionException()
		else:
			for recipient in recipients:
				# Use alterantive subclass here so that both HTML and plain
				# versions can be attached
				msg            = MIMEMultipart('alternative')
				msg['subject'] = self.subject + ' **PREVIEW**'
				msg['From']    = self.smtp_from_address
				msg['To']      = recipient

				msg.attach(MIMEText(explanation + html, 'html', _charset='us-ascii'))

				# TODO - Implement plaintext alternative

				try:
					amazon.sendmail(self.from_email_address, recipient, msg.as_string())
				except smtplib.SMTPException, e:
					logging.exception('Unable to send email.')
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

		# Fetch the email content. At this point, it is not customized
		# for each recipient.
		html = self.html
		instance = Instance.objects.create(
			email         = self,
			sent_html     = html,
			in_progress   = True,
			opens_tracked = self.track_opens,
			urls_tracked  = self.track_urls
		)

		recipients = Recipient.objects.filter(groups__in = self.recipient_groups.all()).exclude(pk__in=self.unsubscriptions.all()).distinct()

		try:
			amazon = smtplib.SMTP_SSL(settings.AMAZON_SMTP['host'], settings.AMAZON_SMTP['port'])
			amazon.login(settings.AMAZON_SMTP['username'], settings.AMAZON_SMTP['password'])
		except smtplib.SMTPException, e:
			logging.exception('Unable to connect to Amazon')
			raise self.EmailException()
		else:
			for recipient in recipients:
				instance_recipient_details = InstanceRecipientDetails(
					recipient=recipient,
					instance =instance
				)

				# Use alterantive subclass here so that both HTML and plain
				# versions can be attached
				msg            = MIMEMultipart('alternative')
				msg['subject'] = self.subject + str(additional_subject)
				msg['From']    = self.smtp_from_address
				msg['To']      = recipient.email_address

				msg.attach(MIMEText(instance_recipient_details.html, 'html', _charset='us-ascii'))

				# TODO - Implement plaintext alternative

				try:
					amazon.sendmail(self.from_email_address, recipient.email_address, msg.as_string())
				except smtplib.SMTPException, e:
					instance_recipient_details.exception_msg = str(e)
				time.sleep(settings.AMAZON_SMTP['rate'])
				instance_recipient_details.save()
			amazon.quit()
		instance.in_progress = False
		instance.end        = datetime.now()
		instance.save()

	def __str__(self):
		return self.title

class Instance(models.Model):
	'''
		Describes what happens when an email is actual sent.
	'''
	email         = models.ForeignKey(Email, related_name='instances')
	sent_html     = models.TextField()
	start         = models.DateTimeField(auto_now_add=True)
	end           = models.DateTimeField(null=True)
	in_progress   = models.BooleanField(default=False)
	sent          = models.IntegerField(default=0)
	recipients    = models.ManyToManyField(Recipient, through='InstanceRecipientDetails')
	opens_tracked = models.BooleanField(default=False)
	urls_tracked  = models.BooleanField(default=False)
	
	def open_rate(self, significance=2):
		'''
			Open rate of this instance as a percent.
		'''
		total = self.recipient_details.count()
		opens = self.opens.count()

		return 0 if total == 0 else round(float(opens)/float(total)*100, significance)

	class Meta:
		ordering = ('-start',)

class InstanceRecipientDetails(models.Model):
	'''
		Describes what happens when an instance of an email is sent to specific
		recipient.
	'''

	_EXCEPTION_CHOICES = (
		(0, 'SMTPRecipientsRefused'),
		(1, 'SMTPHeloError'),
		(2, 'SMTPSenderRefused'),
		(3, 'SMTPDataError')
	)

	recipient      = models.ForeignKey(Recipient, related_name='instance_receipts')
	instance       = models.ForeignKey(Instance, related_name='recipient_details')
	when           = models.DateTimeField(auto_now_add=True)
	exception_type = models.SmallIntegerField(null=True, blank=True, choices=_EXCEPTION_CHOICES)
	exception_msg  = models.TextField(null=True, blank=True)

	@property
	def html(self):
		'''
			Replace template placeholders.
			Track URLs if neccessary.
			Track clicks if necessary.
		'''
		html = self.instance.sent_html
		
		# Template placeholders
		delimiter    = self.instance.email.replace_delimiter
		placeholders = re.findall(re.escape(delimiter) + '(.+)' + re.escape(delimiter), html)
		
		for placeholder in placeholders:
			replacement = ''
			if placeholder.lower() == 'unsubscribe':
				unsubscribe_url = '?'.join([
					settings.PROJECT_URL + reverse('manager-email-unsubscribe'),
					urllib.urlencode({
						'recipient':self.recipient.pk,
						'email'    :self.instance.email.pk,
						'mac'      :calc_unsubscribe_mac(self.recipient.pk, self.instance.email.pk)
					})
				])
				replacement = '<a style="color:blue;text-decoration:underline;" href="%s">Unsubscribe</a>' % unsubscribe_url
			else:
				try:
					replacement = getattr(self.recipient, placeholder)
				except AttributeError:
					log.error('Recipeint %s is missing attribute %s' % (str(self.recipient), placeholder))
			html = html.replace(delimiter + placeholder + delimiter, replacement)

		if self.instance.urls_tracked:
			instance = self.instance
			def gen_tracking_url(match):
				groups = match.groups()
				fill   = groups[0]
				url    = groups[1]
				
				# Check to see if this URL is trackable. Links that don't start
				# with http, https or ftp will raise a SuspiciousOperation exception
				# when you try to HttpResponseRedirect them.
				# See HttpResponseRedirectBase in django/http/__init__.py
				try:
					HttpResponseRedirect(url)
				except SuspiciousOperation:
					href = url
				else:
					# The same URL might exist in more than one place in the content.
					# Use the position field to differentiate them
					previous_url_count = URL.objects.filter(instance=instance, name=url).count()
					try:
						tracking_url = URL.objects.get(instance=instance, name=url, position=previous_url_count)
					except URL.DoesNotExist:
						tracking_url = URL.objects.create(instance=instance, name=url, position=previous_url_count)

					href = '?'.join([
						settings.PROJECT_URL + reverse('manager-email-redirect'),
						urllib.urlencode({
							'instance'  :self.instance.pk,
							'recipient' :self.recipient.pk,
							'url'       :urllib.quote(url),
							'position'  :previous_url_count,
							# The mac uniquely identifies the recipient and acts as a secure integrity check
							'mac'       :calc_url_mac(url, previous_url_count, self.recipient.pk, self.instance.pk)
						})
					])

				return '<a%shref="%s"' % (fill, href)

			html = re.sub('<a(.*)href="([^"]+)"', gen_tracking_url, html)

		if self.instance.opens_tracked:
			open_tracking_url = '?'.join([
				settings.PROJECT_URL + reverse('manager-email-open'),
				urllib.urlencode({
					'recipient':self.recipient.pk,
					'instance' :self.instance.pk,
					'mac'      :calc_open_mac(self.recipient.pk, self.instance.pk)
				})
			])
			html += '<img src="%s" />' % open_tracking_url

		return html

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
