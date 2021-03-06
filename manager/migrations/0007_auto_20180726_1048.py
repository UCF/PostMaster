# -*- coding: utf-8 -*-
# Generated by Django 1.11.12 on 2018-07-26 10:48


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0006_auto_20180719_0959'),
    ]

    operations = [
        migrations.AlterField(
            model_name='email',
            name='send_time',
            field=models.TimeField(help_text=b'Time of day when the email will be sent. Times will be rounded to the nearest quarter hour.'),
        ),
        migrations.AlterField(
            model_name='email',
            name='source_html_uri',
            field=models.URLField(help_text=b'Source URI of the email HTML. <a href="#" class="upload-modal-trigger btn btn-sm btn-link text-transform-none letter-spacing-0" data-id="id_source_html_uri" data-accept="text/html" data-toggle="modal" data-target="#upload-email-modal">Upload Email</a> <a href="" target="_blank" data-id="id_source_html_uri" class="btn btn-sm btn-link text-transform-none letter-spacing-0 view-email-trigger d-none">View Email HTML</a>'),
        ),
        migrations.AlterField(
            model_name='email',
            name='source_text_uri',
            field=models.URLField(blank=True, help_text=b'Source URI of the email text. <a href="#" class="upload-modal-trigger btn btn-sm btn-link text-transform-none letter-spacing-0" data-id="id_source_text_uri" data-accept="text/plain" data-toggle="modal" data-target="#upload-email-modal">Upload Email</a> <a href="" target="_blank" data-id="id_source_text_uri" class="btn btn-sm btn-link text-transform-none letter-spacing-0 view-email-trigger d-none">View Email Text</a>', null=True),
        ),
        migrations.AlterField(
            model_name='email',
            name='start_date',
            field=models.DateField(help_text=b'Date that the email will first be sent.'),
        ),
        migrations.AlterField(
            model_name='subscriptioncategory',
            name='applies_to',
            field=models.CharField(blank=True, help_text=b'The pattern used to determine if users can unsubscribe from emails of this category. For example "(knights)?\\.?ucf\\.edu$" would apply to "email@knights.ucf.edu" and "email@ucf.edu".', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='subscriptioncategory',
            name='name',
            field=models.CharField(help_text=b'The name of the subscription category. Will be viewable by front-end users.', max_length=100, unique=True),
        ),
    ]
