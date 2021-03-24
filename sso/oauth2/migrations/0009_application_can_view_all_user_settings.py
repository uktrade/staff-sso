# Generated by Django 2.1.7 on 2019-05-30 10:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("oauth2", "0008_auto_20181121_1537"),
    ]

    operations = [
        migrations.AddField(
            model_name="application",
            name="can_view_all_user_settings",
            field=models.BooleanField(
                default=False,
                help_text="Allow all authenticated users to access all their recorded settings",
                verbose_name="allow access to all user settings",
            ),
        ),
    ]
