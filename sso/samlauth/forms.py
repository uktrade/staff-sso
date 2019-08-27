from django import forms


class EmailForm(forms.Form):
    email = forms.EmailField(
        widget=forms.TextInput(attrs={'class': 'form-control form-control-1-4'}))
