# -*- coding: utf-8 -*-
# Generated by Django 1.11.12 on 2018-07-26 12:31
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0007_auto_20180726_1048'),
    ]

    operations = [
        migrations.AddField(
            model_name='recipientgroup',
            name='preview',
            field=models.BooleanField(default=False),
        ),
    ]
