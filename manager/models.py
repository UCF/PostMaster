from django.db import models
from django.conf import settings
from datetime import datetime, timedelta, date
from django.db.models import Q
from util import calc_url_mac, calc_open_mac, calc_unsubscribe_mac
from django.core.urlresolvers import reverse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from django.http import HttpResponseRedirect
from django.core.exceptions import SuspiciousOperation
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe
from itertools import chain
import logging
import smtplib
import re
import urllib
import time
import Queue
import threading
import requests
import random

from bs4 import BeautifulSoup

log = logging.getLogger(__name__)


class Recipient(models.Model):
    '''
        Describes the details of a recipient
    '''

    email_address = models.CharField(max_length=255, unique=True)
    disable = models.BooleanField(default=False)

    class Meta:
            ordering = ["email_address"]

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
        return calc_unsubscribe_mac(self.pk)

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
        # Use prefix='/' for reverse here instead of relying on get_script_prefix inside of
        # reverse. This is because this method is called by management commands which
        # have no concept of get_script_prefix().
        return '?'.join([
            settings.PROJECT_URL + reverse('manager-recipient-subscriptions', kwargs={'pk':self.pk}),
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
    name = models.CharField(max_length=100)
    value = models.CharField(max_length=1000,blank=True)

    class Meta:
        unique_together  = (('recipient', 'name'))


class RecipientGroup(models.Model):
    '''
        Describes a named group of recipients. Email objects are not associated with
        Recipient objects directly. They are associated to each other via RecipientGroup.
    '''
    name = models.CharField(max_length=100, unique=True)
    recipients = models.ManyToManyField(Recipient, related_name='groups')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived = models.BooleanField(default=False)
    preview = models.BooleanField(
        default=False,
        verbose_name='Is a Preview Group',
        help_text='Specify whether this group should be used for organizing recipients of preview emails. Leave unchecked if this group contains/will contain recipients for live emails.',
    )

    class Meta:
            ordering = ["name"]

    def __str__(self):
        return self.name + ' (' + str(self.recipients.exclude(disable=True).count()) + ' active recipients)'


class SubscriptionCategory(models.Model):
    """
        Describes a category of email for subscription purposes.
    """

    _HELP_TEXT = {
        "name": "The name of the subscription category. Will be viewable by front-end users.",
        "description": "The description of the subscription category. Should include the types of emails sent in this category, as well as frequency.",
        "unsubscriptions": "A list of recipients unsubscribed from this category.",
        "cannot_unsubscribe": "When checked, users following the Applies To pattern will not be able to unsubscribe from emails.",
        "applies_to": "The pattern used to determine if users can unsubscribe from emails of this category. For example \"(knights)?\.?ucf\.edu$\" would apply to \"email@knights.ucf.edu\" and \"email@ucf.edu\"."
    }

    name = models.CharField(max_length=100, unique=True, null=False, blank=False, help_text=_HELP_TEXT['name'])
    description = models.TextField(null=False, blank=False, help_text=_HELP_TEXT['description'])
    unsubscriptions = models.ManyToManyField(Recipient, help_text=_HELP_TEXT['unsubscriptions'], related_name="subscription_category")
    cannot_unsubscribe = models.BooleanField(null=False, blank=False, default=False, help_text=_HELP_TEXT['cannot_unsubscribe'])
    applies_to = models.CharField(max_length=255, null=True, blank=True, help_text=_HELP_TEXT['applies_to'])

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name

    def applies_to_email(self, email_address):
        if re.search(self.applies_to, email_address):
            return True

        return False


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
                Q(Q(recurrence=self.model.Recurs.daily) & Q(start_date__lte=today)) |
                # Weekly
                Q(Q(recurrence=self.model.Recurs.weekly) & Q(start_date__week_day=today.isoweekday() % 7 + 1)) |
                # Monthly
                Q(Q(recurrence=self.model.Recurs.monthly) & Q(start_date__day=today.day))
            ),
            active=True
        )

    def sending_today_no_pre_est(self, now=datetime.now()):
        """Returns all the emails that are sending today with no preview estimate

        :param now: The datetime to check if the email is being sent.
        :return: Array of email objects
        """
        return self.sending_today(now).filter(
            preview=True,
            preview_est_time=None
        )

    def sending_today_no_live_est(self, now=datetime.now()):
        """Returns all the emails that are sending today with no live estimate

        :param now: The datetime to check if the email is being sent.
        :return: Array of email objects
        """
        return self.sending_today(now).filter(live_est_time=None)

    def not_sending_today(self, today=date.today()):
        """Returns all the emails that aren't sending today

        :param today: The date to check if the email is being sent.
        :return: Array of email objects
        """
        return Email.objects.filter(
            Q(
                # One-time
                ~Q(Q(recurrence=self.model.Recurs.never) & Q(start_date=today)) &
                # Daily
                ~Q(Q(recurrence=self.model.Recurs.daily) & Q(start_date__lte=today)) &
                # Weekly
                ~Q(Q(recurrence=self.model.Recurs.weekly) & Q(start_date__week_day=today.isoweekday() % 7 + 1)) &
                # Monthly
                ~Q(Q(recurrence=self.model.Recurs.monthly) & Q(start_date__day=today.day))
            )
        )

    def sending_today_old_est(self, now=datetime.now()):
        """Returns all the emails that are sending today but have old estimates

        :param now: The datetime to check if the email is being sent
        :return: Array of email objects
        """
        return self.sending_today(now).filter(
            Q(
                Q(
                    ~Q(preview_est_time=None) &
                    ~Q(
                        Q(preview_est_time__day=now.day) &
                        Q(preview_est_time__month=now.month) &
                        Q(preview_est_time__year=now.year)
                    )
                ) |
                Q(
                    ~Q(live_est_time=None) &
                    ~Q(
                        Q(live_est_time__day=now.day) &
                        Q(live_est_time__month=now.month) &
                        Q(live_est_time__year=now.year)
                    )
                )
            )
        )

    def sending_now(self, now=None):
        if now is None:
            now = datetime.now()
        send_interval_start = now.time()
        send_interval_end = (now + self.processing_interval_duration).time()

        # Exclude emails outside this sending interval
        # Exclude emails with instances that have the same requested_start or
        # or are in progress (end=None)
        email_pks = []
        for candidate in Email.objects.sending_today(now=now):
            requested_start = datetime.combine(now.date(), candidate.send_time)
            # check if preview has been sent (or no preview requested) and if a send override is set
            if ((send_interval_start <= candidate.send_time <= send_interval_end) or
                    (candidate.send_time <= send_interval_end and candidate.send_override)) and \
                    (not candidate.preview or candidate.previews.filter(requested_start=requested_start).count()):

                # Email is queued to be sent so no need override the send functionality anymore
                candidate.send_override = False
                candidate.save()
                if candidate.instances.filter(requested_start=requested_start).count() == 0:
                    email_pks.append(candidate.pk)
        return Email.objects.filter(pk__in=email_pks)

    def previewing_now(self, now=None):
        if now is None:
            now = datetime.now()
        preview_lead_time = timedelta(seconds=settings.PREVIEW_LEAD_TIME)
        preview_interval_start = (now + preview_lead_time).time()
        preview_interval_end = (now + preview_lead_time + self.processing_interval_duration).time()

        # Exclude emails outside this previewing interval
        # Exclude emails with instances that have the same requested_start or
        # or are in progress (end=None)
        email_pks = []
        for candidate in Email.objects.sending_today(now=now).filter(preview=True):
            if (preview_interval_start <= candidate.send_time <= preview_interval_end) or \
                    (candidate.send_time <= preview_interval_end and candidate.send_override):
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
        never, daily, weekly, biweekly, monthly = range(0, 5)
        choices = (
            (never, 'Never'),
            (daily, 'Daily'),
            (weekly, 'Weekly'),
            (biweekly, 'Biweekly'),
            (monthly, 'Monthly'),
        )

    _HELP_TEXT = {
        'active': 'Whether the email is active or not. Inactive emails will not be sent',
        'title': 'Internal identifier of the email',
        'subject': 'Subject of the email',
        'source_html_uri': 'Source URI of the email HTML. <a href="#" class="upload-modal-trigger btn btn-sm btn-link text-transform-none letter-spacing-0" data-id="id_source_html_uri" data-accept="text/html" data-toggle="modal" data-target="#upload-email-modal">Upload Email</a> <a href="" target="_blank" data-id="id_source_html_uri" class="btn btn-sm btn-link text-transform-none letter-spacing-0 view-email-trigger d-none">View Email HTML</a>',
        'source_text_uri': 'Source URI of the email text. <a href="#" class="upload-modal-trigger btn btn-sm btn-link text-transform-none letter-spacing-0" data-id="id_source_text_uri" data-accept="text/plain" data-toggle="modal" data-target="#upload-email-modal">Upload Email</a> <a href="" target="_blank" data-id="id_source_text_uri" class="btn btn-sm btn-link text-transform-none letter-spacing-0 view-email-trigger d-none">View Email Text</a>',
        'start_date': 'Date that the email will first be sent.',
        'send_time': 'Time of day when the email will be sent. Times will be rounded to the nearest quarter hour.',
        'recurrence': 'If and how often the email will be resent.',
        'replace_delimiter': 'Character(s) that replacement labels are wrapped in.',
        'recipient_groups': 'Which group(s) of recipients this email will go to.',
        'from_email_address': 'Email address from where the sent emails will originate',
        'from_friendly_name': 'A display name associated with the from email address',
        'track_urls': 'Rewrites all URLs in the email content to be recorded',
        'track_opens': 'Adds a tracking image to email content to track if and when an email is opened.',
        'preview': 'BE CAREFUL! Un-checking this value will disable sending the preview email. In some cases, if un-checked, this will cause a live email to be sent on the next send cycle.\nSend a preview to a specific set of individuals allowing them to proof the content.',
        'preview_recipients': 'A comma-separated list of preview recipient email addresses'
    }

    active = models.BooleanField(default=False, help_text=_HELP_TEXT['active'])
    creator = models.ForeignKey(User, related_name='created_email', null=True)
    title = models.CharField(blank=False, max_length=100, help_text=_HELP_TEXT['title'])
    subject = models.CharField(max_length=998, help_text=_HELP_TEXT['subject'])
    source_html_uri = models.URLField(help_text=mark_safe(_HELP_TEXT['source_html_uri']))
    source_text_uri = models.URLField(null=True, blank=True, help_text=mark_safe(_HELP_TEXT['source_text_uri']))
    start_date = models.DateField(help_text=_HELP_TEXT['start_date'])
    send_time = models.TimeField(help_text=_HELP_TEXT['send_time'])
    recurrence = models.SmallIntegerField(null=True, blank=True, default=Recurs.never, choices=Recurs.choices, help_text=_HELP_TEXT['recurrence'])
    from_email_address = models.CharField(max_length=256, help_text=_HELP_TEXT['from_email_address'])
    from_friendly_name = models.CharField(max_length=100, blank=True, null=True, help_text=_HELP_TEXT['from_friendly_name'])
    replace_delimiter = models.CharField(max_length=10, default='!@!', help_text=_HELP_TEXT['replace_delimiter'])
    recipient_groups = models.ManyToManyField(RecipientGroup, related_name='emails', help_text=_HELP_TEXT['recipient_groups'])
    track_urls = models.BooleanField(default=True, help_text=_HELP_TEXT['track_urls'])
    track_opens = models.BooleanField(default=True, help_text=_HELP_TEXT['track_opens'])
    preview = models.BooleanField(default=True, help_text=_HELP_TEXT['preview'])
    preview_recipients = models.TextField(null=True, blank=True, help_text=_HELP_TEXT['preview_recipients'])
    preview_est_time = models.DateTimeField(null=True)
    live_est_time = models.DateTimeField(null=True)
    send_override = models.BooleanField(null=False, blank=False, default=True)
    unsubscriptions = models.ManyToManyField(Recipient, related_name='unsubscriptions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    subscription_category = models.ForeignKey(SubscriptionCategory, related_name='emails', null=True)

    class Meta:
            ordering = ["title"]

    def is_sending_today(self, now=datetime.now()):
        """
        Determines if the email is meant to be sent today

        :param now: The date to check against the email send date
        :return: True if sending on specified date, otherwise False
        """
        if self.recurrence == self.Recurs.never and self.start_date == now.date():
            return True
        if self.recurrence == self.Recurs.daily and self.start_date <= now.date():
            return True
        if self.recurrence == self.Recurs.weekly and self.start_date.weekday() == now.date().weekday():
            return True
        if self.recurrence == self.Recurs.monthly and self.start_date.day == now.day:
            return True

        return False

    @property
    def preview_exists(self):
        """
        Determines if a preview email exists based on the requested time (today + send time)
        :return: True if preview exists, otherwise false
        """
        if self.todays_preview:
            return True
        return False

    @property
    def todays_preview(self):
        """
        Determines the wether an email instance exists for today with the
        proper send time.
        :return: Preview instance otherwise None
        """
        requested_start = datetime.combine(date.today(), self.send_time)
        preview_set = self.previews.filter(requested_start=requested_start)
        if preview_set.exists():
            return preview_set[0]
        return None

    @property
    def instance_exists(self):
        """
        Determines if a instance email exists based on the requested time (today + send time)
        :return: True if instance exists, otherwise false
        """
        requested_start = datetime.combine(date.today(), self.send_time)
        instance_set = self.instances.filter(requested_start=requested_start)
        if instance_set.exists():
            return True
        return False

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
                # Warm the cache
                requests.get(self.source_html_uri, verify=False)

                # Get the email html
                # This must be encoded in ASCII format due to Amazon SES limitations:
                #http://docs.aws.amazon.com/ses/latest/DeveloperGuide/send-email-raw.html#send-email-mime-encoding
                request = requests.get(self.source_html_uri, verify=False)
                return (request.status_code, request.text.encode('ascii', 'xmlcharrefreplace'))
            except IOError, e:
                log.exception('Unable to fetch email html')
                raise self.EmailException()

    @property
    def placeholders(self):
        delimiter    = self.replace_delimiter
        placeholders = re.findall(re.escape(delimiter) + '(.+)' + re.escape(delimiter), self.html[1])
        return filter(lambda p: p.lower() != 'unsubscribe', placeholders)

    @property
    def recipients(self):
        retval = None
        for recipient_group in self.recipient_groups.all():
            if retval is None:
                retval = recipient_group.recipients.all()
            else:
                retval = retval | recipient_group.recipients.all()

        return retval.distinct()


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
                # Warm the cache
                urllib.urlopen(self.source_text_uri)

                # Get the email text
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
        status_code, html = self.html
        if status_code != requests.codes.ok:
            log.info('Preview HTML request returned status code ' + str(status_code))

            # Prepend a message to the content explaining that this is a preview
            html_explanation = '''
                <div style="background-color:#000;color:#FFF;font-size:18px;padding:20px; color: #FF0000">
                    HTML request returned status code ''' + str(status_code) + '''. Live email will NOT be sent if the error continues.
                </div>
                <div style="background-color:#000;color:#FFF;font-size:18px;padding:20px;">
                    This is a preview of an email that will go out at approximately ''' + self.live_est_time.strftime('%I:%M %p') + '''
                    <br /><br />
                    The content of this email may be changed before the final email is sent. Any changes that are made to the content below will be included on the live email.
                </div>
            '''
            text_explanation = 'HTML request returned status code ' + str(status_code) + '. Live email will NOT be sent if the error continues.\n\nThis is a preview of an email that will go out at approximately ' + self.live_est_time.strftime('%I:%M %p') + '.\n\nThe content of this email may be changed before the final email is sent. Any changes that are made to the content below will be included on the live email'
        else:
            # Prepend a message to the content explaining that this is a preview
            html_explanation = '''
                <div style="background-color:#000;color:#FFF;font-size:18px;padding:20px;">
                    This is a preview of an email that will go out at approximately ''' + self.live_est_time.strftime('%I:%M %p') + '''
                    <br /><br />
                    The content of this email may be changed before the final email is sent. Any changes that are made to the content below will be included on the live email.
                </div>
            '''
            text_explanation = 'This is a preview of an email that will go out at approximately ' + self.live_est_time.strftime('%I:%M %p') + '.\n\nThe content of this email may be changed before the final email is sent. Any changes that are made to the content below will be included on the live email'

        try:
            text = self.text
        except self.TextContentMissingException:
            text = None

        soup = BeautifulSoup(html, 'html.parser')
        explanation = BeautifulSoup(html_explanation, 'html.parser')
        soup.body.insert(0, explanation)
        html = str(soup.encode('us-ascii'))

        # The recipients for the preview emails aren't the same as regular
        # recipients. They are defined in the comma-separate field preview_recipients
        recipients = [r.strip() for r in self.preview_recipients.split(',')]

        # Add email creator email to recipient list
        if self.creator.email and self.preview is True:
            if self.creator.email not in recipients:
                recipients.append(self.creator.email)
        else:
            log.debug('email_address not set for creator')

        try:
            amazon = smtplib.SMTP_SSL(settings.AMAZON_SMTP['host'],
                                      settings.AMAZON_SMTP['port'])
            amazon.login(settings.AMAZON_SMTP['username'],
                         settings.AMAZON_SMTP['password'])
        except smtplib.SMTPException, e:
            log.exception('Unable to connect to Amazon')
            raise self.AmazonConnectionException()
        else:
            preview_instance = PreviewInstance.objects.create(
                email=self,
                sent_html=html,
                recipients=self.preview_recipients,
                requested_start=datetime.combine(datetime.now().today(),
                                                 self.send_time)
            )

            for recipient in recipients:
                # Use alterantive subclass here so that both HTML and plain
                # versions can be attached
                msg = MIMEMultipart('alternative')
                msg['subject'] = self.subject + ' **PREVIEW**'
                msg['From'] = self.smtp_from_address
                msg['To'] = recipient

                msg.attach(MIMEText(html,
                                    'html',
                                    _charset='us-ascii'))

                if text is not None:
                    msg.attach(MIMEText(text_explanation + text,
                                        'plain',
                                        _charset='us-ascii'))

                try:
                    amazon.sendmail(self.from_email_address,
                                    recipient,
                                    msg.as_string())
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
        class TerminationThread(threading.Thread):
            def run(self):
                from manager.utils import flush_transaction
                while True:
                    # Flushes sql transaction so we get fresh data
                    flush_transaction()
                    the_instance = Instance.objects.get(pk=instance.pk)
                    if the_instance.send_terminate:
                        sender_stop.set()
                        instance.send_terminate = True
                        instance.save()
                        break
                    elif recipient_details_queue.empty():
                        break
                    else:
                        time.sleep(1)

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

                    if sender_stop.is_set():
                        log.debug('%s receieved termination signal.' % self.name)
                        while not recipient_details_queue.empty():
                            recipient_details_queue.get()
                            recipient_details_queue.task_done()
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
                                tracking_url = '?'.join([
                                    settings.PROJECT_URL + reverse('manager-email-redirect'),
                                    urllib.urlencode({
                                        'instance'  :recipient_details.instance.pk,
                                        'recipient' :recipient_details.recipient.pk,
                                        'url'       :urllib.quote(url.name),
                                        'position'  :url.position,
                                        # The mac uniquely identifies the recipient and acts as a secure integrity check
                                        'mac'       :calc_url_mac(url.name, url.position, recipient_details.recipient.pk, recipient_details.instance.pk)
                                    })
                                ])

                                customized_html = customized_html.replace(
                                    'href="' + url.name + '"',
                                    'href="' + tracking_url + '"',
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


        # Check to see if there is a content lock on the preview email
        # otherwise grab the new content
        preview_email = self.todays_preview
        if preview_email is not None and \
           preview_email.lock_content and \
           preview_email.sent_html:
            html = preview_email.sent_html
            text = None
        else:
            try:
                text = self.text
            except self.TextContentMissingException:
                text = None

            status_code, html = self.html
            if status_code != requests.codes.ok:
                log.exception('Not sending Live email. HTML request returned status code ' + str(status_code))
                raise self.EmailException()

        instance = Instance.objects.create(
            email           = self,
            subject         = self.subject,
            sent_html       = html,
            requested_start = datetime.combine(datetime.now().today(), self.send_time),
            opens_tracked   = self.track_opens,
            urls_tracked    = self.track_urls
        )

        recipients = Recipient.objects.filter(
            groups__in = self.recipient_groups.all(),
            disable=False
            ).distinct()

        if self.subscription_category:
            unsubscriptions = self.subscription_category.unsubscriptions.all()
        else:
            unsubscriptions = self.unsubscriptions.all()

        if unsubscriptions:
            recipients = recipients.exclude(id__in=[o.id for o in unsubscriptions])

        # Add email creator email to recipient list
        if self.creator.email:
            # Get recipient from creator email
            try:
                recipient, created = Recipient.objects.get_or_create(email_address=self.creator.email)
                recipient = Recipient.objects.filter(pk=recipient.id)
                recipients = list(chain(recipients, recipient))
            except Recipient.MultipleObjectsReturned:
                log.error('Multiple emails found for creator email ' + self.creator.email)
        else:
            log.debug('email_address not set for creator')

        # The interval between ticks is one second. This is used to make
        # sure that the threads don't exceed the sending limit
        subject                 = self.subject + str(additional_subject)
        display_from            = self.smtp_from_address
        real_from               = self.from_email_address
        recipient_details_queue = Queue.Queue()
        sender_stop             = threading.Event()
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
        # Get all recipient attributes
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

        terminate_thread = TerminationThread()
        terminate_thread.daemon = True
        terminate_thread.start()

        for i in xrange(0, settings.AMAZON_SMTP['rate'] - 1):
            sending_thread = SendingThread()
            sending_thread.daemon = True
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
    email = models.ForeignKey(Email, related_name='instances')
    subject = models.TextField(null=True, max_length=998)
    sent_html = models.TextField()
    requested_start = models.DateTimeField()
    start = models.DateTimeField(auto_now_add=True)
    end = models.DateTimeField(null=True)
    success = models.NullBooleanField(default=None)
    recipients = models.ManyToManyField(Recipient,
                                        through='InstanceRecipientDetails')
    opens_tracked = models.BooleanField(default=False)
    urls_tracked = models.BooleanField(default=False)
    send_terminate = models.BooleanField(default=False)

    @property
    def in_progress(self):
        if self.start is not None and self.end is None and self.send_terminate is False:
            return True
        else:
            return False

    @property
    def open_rate(self, significance=2):
        '''
            Open rate of this instance as a percent.
        '''
        opens = self.initial_opens
        return 0 if self.sent_count == 0 else round(float(opens)/float(self.sent_count)*100, significance)

    @property
    def sent_count(self):
        return self.recipient_details.exclude(when=None).count()

    @property
    def initial_opens(self):
        return self.opens.exclude(is_reopen=True).count()

    @property
    def re_opens(self):
        return self.opens.exclude(is_reopen=False).count()

    @property
    def total_opens(self):
        return self.opens.count()

    @property
    def placeholders(self):
        delimiter    = self.email.replace_delimiter
        placeholders = re.findall(re.escape(delimiter) + '(.+)' + re.escape(delimiter), self.sent_html)
        return filter(lambda p: p.lower() != 'unsubscribe', placeholders)

    @property
    def tracking_urls(self):
        if not self.urls_tracked:
            return []

        hrefs = re.findall('<a(?:[ \w\-\=\"]+)?href=\"([^\"]+)\"', self.sent_html)
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
    email = models.ForeignKey(Email, related_name='previews')
    sent_html = models.TextField()
    recipients = models.TextField()
    requested_start = models.DateTimeField()
    when = models.DateTimeField(auto_now_add=True)
    lock_content = models.BooleanField(default=False)

    @property
    def instance(self):
        """
        Returns the accociated instance email based on the requested start
        :return: email instance
        """
        instance_set = self.email.instances. \
            filter(requested_start=self.requested_start). \
            order_by('-start')
        if instance_set.exists():
            return instance_set[0]
        return None

    @property
    def past(self):
        """
        Determines if the requested start has passed.
        :return: Boolean True request time is in the past else False
        """
        if self.requested_start < datetime.now():
            return True
        else:
            return False

    class Meta:
        ordering = ('-when',)


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
    is_reopen = models.BooleanField(default=False)


class Setting(models.Model):
    name = models.CharField(max_length=80)
    value = models.CharField(max_length=200)


class SubprocessStatus(models.Model):
    name = models.CharField(max_length=200)
    unit_name = models.CharField(max_length=200)
    current_unit = models.IntegerField()
    total_units = models.IntegerField()
    status = models.CharField(max_length=12, default='In Progress')
    error = models.CharField(max_length=1000)
    success_url = models.URLField(blank=True, null=True)
    back_url = models.URLField(blank=True, null=True)

# Signals
from manager.signals import *

pre_save.connect(migrate_unsubscriptions, sender=Email)
