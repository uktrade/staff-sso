# Generated by Django 2.1.7 on 2019-05-28 14:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("usersettings", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="usersettings",
            name="app_slug",
            field=models.CharField(max_length=50, verbose_name="app slug"),
        ),
    ]
