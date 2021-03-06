# Generated by Django 3.1.5 on 2021-03-18 12:22

from django.db import migrations, models
import djangosaml2idp.models


class Migration(migrations.Migration):

    dependencies = [
        ("samlidp", "0004_auto_20210317_1623"),
    ]

    run_before = [
        ("djangosaml2idp", "0001_initial_squashed_swappable"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="samlapplication",
            options={
                "verbose_name": "Service Provider",
                "verbose_name_plural": "Service Providers",
            },
        ),
        migrations.RemoveField(
            model_name="samlapplication",
            name="enabled",
        ),
        migrations.RemoveField(
            model_name="samlapplication",
            name="name",
        ),
        migrations.AddField(
            model_name="samlapplication",
            name="_digest_algorithm",
            field=models.CharField(
                blank=True,
                choices=[
                    ("http://www.w3.org/2000/09/xmldsig#sha1", "DIGEST_SHA1"),
                    ("http://www.w3.org/2001/04/xmldsig-more#sha224", "DIGEST_SHA224"),
                    ("http://www.w3.org/2001/04/xmlenc#sha256", "DIGEST_SHA256"),
                    ("http://www.w3.org/2001/04/xmldsig-more#sha384", "DIGEST_SHA384"),
                    ("http://www.w3.org/2001/04/xmlenc#sha512", "DIGEST_SHA512"),
                    ("http://www.w3.org/2001/04/xmlenc#ripemd160", "DIGEST_RIPEMD160"),
                ],
                help_text="If not set, default to settings.SAML_AUTHN_DIGEST_ALG.",
                max_length=256,
                null=True,
                verbose_name="Digest algorithm",
            ),
        ),
        migrations.AddField(
            model_name="samlapplication",
            name="_encrypt_saml_responses",
            field=models.BooleanField(
                help_text="If not set, default to settings.SAML_ENCRYPT_AUTHN_RESPONSE. If that one is not set, default to False.",
                null=True,
                verbose_name="Encrypt SAML Response",
            ),
        ),
        migrations.AddField(
            model_name="samlapplication",
            name="_sign_assertion",
            field=models.BooleanField(
                blank=True,
                help_text='If not set, default to the "sign_assertion" setting of the IDP. If that one is not set, default to False.',
                null=True,
                verbose_name="Sign assertion",
            ),
        ),
        migrations.AddField(
            model_name="samlapplication",
            name="_sign_response",
            field=models.BooleanField(
                blank=True,
                help_text='If not set, default to the "sign_response" setting of the IDP. If that one is not set, default to False.',
                null=True,
                verbose_name="Sign response",
            ),
        ),
        migrations.AddField(
            model_name="samlapplication",
            name="_signing_algorithm",
            field=models.CharField(
                blank=True,
                choices=[
                    ("http://www.w3.org/2000/09/xmldsig#rsa-sha1", "SIG_RSA_SHA1"),
                    ("http://www.w3.org/2001/04/xmldsig-more#rsa-sha224", "SIG_RSA_SHA224"),
                    ("http://www.w3.org/2001/04/xmldsig-more#rsa-sha256", "SIG_RSA_SHA256"),
                    ("http://www.w3.org/2001/04/xmldsig-more#rsa-sha384", "SIG_RSA_SHA384"),
                    ("http://www.w3.org/2001/04/xmldsig-more#rsa-sha512", "SIG_RSA_SHA512"),
                ],
                help_text="If not set, use settings.SAML_AUTHN_SIGN_ALG.",
                max_length=256,
                null=True,
                verbose_name="Signing algorithm",
            ),
        ),
        migrations.AddField(
            model_name="samlapplication",
            name="real_entity_id",
            field=models.CharField(
                blank=True,
                help_text="Takes precendence over the entity_id field and allows for the entity_id field to be an alias",
                max_length=255,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="samlapplication",
            name="remote_metadata_url",
            field=models.CharField(
                blank=True,
                help_text="If set, metadata will be fetched upon saving into the local metadata xml field, and automatically be refreshed after the expiration timestamp.",
                max_length=512,
                verbose_name="Remote metadata URL",
            ),
        ),
        migrations.AlterField(
            model_name="samlapplication",
            name="_attribute_mapping",
            field=models.TextField(
                default=djangosaml2idp.models.get_default_attribute_mapping,
                help_text="dict with the mapping from django attributes to saml attributes in the identity.",
                verbose_name="Attribute mapping",
            ),
        ),
        migrations.AlterField(
            model_name="samlapplication",
            name="_processor",
            field=models.CharField(
                default=djangosaml2idp.models.get_default_processor,
                help_text="Import string for the (access) Processor to use.",
                max_length=256,
                verbose_name="Processor",
            ),
        ),
        migrations.AlterField(
            model_name="samlapplication",
            name="entity_id",
            field=models.CharField(max_length=255, unique=True, verbose_name="Entity ID"),
        ),
        migrations.AlterField(
            model_name="samlapplication",
            name="slug",
            field=models.SlugField(unique=True, verbose_name="unique text id"),
        ),
        migrations.AddIndex(
            model_name="samlapplication",
            index=models.Index(fields=["entity_id"], name="samlidp_sam_entity__f7db75_idx"),
        ),
    ]
