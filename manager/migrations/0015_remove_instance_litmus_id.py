# -*- coding: utf-8 -*-
# Generated by Django 1.11.12 on 2019-03-27 11:00
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0014_subprocessstatus_back_url'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='instance',
            name='litmus_id',
        ),
    ]