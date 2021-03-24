# Generated by Django 2.1.7 on 2019-06-04 14:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0019_user_user_settings"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="user_settings",
            field=models.ManyToManyField(
                blank=True, related_name="user_settings", to="usersettings.UserSettings"
            ),
        ),
    ]
