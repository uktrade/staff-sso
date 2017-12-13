from zenpy import Zenpy
from zenpy.lib.api_objects import Ticket, User as ZendeskUser, CustomField

from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _


# Zenpy will let the connection timeout after 5s and will retry 3 times
zenpy_client = Zenpy(timeout=5, **settings.ZENPY_CREDENTIALS)


class RequestAccessForm(forms.Form):
    full_name = forms.CharField(
        label=_('Full name'),
        max_length=200
    )
    team = forms.CharField(
        label=_('Team')
    )
    email = forms.EmailField(
        label=_('email'),
        widget=forms.HiddenInput(),
    )
    application = forms.CharField(
        label=_('Application the user requesting access'),
        widget=forms.HiddenInput(),
    )

    def get_or_create_zendesk_user(self, name, email):
        zendesk_user = ZendeskUser(
            name=name,
            email=email,
        )
        return zenpy_client.users.create_or_update(zendesk_user)

    def create_zendesk_ticket(self):

        zendesk_user = self.get_or_create_zendesk_user(self.cleaned_data['full_name'], self.cleaned_data['email'])

        description = (
            'Name: {full_name}\n'
            'Team: {team}\n'
            'Email: {email}\n'
            'Application: {application}\n'
        ).format(**self.cleaned_data)
        ticket = Ticket(
            subject=settings.ZENDESK_TICKET_SUBJECT,
            description=description,
            submitter_id=zendesk_user.id,
            requester_id=zendesk_user.id,
            custom_fields=[CustomField(id=31281329, value=360000030289)]
        )
        zenpy_client.tickets.create(ticket)
