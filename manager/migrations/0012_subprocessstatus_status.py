# -*- coding: utf-8 -*-
# Generated by Django 1.11.12 on 2018-09-17 11:12
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0011_subprocessstatus'),
    ]

    operations = [
        migrations.AddField(
            model_name='subprocessstatus',
            name='status',
            field=models.CharField(default=b'In Progress', max_length=12),
        ),
    ]