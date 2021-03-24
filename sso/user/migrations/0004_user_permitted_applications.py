# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-10-26 11:15
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.OAUTH2_PROVIDER_APPLICATION_MODEL),
        ("user", "0003_auto_20170707_1441"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="permitted_applications",
            field=models.ManyToManyField(
                help_text="Applications that this use is permitted to access",
                related_name="users",
                to=settings.OAUTH2_PROVIDER_APPLICATION_MODEL,
            ),
        ),
    ]
