# Generated by Django 2.0.7 on 2018-07-31 12:04

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('oauth2', '0004_application_allow_access_by_email_suffix_squashed_0005_auto_20180205_2004'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='allow_tokens_from',
            field=models.ManyToManyField(blank=True, to=settings.OAUTH2_PROVIDER_APPLICATION_MODEL),
        ),
    ]