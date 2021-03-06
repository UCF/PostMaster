# -*- coding: utf-8 -*-
# Generated by Django 1.11.12 on 2018-07-19 09:59


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0005_auto_20180719_0959'),
    ]

    operations = [
        migrations.AlterField(
            model_name='subscriptioncategory',
            name='cannot_unsubscribe',
            field=models.BooleanField(default=False, help_text=b'When checked, users following the Applies To pattern will not be able to unsubscribe from emails.'),
        ),
    ]
