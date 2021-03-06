# -*- coding: utf-8 -*-
# Generated by Django 1.11.12 on 2018-07-19 09:09


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0003_auto_20180718_1444'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscriptioncategory',
            name='applies_to',
            field=models.CharField(blank=True, help_text=b'The pattern used to determine if users can unsubscribe from emails of this category.', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='subscriptioncategory',
            name='can_unsubscribe',
            field=models.BooleanField(default=True, help_text=b'When unchecked, users following the Applies To pattern will not be able to unsubscribe from emails.'),
        ),
    ]
