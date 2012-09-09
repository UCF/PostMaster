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

	def set_groups(self, groups):
		if groups is not None:
			remove_groups = []

			for group in self.groups.all():
				if group not in groups:
					remove_groups.append(group)
			self.groups.remove(*remove_groups)
			self.groups.add(*groups)

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
		return Email.objects.sending_today(now=now).filter(
			active         = True,
			send_time__gte = send_interval_start,
			send_time__lte = send_interval_end).exclude(
				instances__requested_start = F('send_time'),
				instnaces__end             = None
			)


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
			send_time__lte = preview_interval_end).exclude(
				instances__requested_start = F('send_time')
			)


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
				page    = urllib.urlopen(self.source_html_uri)
				content = page.read()
				return content.decode('ascii', 'ignore')
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
				return content.decode('ascii', 'ignore')
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
				requested_start = self.send_time
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

		# Fetch the email content. At this point, it is not customized
		# for each recipient.
		html = self.html
		
		try:
			text = self.text
		except self.TextContentMissingException:
			text = None

		instance = Instance.objects.create(
			email           = self,
			sent_html       = html,
			requested_start = self.send_time,
			opens_tracked   = self.track_opens,
			urls_tracked    = self.track_urls
		)

		recipients = Recipient.objects.filter(groups__in = self.recipient_groups.all()).exclude(pk__in=self.unsubscriptions.all()).distinct()

		# Create all the instancerecipientdetails before hand so in case sending
		# fails, we know who hasn't been sent too
		for recipient in recipients:
			InstanceRecipientDetails.objects.create(
				recipient = recipient,
				instance  = instance
			)

		try:
			# It's possible to refactor this sending block to be multi-threaded.
			# Use the instancerecipientdetails.when field as a sent/not sent flag
			# in order to implement queue-like functionality.
			try:
				amazon = smtplib.SMTP_SSL(settings.AMAZON_SMTP['host'], settings.AMAZON_SMTP['port'])
				amazon.login(settings.AMAZON_SMTP['username'], settings.AMAZON_SMTP['password'])
			except smtplib.SMTPException, e:
				log.exception('Unable to connect to Amazon')
				raise self.EmailException()
			else:
				for instance_recipient_details in instance.recipient_details.all():

					# Use alterantive subclass here so that both HTML and plain
					# versions can be attached
					msg            = MIMEMultipart('alternative')
					msg['subject'] = self.subject + str(additional_subject)
					msg['From']    = self.smtp_from_address
					msg['To']      = recipient.email_address

					msg.attach(MIMEText(instance_recipient_details.html, 'html', _charset='us-ascii'))

					if text is not None:
						msg.attach(MIMEText(text, 'plain', _charset='us-ascii' ))

					try:
						amazon.sendmail(self.from_email_address, recipient.email_address, msg.as_string())
					except smtplib.SMTPException, e:
						instance_recipient_details.exception_msg = str(e)
					finally:
						instance_recipient_details.when = datetime.now()
						instance_recipient_details.save()
					time.sleep(settings.AMAZON_SMTP['rate'])
				amazon.quit()
				instance.success = True
		except Exception, e:
			instance.success = False
			log.exception('Unable to send email.')
		finally:
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
	requested_start = models.TimeField()
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
		total = self.recipient_details.count()
		opens = self.opens.count()

		return 0 if total == 0 else round(float(opens)/float(total)*100, significance)

	class Meta:
		ordering = ('-start',)

class PreviewInstance(models.Model):
	'''
		Record that a preview was sent
	'''
	email           = models.ForeignKey(Email, related_name='previews')
	recipients      = models.TextField()
	requested_start = models.TimeField()
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
			if placeholder.lower() != 'unsubscribe':
				try:
					replacement = getattr(self.recipient, placeholder)
				except AttributeError:
					log.error('Recipeint %s is missing attribute %s' % (str(self.recipient), placeholder))
				html = html.replace(delimiter + placeholder + delimiter, replacement)

		if self.instance.urls_tracked:
			instance     = self.instance
			tracked_urls = {}
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
					# Use the position field to differentiate them.
					# This is done on a per-email basis rather than a per-recipient basis.
					try:
						tracked_urls[url] += 1
					except KeyError:
						tracked_urls[url] = 0

					previous_url_count = tracked_urls[url]

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

		# Replace the unsubscribe URL after everything else
		html = re.sub(
			re.escape(delimiter) + 'unsubscribe' + re.escape(delimiter),
			'<a href="%s" style="color:blue;text-decoration:none;">unsubscribe</a>' %
				'?'.join([
					settings.PROJECT_URL + reverse('manager-email-unsubscribe'),
					urllib.urlencode({
						'recipient':self.recipient.pk,
						'email'    :self.instance.email.pk,
						'mac'      :calc_unsubscribe_mac(self.recipient.pk, self.instance.email.pk)
					})
				]),
			html,
			flags=re.IGNORECASE)

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
