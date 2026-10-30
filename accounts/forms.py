import re

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import AuthenticationForm

from .models import User


class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=150,
        label="First name",
        widget=forms.TextInput(attrs={"autocomplete": "given-name"}),
    )
    last_name = forms.CharField(
        max_length=150,
        label="Last name",
        widget=forms.TextInput(attrs={"autocomplete": "family-name"}),
    )
    mobile = forms.CharField(
        max_length=20, label="Mobile number", widget=forms.TelInput(attrs={"autocomplete": "tel"})
    )
    pincode = forms.CharField(
        max_length=6,
        min_length=6,
        label="PIN code",
        widget=forms.TextInput(attrs={"inputmode": "numeric", "maxlength": "6"}),
    )
    terms_accepted = forms.BooleanField(
        required=True,
        label="I agree to the Terms of Use and Privacy Notice.",
    )

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "email",
            "mobile",
            "city",
            "state",
            "pincode",
        )
        widgets = {
            "first_name": forms.TextInput(attrs={"autocomplete": "given-name"}),
            "last_name": forms.TextInput(attrs={"autocomplete": "family-name"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "mobile": forms.TelInput(attrs={"autocomplete": "tel"}),
            "pincode": forms.TextInput(attrs={"inputmode": "numeric", "maxlength": "10"}),
        }

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def clean_mobile(self):
        mobile = re.sub(r"[\s()-]", "", self.cleaned_data["mobile"])
        if mobile.startswith("+91"):
            mobile = mobile[3:]
        elif mobile.startswith("91") and len(mobile) == 12:
            mobile = mobile[2:]
        if not re.fullmatch(r"[6-9]\d{9}", mobile):
            raise forms.ValidationError("Enter a valid 10-digit Indian mobile number.")
        return mobile

    def clean_pincode(self):
        pincode = self.cleaned_data["pincode"].strip()
        if not re.fullmatch(r"\d{6}", pincode):
            raise forms.ValidationError("Enter a valid 6-digit PIN code.")
        return pincode

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.email
        if commit:
            user.save()
        return user


class EmailLoginForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(attrs={"autocomplete": "email", "autofocus": True}),
    )
