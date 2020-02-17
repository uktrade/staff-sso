# Generated by Django 2.2.9 on 2020-02-14 16:18

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0030_auto_20200212_1322'),
    ]

    operations = [
        migrations.AlterField(
            model_name='applicationpermission',
            name='oauth2_application',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='application_permissions', to=settings.OAUTH2_PROVIDER_APPLICATION_MODEL),
        ),
        migrations.AlterField(
            model_name='applicationpermission',
            name='saml2_application',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='application_permissions', to='samlidp.SamlApplication'),
        ),
    ]