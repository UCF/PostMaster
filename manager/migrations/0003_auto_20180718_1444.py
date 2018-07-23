# -*- coding: utf-8 -*-
# Generated by Django 1.11.12 on 2018-07-18 14:44
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion

from django.core.management import call_command

fixture_name = 'manager_initial_data'

def initial_load_data(apps, schema_editor):
    call_command('loaddata', fixture_name, app_label='manager')

class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0002_recipientgroup_archived'),
    ]

    operations = [
        migrations.CreateModel(
            name='SubscriptionCategory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text=b'The name of the subscription category. Will be viewed by users on frontend.', max_length=100, unique=True)),
                ('description', models.TextField(help_text=b'The description of the subscription category. Should include the types of emails sent in this category, as well as frequency.')),
                ('unsubscriptions', models.ManyToManyField(help_text=b'A list of recipients unsubscribed from this category.', related_name='subscription_category', to='manager.Recipient')),
            ],
        ),
        migrations.RunPython(initial_load_data),
        migrations.AddField(
            model_name='email',
            name='subscription_category',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='emails', to='manager.SubscriptionCategory'),
            preserve_default=False,
        )
    ]
