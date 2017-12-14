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
        required=False
    )

    file = forms.FileField(
        label='select a csv file',
        required=False
    )


class AdminUserAddAliasForm(forms.Form):
    dry_run = forms.BooleanField(
        label='Test run - do not change any data',
        required=False
    )

    file = forms.FileField(
        label='select a csv file',
        required=False
    )
