from django import forms

from sso.oauth2.models import Application


class AdminUserUploadForm(forms.Form):
    applications = forms.ModelMultipleChoiceField(
        label='select which applications newly imported users will be able to access',
        widget=forms.CheckboxSelectMultiple,
        queryset=Application.objects.all(),
        required=False
    )

    dry_run = forms.BooleanField(
        label='Test run - do not change any data',
        required=False,
        initial=True
    )

    file = forms.FileField(
        label='select a csv file',
        required=True,
        initial=True
    )


class AdminUserAddAliasForm(forms.Form):
    dry_run = forms.BooleanField(
        label='Test run - do not change any data',
        required=False,
        initial=True
    )

    file = forms.FileField(
        label='select a csv file',
        required=True
    )
