# Generated by Django 2.2.4 on 2019-12-16 14:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0027_auto_20191212_1427"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="email_user_id",
            field=models.EmailField(
                help_text="A unique user id in an email format", max_length=254, unique=True
            ),
        ),
    ]
