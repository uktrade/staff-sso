# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-11-13 18:11
from __future__ import unicode_literals

from django.db import migrations, models

import sso.emailauth.models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="EmailToken",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True)),
                (
                    "token",
                    models.CharField(
                        default=sso.emailauth.models.generate_token, max_length=64, unique=True
                    ),
                ),
                ("email", models.EmailField(max_length=254)),
                ("used", models.BooleanField(default=False)),
            ],
        ),
    ]
