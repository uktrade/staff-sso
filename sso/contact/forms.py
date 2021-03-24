from django import forms
from django.utils.translation import gettext_lazy as _


class RequestAccessForm(forms.Form):
    full_name = forms.RegexField(
        label=_("Full name"),
        max_length=200,
        regex=r"^[A-Za-z\.\- ]*$",
        widget=forms.TextInput(attrs={"class": "form-control"}),
        error_messages={
            "required": "Provide your full name",
            "invalid": "Provide a valid full name without punctuation",
        },
    )
    team = forms.RegexField(
        label=_("Team"),
        regex=r"^[A-Za-z0-9\&\.\-\(\) ]*$",
        widget=forms.TextInput(attrs={"class": "form-control"}),
        error_messages={
            "required": "Provide your team name",
            "invalid": "Provide a valid team name without punctuation",
        },
    )
