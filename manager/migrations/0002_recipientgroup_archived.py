# -*- coding: utf-8 -*-
# Generated by Django 1.11.12 on 2018-07-17 13:19
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='recipientgroup',
            name='archived',
            field=models.BooleanField(default=False),
        ),
    ]
