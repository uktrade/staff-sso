# Generated by Django 2.2.13 on 2021-01-12 09:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0035_merge_20200903_1332'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='became_inactive_on',
            field=models.DateTimeField(blank=True, help_text='The date the user is account is deactivated', null=True),
        ),
    ]