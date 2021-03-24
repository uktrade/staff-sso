# Generated by Django 2.1.7 on 2019-06-05 12:45

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0023_remove_user_user_settings"),
        ("usersettings", "0002_auto_20190528_1407"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="usersettings",
            name="user_id",
        ),
        migrations.AddField(
            model_name="usersettings",
            name="user",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="user.User",
                to_field="user_id",
            ),
        ),
    ]
