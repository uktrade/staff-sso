# Generated by Django 2.2.13 on 2020-06-16 19:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0031_auto_20200214_1618'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='last_modified',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
