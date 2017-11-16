from django import forms
from sso.oauth2.models import Application


class AdminUserUploadForm(forms.Form):
    applications = forms.ModelMultipleChoiceField(
        label='select which applications newly imported users will be able to access',
        widget=forms.CheckboxSelectMultiple,
        queryset=Application.objects.all(),
        required=False
    )

    modify_applications = forms.ModelMultipleChoiceField(
        label='modify permissions for existing users',
        widget=forms.CheckboxSelectMultiple,
        queryset=Application.objects.all(),
        required=False,
        help_text='NOTE: applications will be added or removed based on the selected option below'
    )

    modify_applications_action = forms.ChoiceField(
        label='action to take for existing users',
        widget=forms.RadioSelect,
        choices=(
            ('add', 'Add permissions'),
            ('remove', 'Remove permissions')
        ),
        initial='add',
    )

    file = forms.FileField(
        label='select a csv file',
        required=False
    )
