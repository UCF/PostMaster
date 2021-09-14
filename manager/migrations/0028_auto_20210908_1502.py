# Generated by Django 3.1.12 on 2021-09-08 15:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0027_auto_20210908_1104'),
    ]

    operations = [
        migrations.AlterField(
            model_name='segmentrule',
            name='field',
            field=models.CharField(choices=[('in_recipient_group', 'In recipient group'), ('has_attribute', 'Has attribute'), ('received_instance', 'Received instance'), ('opened_email', 'Opened email'), ('opened_instance', 'Opened instance'), ('clicked_link', 'Clicked on URL'), ('clicked_any_url_in_email', 'Clicked on any url in instance'), ('clicked_url_in_instance', 'Clicked on a specific url in an instance')], max_length=40),
        ),
    ]