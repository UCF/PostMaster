from django.db   import models
from django.conf import settings
import hmac
import calendar
import datetime
import urllib
import re

class Recipient(models.Model):
	'''
		Describes the details of a possible email recipient
	'''

	LABELABLE_FIELD_NAMES = [
		('first_name',           'First name'),
		('last_name',            'Last Name'),
		('email_address',        'Email Address'),
		('preferred_first_name', 'Preferred First Name')
	]

	first_name      = models.CharField(max_length=100, null=True, blank=True)
	last_name       = models.CharField(max_length=100, null=True, blank=True)
	email_address   = models.CharField(max_length=256)
	preferred_name  = models.CharField(max_length=200, null=True, blank=True)

	@property
	def hmac_hash(self):
		return hmac.new(settings.SECRET_KEY, self.email_address).hexdigest()

	@property
	def smtp_address(self):
		if self.preferred_first_name is None or self.last_name is None:
			return self.email_address
		else:
			return '"%s %s" <%s>' % (self.preferred_first_name, self.last_name, self.email_address)

	@property
	def preferred_first_name(self):
		if self.preferred_name is None or self.preferred_name == '':
			return self.first_name
		else:
			preferred_first_name = re.sub('\s%s$' % self.last_name, '', self.preferred_name)
			if preferred_first_name ==self.preferred_name or preferred_first_name == '':
				return self.first_name
			else:
				return preferred_first_name
				
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

	def unsubscribe_uri(self, email):
		from util                        import calc_unsubscribe_mac
		from urllib                      import urlencode
		from django.core.urlresolvers    import reverse
		params = {'recipient':self.pk, 'email':email.pk, 'mac':calc_unsubscribe_mac(self.pk, email.pk)}
		return '?'.join([settings.PROJECT_URL + reverse('manager-email-unsubscribe'), urlencode(params)])

	def __str__(self):
		return ' '.join([str(self.first_name), str(self.last_name), str(self.preferred_name), self.email_address])

class RecipientRole(models.Model):
	'''
		Descibes the roles of a particular recipient. recipients
	'''

	ROLE_CHOICES = (
		(0, 'Student'),
		(1, 'Staff'),
		(2, 'Facutly'),
		(3, 'Alumni')
	)
	pass


class RecipientGroup(models.Model):
	'''
		Describes the details of a named group of email recipients
	'''
	name       = models.CharField(max_length=100, unique=True)
	recipients = models.ManyToManyField(Recipient, related_name='groups')

	def __str__(self):
		return self.name + ' (' +  str(self.recipients.count()) + ' recipients)'

class Email(models.Model):
	'''
		Describes the details of an email 
	'''

	class Recurs:
		never, daily, weekly, biweekly, monthly, yearly = range(0,6)
		choices = (
			(never    , 'Never'),
			(daily    , 'Daily'),
			(weekly   , 'Weekly'),
			(biweekly , 'Biweekly'),
			(monthly  , 'Monthly'),
			(yearly   , 'Yearly'),
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
	def content(self):
		if self.html != '':
			return self.html
		else:
			page = urllib.urlopen(self.source_uri)
			return page.read()

	def __str__(self):
		return self.title

class Instance(models.Model):
	'''
		Describes a sending of an email based on its schedule
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
	
	class Meta:
		ordering = ('-start',)

class InstanceRecipientDetails(models.Model):
	'''
		Describes the response from the SMTP server
		when an email was sent to a particular recipient
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

class URL(models.Model):
	'''
		Describes a particular URL in an email
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
		Describes a recipient opening an email
	'''
	recipient = models.ForeignKey(Recipient, related_name='instances_opened')
	instance  = models.ForeignKey(Instance, related_name='opens')
	when      = models.DateTimeField(auto_now_add=True)
