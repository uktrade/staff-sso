# Generated by Django 2.1.7 on 2019-04-29 14:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0017_user_is_staff"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="contact_email",
            field=models.EmailField(blank=True, max_length=254),
        ),
    ]
