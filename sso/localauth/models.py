from django.core.validators import RegexValidator
from django.db import models


domain_validator = RegexValidator(regex=r'[a-zA-Z0-9\.-]+', message='Invalid domain')


class DomainWhitelist(models.Model):
    """A white list of external domains that we can redirect users to

    This is currently only used to verify the next url on the /logout/ page
    """

    domain = models.CharField(validators=[domain_validator], max_length=255)

    def __str__(self):
        return self.domain
