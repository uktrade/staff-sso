# Generated by Django 2.2.13 on 2020-07-15 16:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0033_serviceemailaddress'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='is_active',
            field=models.BooleanField(default=True, help_text='is the account active?', verbose_name='is active'),
        ),
    ]
