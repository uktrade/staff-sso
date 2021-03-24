# Generated by Django 2.2.13 on 2020-08-20 17:42

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="DomainWhitelist",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "domain",
                    models.CharField(
                        max_length=255,
                        validators=[
                            django.core.validators.RegexValidator(
                                message="Invalid domain", regex="[a-zA-Z-0-9\\.-]+"
                            )
                        ],
                    ),
                ),
            ],
        ),
    ]
