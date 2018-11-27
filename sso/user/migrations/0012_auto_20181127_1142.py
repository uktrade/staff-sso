# Generated by Django 2.0.8 on 2018-11-27 11:42

from django.conf import settings
from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.OAUTH2_PROVIDER_APPLICATION_MODEL),
        ('user', '0011_user_unique_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='AccessProfile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='name')),
                ('description', models.TextField(blank=True, help_text='for internal use only', null=True, verbose_name='description')),
                ('oauth2_applications', models.ManyToManyField(related_name='access_profiles', to=settings.OAUTH2_PROVIDER_APPLICATION_MODEL)),
            ],
        ),
        migrations.AlterField(
            model_name='user',
            name='user_id',
            field=models.UUIDField(default=uuid.uuid4, unique=True, verbose_name='unique user id'),
        ),
        migrations.AddField(
            model_name='user',
            name='access_profiles',
            field=models.ManyToManyField(blank=True, related_name='users', to='user.AccessProfile'),
        ),
    ]
