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

class Schedule(models.Model):
	'''
		Describes the schedule of an email
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

	start      = models.DateTimeField()
	recurrence = models.SmallIntegerField(null=True, blank=True, default=Recurs.never, choices=Recurs.choices)


class Email(models.Model):
	'''
		Describes the details of an email 
	'''
	title             = models.CharField(max_length=100)
	html              = models.TextField(blank=True, null=True)
	source            = models.URLField(blank=True, null=True)	
	replace_delimiter = models.CharField(max_length=10, default='!@!')
	schedule          = models.ForeignKey(Schedule)
	recipient_groups  = models.ManyToManyField(RecipientGroup)

class Instance(models.Model):
	'''
		Describes a sending of an email based on its schedule
	'''
	email = models.ForeignKey(Email)