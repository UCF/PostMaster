# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from django.http import HttpResponseBadRequest, HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from django.shortcuts import render
from django.views.generic import View

from sns import signals
from sns.models import Bounce
from sns.utils import clean_time

import json
import re

try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Create your views here.
class Endpoint(View):
    VITAL_NOTIFICATION_FIELDS = [
        'notificationType'
    ]

    ALLOWED_TYPES = [
        'Bounce', 'Complaint'
    ]

    @csrf_exempt
    def post(self, request):
        # Make sure this is a valid topic ARN from SNS
        if hasattr(settings, 'SNS_TOPIC_ARN'):
            if 'HTTP_X_AMZ_SNS_TOPIC_ARN' not in request.META:
                return HttpResponseBadRequest('No TopicArn Header')

            if not request.META['HTTP_X_AMZ_SNS_TOPIC_ARN'] in settings.SNS_TOPIC_ARN:
                return HttpResponseBadRequest('Bad Topic')

        # Get the request body and validate as JSON
        if isinstance(request.body, str):
            request_body = request.body
        else:
            request_body = request.body.decode()

        try:
            data = json.loads(request_body)
        except ValueError:
            logger.warning('Notification Not Valid JSON: {}'.format(request_body))
            return HttpResponseBadRequest('Not Valid JSON')

        # Make sure we have all the fields we need to verify
        if not set(self.VITAL_NOTIFICATION_FIELDS) <= set(data):
            logger.warning('Request Missing Necessary Keys')
            return HttpResponseBadRequest('Request Missing Necessary Keys')

        # Make sure this is a notification type we can handle
        if not data['notificationType'] in self.ALLOWED_TYPES:
            logger.info('Notification Type Not Known: %s', data['notificationType'])
            return HttpResponseBadRequest('Unknown Notification Type')

        signals.notification.send(
            sender='sns_endpoint', notification=data, request=request
        )

        if data['notificationType'] == 'Bounce':
            return self.process_bounce(data, request)
        elif data['notificationType'] == 'Complaint':
            return self.process_complaint(data, request)

        # We should be able to get down here, but it's always
        # good to return something
        return HttpResponseBadRequest('Unknown Notification Type')

    def process_bounce(self, data, request):
        mail = data['mail']
        bounce = data['bounce']

        bounces = []
        for recipient in bounce['bouncedRecipients']:
            bounces += [Bounce.objects.create(
                sns_topic=mail['sourceArn'],
                sns_message_id=mail['messageId'],
                mail_timestamp=clean_time(mail['timestamp']),
                mail_id=mail['messageId'],
                mail_from=mail['source'],
                address=recipient['emailAddress'],
                feedback_id=bounce['feedbackId'],
                feedback_timestamp=clean_time(bounce['timestamp']),
                hard=bool(bounce['bounceType'] == 'Permanent'),
                bounce_type=bounce['bounceType'],
                bounce_subtype=bounce['bounceSubType'],
                reporting_mta=bounce.get('reportingMTA'),
                action=recipient.get('action'),
                status=recipient.get('status'),
                diagnostic_code=recipient.get('diagnosticCode')
            )]

        for bounce in bounces:
            signals.feedback.send(
                sender=Bounce,
                instance=bounce,
                message=data
            )

        return HttpResponse('Bounce Processed')

    def process_complaint(self, data, request):
        print data

        return HttpResponse('Complaint Processed')
