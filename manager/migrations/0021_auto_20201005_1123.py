# Generated by Django 3.1.1 on 2020-10-05 11:23

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('manager', '0020_auto_20201002_1514'),
    ]

    operations = [
        migrations.AlterField(
            model_name='email',
            name='creator',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_email', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='email',
            name='subscription_category',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='emails', to='manager.subscriptioncategory'),
        ),
    ]
