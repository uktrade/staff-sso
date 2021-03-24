from django.conf import settings
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic.edit import FormView

from zenpy import Zenpy
from zenpy.lib.api_objects import CustomField, Ticket, User as ZendeskUser

from .forms import RequestAccessForm


class AccessDeniedView(FormView):
    template_name = "sso/access-denied.html"
    form_class = RequestAccessForm
    success_url = reverse_lazy("contact:success")

    def form_valid(self, form):

        ticket_id = self.create_zendesk_ticket(form.cleaned_data)

        return render(
            self.request, "sso/request-access-success.html", dict(zendesk_ticket_id=ticket_id)
        )

    def get_zendesk_client(self):
        # Zenpy will let the connection timeout after 5s and will retry 3 times
        return Zenpy(timeout=5, **settings.ZENPY_CREDENTIALS)

    def create_zendesk_ticket(self, cleaned_data):

        email = self.request.user.email
        application = self.request.session.get("_last_failed_access_app", "Unspecified")

        zendesk_user = ZendeskUser(name=cleaned_data["full_name"], email=email)

        description = (
            "Name: {full_name}\n" "Team: {team}\n" "Email: {email}\n" "Application: {application}\n"
        ).format(email=email, application=application, **cleaned_data)
        ticket = Ticket(
            subject=settings.ZENDESK_TICKET_SUBJECT,
            description=description,
            requester=zendesk_user,
            custom_fields=[CustomField(id="31281329", value="auth_broker")],
        )
        response = self.get_zendesk_client().tickets.create(ticket)
        return response.ticket.id
