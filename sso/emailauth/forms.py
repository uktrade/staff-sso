from urllib.parse import quote_plus, urlparse, parse_qs

from django import forms
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.core.urlresolvers import reverse


from .models import EmailToken


class EmailForm(forms.Form):
    username = forms.CharField(max_length=255)   # TODO: regex restrict to allowed chars
    domain = forms.ChoiceField(choices=settings.EMAIL_TOKEN_DOMAIN_WHITELIST)

    @property
    def email(self):
        if self.is_valid():
            return self.cleaned_data['username'] + self.cleaned_data['domain']

    def extract_redirect_url(self, next_url):

        oauth2_url = urlparse(next_url)

        qs_items = parse_qs(oauth2_url.query)

        try:
            redirect_url = qs_items['redirect_uri'][0]
        except KeyError:
            return next_url

        url = urlparse(redirect_url)
        redirect_url = f'{url.scheme}://{url.netloc}'

        return redirect_url

    def send_signin_email(self, request):
        """
        Generate an EmailToken and send a sign in email to the user
        """
        token = EmailToken.objects.create_token(self.email)
        next_url = request.GET.get('next', '')

        if next_url:
            next_url = self.extract_redirect_url(next_url)
            next_url = quote_plus(next_url)

        path = reverse('email-auth-signin', kwargs=dict(token=token))

        url = '{scheme}{host}{path}?next={next_url}'.format(
            scheme='https://',
            host=request.get_host(),
            path=path,
            next_url=next_url
        )

        subject = render_to_string('emailauth/email_subject.txt')
        message = render_to_string('emailauth/email.txt', context=dict(auth_url=url))

        send_mail(
            subject,
            message,
            settings.EMAIL_FROM,
            [self.email],
            fail_silently=False,
        )
