# Generated by Django 2.2.13 on 2020-08-12 11:53

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0033_serviceemailaddress'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='use_new_journey',
        ),
    ]