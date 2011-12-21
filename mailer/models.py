from django.db import models
from django.conf import settings
import hmac
import calendar
import datetime
import urllib

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
	email_address = models.CharField(max_length=256)

	@property
	def hmac_hash(self):
		return hmac.new(settings.SECRET_KEY, self.email_address).hexdigest()

	@property
	def smtp_address(self):
		return '"%s %s" <%s>' % (self.first_name, self.last_name, self.email_address)

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
		'confirm_send'      : 'Send a go/no-go email to the administrators before the email is sent.',
		'from_email_address': 'Email address from where the sent emails will originate',
		'from_friendly_name': 'A display name associated with the from email address',
		'track_urls'        : 'Rewrites all URLs in the email content to be recorded',
		'track_opens'       : 'Adds a tracking image to email content to track if and when an email is opened.'
	}

	title              = models.CharField(max_length=100, help_text=_HELP_TEXT['title'])
	html               = models.TextField(blank=True, null=True, help_text=_HELP_TEXT['html'])
	source_uri         = models.URLField(blank=True, null=True, help_text=_HELP_TEXT['source_uri'])
	start_date         = models.DateField(help_text=_HELP_TEXT['start_date'])
	send_time          = models.TimeField(help_text=_HELP_TEXT['send_time'])
	recurrence         = models.SmallIntegerField(null=True, blank=True, default=Recurs.never, choices=Recurs.choices, help_text=_HELP_TEXT['recurrence'])
	from_email_address = models.CharField(max_length=256, help_text=_HELP_TEXT['from_email_address'])
	from_friendly_name = models.CharField(max_length=100, blank=True, null=True, help_text=_HELP_TEXT['from_friendly_name'])
	replace_delimiter  = models.CharField(max_length=10, default='!@!', help_text=_HELP_TEXT['replace_delimiter'])
	recipient_groups   = models.ManyToManyField(RecipientGroup, help_text=_HELP_TEXT['recipient_groups'])
	confirm_send       = models.BooleanField(default=True, help_text=_HELP_TEXT['confirm_send'])
	track_urls         = models.BooleanField(default=False, help_text=_HELP_TEXT['track_urls'])
	track_opens        = models.BooleanField(default=False, help_text=_HELP_TEXT['track_opens'])

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
	
	def graph(self, duration=15, width=630, height=125):
		'''
			Creates a graph using the Google Charts Image API.

			http://code.google.com/apis/chart/image/docs/gallery/line_charts.html
		'''
		base_url = 'https://chart.googleapis.com/chart'
		params = {
			'cht' :'lc',      # chart type - lc=line chart
			'chco': '',       # line colors
			'chs' : '',       # chart dimensions - width by height in pixels
			'chd' : '',       # chart data
			'chxt': 'x,y',    # visible axes
			'chxl': '',       # custom axis label
			'chdl': '',       # legend names
			#'chtt': '',       # graph title
			'chxr': '',       # axis range
			'chm' : '',       # value markers
		}

		# Dimensions
		params['chs'] = 'x'.join([str(width), str(height)])

		# Define the lines we are going to have
		lines = {
			'Sent'           : '0000FF',
			'Sending Errors' : 'FF0000',
		}
		if self.track_urls:
			lines['URLs Clicked'] = '00FF00'
		if self.track_opens:
			lines['Opened'] = '0000FF'
		
		# line colors
		params['chco'] = ','.join(list(val for key,val in lines.items()))

		# Compile data and labels
		data_sets = {
			'sent'  :[],
			'errors':[]
		}
		labels = []
		now = datetime.datetime.now()
		for i in range(duration):
			start = datetime.datetime(now.year, now.month, now.day, 0, 0, 0) - datetime.timedelta(days=i)
			end   = datetime.datetime(now.year, now.month, now.day, 23, 59, 59) - datetime.timedelta(days=i)

			# Sent
			total = 0
			for instance in self.instances.filter(start__gte=start, start__lt=end):
				total += instance.recipient_details.count()
			data_sets['sent'].append(total)
			
			# Sending Errors
			total = 0
			for instance in self.instances.filter(start__gte=start, start__lt=end):
				total += instance.recipient_details.exclude(exception_type=None).count()
			data_sets['errors'].append(total)

			labels.append('/'.join([str(start.month), str(start.day)]))

		graph_max = 0
		g_data_sets = []
		for name, data in data_sets.items():
			set_max = max(data)
			if set_max > graph_max:
				graph_max = set_max
			data.reverse()
			g_data_sets.append(','.join(list(str(v) for v in data)))

		params['chd']  = 't:' + '|'.join(g_data_sets)

		# Axis Ranges
		graph_max += 10
		params['chxr'] = ','.join(['1', '0', str(graph_max)])
		params['chds'] = ','.join(['0', str(graph_max)])
		
		# Labels
		labels.reverse()
		params['chxl'] = '0:|' + '|'.join(labels)

		# Legend
		params['chdl'] = '|'.join(list(key for key,val in lines.items()))

		# Value Markers
		params['chm'] = 'N*f0,666666,1,-1,11,,lb:-10:5'
		
		return '?'.join([base_url,urllib.urlencode(params)])

class EmailLabelRecipientFieldMapping(models.Model):
	'''
		Describes the mapping between attributes on a recipient
		objects to a label in an email for replacement.
	'''
	email           = models.ForeignKey(Email, related_name='mappings')
	recipient_field = models.CharField(max_length=100, blank=True, null=True)
	email_label     = models.CharField(max_length=100)

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