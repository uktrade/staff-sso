# Generated by Django 2.2.9 on 2020-02-12 13:22

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0029_applicationpermission'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='application_permissions',
            field=models.ManyToManyField(blank=True, help_text='Permissions that a user has on in an application', related_name='application_permissions', to='user.ApplicationPermission'),
        ),
        migrations.AlterField(
            model_name='applicationpermission',
            name='oauth2_application',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='application_permissions', to='samlidp.SamlApplication'),
        ),
        migrations.AlterField(
            model_name='applicationpermission',
            name='saml2_application',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='application_permissions', to=settings.OAUTH2_PROVIDER_APPLICATION_MODEL),
        ),
    ]