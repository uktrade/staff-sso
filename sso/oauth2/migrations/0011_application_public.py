# Generated by Django 2.2.9 on 2020-01-27 13:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("oauth2", "0010_auto_20190604_1436"),
    ]

    operations = [
        migrations.AddField(
            model_name="application",
            name="public",
            field=models.BooleanField(
                default=False,
                max_length=255,
                verbose_name="display a link to this application on the logged in page",
            ),
        ),
    ]
