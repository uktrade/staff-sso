# Generated by Django 2.1.7 on 2019-06-04 15:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("usersettings", "0002_auto_20190528_1407"),
        ("user", "0021_auto_20190604_1550"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="user",
            name="user_settings",
        ),
        migrations.AddField(
            model_name="user",
            name="user_settings",
            field=models.ManyToManyField(
                blank=True, related_name="user_settings", to="usersettings.UserSettings"
            ),
        ),
    ]
