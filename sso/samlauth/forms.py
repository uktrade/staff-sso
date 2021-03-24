from django import forms
from django.conf import settings


def lookup_idp_ref_from_email(email_domain):
    idp_ref = None

    domain = email_domain.lower()

    for ref, allowed_email_domains in settings.AUTH_EMAIL_TO_IPD_MAP.items():
        if domain in allowed_email_domains:
            idp_ref = ref
            break

    return idp_ref


class EmailForm(forms.Form):
    email = forms.EmailField(
        widget=forms.TextInput(attrs={"class": "form-control form-control-1-5"})
    )

    def __init__(self, *args, **kwargs):
        self.idp_ref = None
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data["email"]

        email_domain = "@" + email.split("@")[1]

        idp_ref = lookup_idp_ref_from_email(email_domain)

        if not idp_ref and email_domain.lower() not in settings.EMAIL_TOKEN_DOMAIN_WHITELIST:
            raise forms.ValidationError("__unsupported_email__")

        self.idp_ref = idp_ref

        return email
