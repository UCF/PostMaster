# Generated by Django 3.1.12 on 2021-08-27 13:10

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0023_auto_20210825_1022'),
    ]

    operations = [
        migrations.AddField(
            model_name='campaign',
            name='click_to_open_rate_target',
            field=models.FloatField(default=10),
        ),
        migrations.AddField(
            model_name='campaign',
            name='open_rate_target',
            field=models.FloatField(default=25),
        ),
        migrations.AlterField(
            model_name='email',
            name='campaign',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='emails', to='manager.campaign'),
        ),
    ]
