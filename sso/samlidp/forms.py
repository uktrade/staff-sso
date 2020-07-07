from django import forms


class SelectEmailForm(forms.Form):

    email = forms.ChoiceField(widget=forms.widgets.Select(attrs={'class': 'form-control'}))

    def __init__(self, email_choices: list, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['email'].choices = zip(email_choices, email_choices)
