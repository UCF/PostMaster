from django.db import models

class Recipient(models.Model):
	'''
		Describes the details of a possible email recipient
	'''

	LABELABLE_FIELD_NAMES = [
		('first_name',    'First name'),
		('last_name',     'Last Name'),
		('email_address', 'Email Address'),
	]

	first_name    = models.CharField(max_length=100)
	last_name     = models.CharField(max_length=100)
	email_address = models.CharField(max_length=100)

	def __str__(self):
		return ' '.join([self.first_name, self.last_name, self.email_address])

class RecipientGroup(models.Model):
	'''
		Describes the details of a named group of email recipients
	'''
	name       = models.CharField(max_length=100)
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
		'title'             : 'Internal identifier of the email',
		'html'              : 'HTML source code of the email content',
		'source_uri'        : 'Source URI of the email content',
		'start_date'        : 'Date that the email will first be sent.',
		'send_time'         : 'Format: %H:%M or %H:%M:%S. Time of day when the email will be sent. Times will be rounded to the nearest quarter hour.',
		'recurrence'        : 'If and how often the email will be resent.',
		'replace_delimiter' : 'Character(s) that replacement labels are wrapped in.',
		'recipient_groups'  : 'Which group(s) of recipients this email will go to.',
		'confirm_send'      : 'Send a go/no-go email to the administrators before the email is sent.'
	}

	title             = models.CharField(max_length=100, help_text=_HELP_TEXT['title'])
	html              = models.TextField(blank=True, null=True, help_text=_HELP_TEXT['html'])
	source_uri        = models.URLField(blank=True, null=True, help_text=_HELP_TEXT['source_uri'])
	start_date        = models.DateField(help_text=_HELP_TEXT['start_date'])
	send_time         = models.TimeField(help_text=_HELP_TEXT['send_time'])
	recurrence        = models.SmallIntegerField(null=True, blank=True, default=Recurs.never, choices=Recurs.choices, help_text=_HELP_TEXT['recurrence'])
	replace_delimiter = models.CharField(max_length=10, default='!@!', help_text=_HELP_TEXT['replace_delimiter'])
	recipient_groups  = models.ManyToManyField(RecipientGroup, help_text=_HELP_TEXT['recipient_groups'])
	confirm_send      = models.BooleanField(default=True, help_text=_HELP_TEXT['confirm_send'])

	@property
	def total_sent(self):
		return sum(list(i.sent for i in self.instances.all()))

	@property
	def content(self):
		if self.html != '':
			return self.html
		else:
			import urllib
			page = urllib.urlopen(self.source_uri)
			return page.read()

class EmailLabelRecipientFieldMapping(models.Model):
	'''
		Describes the mapping between attributes on a recipient
		objects to a label in an email for replacement.
	'''
	email           = models.ForeignKey(Email)
	recipient_field = models.CharField(max_length=100, blank=True, null=True)
	email_label     = models.CharField(max_length=100)

class Instance(models.Model):
	'''
		Describes a sending of an email based on its schedule
	'''
	email       = models.ForeignKey(Email, related_name='instances')
	sent_html   = models.TextField()
	start       = models.DateTimeField(auto_now_add=True)
	end         = models.DateTimeField()
	in_progress = models.BooleanField(default=False)
	sent        = models.IntegerField(default=0)