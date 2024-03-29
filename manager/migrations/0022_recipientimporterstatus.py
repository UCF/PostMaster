# Generated by Django 3.1.1 on 2021-06-29 15:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0021_auto_20201005_1123'),
    ]

    operations = [
        migrations.CreateModel(
            name='RecipientImporterStatus',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('import_name', models.CharField(max_length=255)),
                ('data_hash', models.CharField(max_length=1000)),
                ('row_count', models.IntegerField()),
                ('import_date', models.DateField(auto_now_add=True)),
            ],
        ),
    ]
