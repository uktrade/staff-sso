import pytest

from django.core.urlresolvers import reverse

from .test_auth_flow import log_user_in

pytestmark = [
    pytest.mark.django_db
]


class TestSubmission:

    def test_form_hidden_for_unauthenticated_users(self, client):

        response = client.get(reverse('contact:access-denied'))

        assert response.status_code == 200
        assert '<form' not in str(response.content)

    def test_submission(self, client, mocker):

        get_client_mock = mocker.patch('sso.contact.views.AccessDeniedView.get_zendesk_client')
        create_ticket_mock = get_client_mock.return_value
        ticket_mock = create_ticket_mock.tickets.create.return_value
        ticket_mock.ticket.id = 'ZENDESKTICKETID'

        log_user_in(client)

        session = client.session
        session['_last_failed_access_app'] = 'TestApplication123'
        session.save()

        form_data = {
            'full_name': 'Mr Smith',
            'team': 'webops'
        }

        response = client.post(reverse('contact:access-denied'), form_data)

        assert response.status_code == 200
        assert 'ZENDESKTICKETID' in str(response.content)
        assert create_ticket_mock.tickets.create.called

        ticket = create_ticket_mock.tickets.create.call_args[0][0]
        assert ticket.description == 'Name: Mr Smith\nTeam: webops\nEmail: user1@example.com\nApplication: TestApplication123\n'
