# Generated by Django 2.2.3 on 2019-08-02 14:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0023_remove_user_user_settings'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailaddress',
            name='last_login',
            field=models.DateTimeField(null=True),
        ),
    ]
