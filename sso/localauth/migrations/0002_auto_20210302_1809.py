# Generated by Django 3.1.5 on 2021-03-02 18:09

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("localauth", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="domainwhitelist",
            name="domain",
            field=models.CharField(
                max_length=255,
                validators=[
                    django.core.validators.RegexValidator(
                        message="Invalid domain", regex="[a-zA-Z0-9\\.-]+"
                    )
                ],
            ),
        ),
    ]
