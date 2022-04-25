# Generated by Django 3.1.14 on 2022-04-22 11:11

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0032_db_collation'),
    ]

    operations = [
        migrations.CreateModel(
            name='CampaignInstanceStat',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('open_rate', models.FloatField(default=0)),
                ('click_rate', models.FloatField(default=0)),
                ('recipient_count', models.IntegerField(default=0)),
                ('click_to_open_rate', models.FloatField(default=0)),
                ('campaign', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='instance_stats', to='manager.campaign')),
                ('instance', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='instances', to='manager.instance')),
            ],
        ),
    ]