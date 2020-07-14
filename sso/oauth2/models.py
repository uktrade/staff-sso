from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
from oauth2_provider.models import AbstractApplication


class Application(AbstractApplication):
    application_key = models.SlugField(
        _('unique text id'),
        max_length=50,
        unique=True)

    display_name = models.CharField(
        _('the name of the application displayed to end users'),
        max_length=100,
    )

    public = models.BooleanField(
        _('display a link to this application on the logged in page'),
        max_length=255,
        default=False,
    )

    start_url = models.CharField(
        _('the start url for the application'),
        max_length=255,
    )

    default_access_allowed = models.BooleanField(
        _('default access allowed'),
        default=False,
        help_text=_(
            'Allow all authenticated users to access this application'
        )
    )

    allow_access_by_email_suffix = models.CharField(
        _('allow access by email'),
        null=True,
        blank=True,
        max_length=255,
        help_text=_(
            ('A comma separated list of email domains, e.g. "mobile.ukti.gov.uk, trade.gsi.gov.uk, fco.gov.uk" '
             'User\'s with an email in this list will be given access.  NOTE: all user emails are checked - '
             'including aliases.')
        )
    )

    email_ordering = models.CharField(
        _('email ordering'),
        blank=True,
        null=True,
        max_length=255,
        help_text=_(
            ('A comma separated list of email domains, e.g "mobile.ukti.gov.uk, trade.gsi.gov.uk, fco.gov.uk" '
             'for users with multiple email addresses this list determines which email is sent to the application.')
        )
    )

    provide_immutable_email = models.BooleanField(
        _('provide immutable primary email to the application'),
        default=False,
        help_text=_(
            ('Always provide the same primary email to the application, instead of selecting the primary email '
             'user\'s list of emails')
        )
    )

    can_view_all_user_settings = models.BooleanField(
        _('allow access to all user settings'),
        default=False,
        help_text=_(
            'Allow for this application authenticated users to access all their user-settings'
        )
    )

    allow_tokens_from = models.ManyToManyField('self', blank=True, symmetrical=False)

    def save(self, *args, **kwargs):

        # these fields are not user configurable
        self.client_type = 'confidential'
        self.authorization_grant_type = 'authorization-code'
        self.skip_authorization = True

        super().save(*args, **kwargs)

    def get_email_order(self):
        ordering = self.email_ordering or getattr(settings, 'DEFAULT_EMAIL_ORDER', '')

        if not ordering:
            return []

        return [email.strip() for email in ordering.split(',')]

    @staticmethod
    def get_default_access_applications():
        return Application.objects.filter(default_access_allowed=True)
