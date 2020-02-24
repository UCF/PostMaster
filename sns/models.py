# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

# Create your models here.
class Feedback(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    sns_topic = models.CharField(max_length=350)
    sns_message_id = models.CharField(max_length=100)
    mail_timestamp = models.DateTimeField()
    mail_id = models.CharField(max_length=100)
    mail_from = models.EmailField()
    address = models.EmailField()
    feedback_id = models.CharField(max_length=100, null=True, blank=True)
    feedback_timestamp = models.DateTimeField(verbose_name="Feedback Time", null=True, blank=True)

    class Meta(object):
        abstract = True

class Bounce(Feedback):
    hard = models.BooleanField(db_index=True, verbose_name="Hard Bounce")
    bounce_type = models.CharField(db_index=True, max_length=50, verbose_name="Bounce Type")
    bounce_subtype = models.CharField(db_index=True, max_length=50, verbose_name="Bounce SubType")
    reporting_mta = models.TextField(blank=True, null=True)
    action = models.CharField(max_length=150, db_index=True, null=True, blank=True, verbose_name="Action")
    status = models.CharField(max_length=150, db_index=True, null=True, blank=True)
    diagnostic_code = models.TextField(null=True, blank=True, max_length=1000)

    def __unicode__(self):
        return "%s %s Bounce (message from %s" % (
            self.address, self.bounce_type, self.mail_from
        )

    def __str__(self):
        return "%s %s Bounce (message from %s" % (
            self.address, self.bounce_type, self.mail_from
        )

class Complaint(Feedback):
    user_agent = models.TextField(blank=True, null=True)
    feedback_type = models.CharField(max_length=150, db_index=True, null=True, blank=True, verbose_name="Complaint Type")
    arrival_date = models.DateTimeField(blank=True, null=True)

    def __unicode__(self):
        return "%s Complaint (email sender: from %s)" % (
            self.address, self.mail_from
        )

    def __str__(self):
        return "%s Complaint (email sender: from %s)" % (
            self.address, self.mail_from
        )
