from django.db import models

class Recipient(models.Model):
	'''
		Describes the details of a possible email recipient
	'''
	first_name    = models.CharField(max_length=100)
	last_name     = models.CharField(max_length=100)
	email_address = models.CharField(max_length=100)

class RecipientGroup(models.Model):
	'''
		Describes the details of a named group of email recipients
	'''
	name       = models.CharField(max_length=100)
	recipients = models.ManyToManyField(Recipient)

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
		'start'             : 'Date and time that the email will be sent.',
		'recurrence'        : 'If and how often the email will be resent.',
		'replace_delimiter' : 'Character(s) that replacement labels are wrapped in.',
		'recipient_groups'  : 'Which group(s) of recipients this email will go to.',
		'confirm_send'      : 'Send a go/no-go email to the administrators before the email is sent.'
	}

	title             = models.CharField(max_length=100, help_text=_HELP_TEXT['title'])
	html              = models.TextField(blank=True, null=True, help_text=_HELP_TEXT['html'])
	source_uri        = models.URLField(blank=True, null=True, help_text=_HELP_TEXT['source_uri'])
	start             = models.DateTimeField(help_text=_HELP_TEXT['start'])
	recurrence        = models.SmallIntegerField(null=True, blank=True, default=Recurs.never, choices=Recurs.choices, help_text=_HELP_TEXT['recurrence'])
	replace_delimiter = models.CharField(max_length=10, default='!@!', help_text=_HELP_TEXT['replace_delimiter'])
	recipient_groups  = models.ManyToManyField(RecipientGroup, help_text=_HELP_TEXT['recipient_groups'])
	confirm_send      = models.BooleanField(default=True, help_text=_HELP_TEXT['confirm_send'])

class Instance(models.Model):
	'''
		Describes a sending of an email based on its schedule
	'''
	email = models.ForeignKey(Email)