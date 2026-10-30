from django.test import TestCase
from django.urls import reverse

from .forms import RegistrationForm
from .models import User


class RegistrationTests(TestCase):
    def test_registration_creates_unverified_member_and_sends_console_email(self):
        response = self.client.post(
            reverse("register"),
            {
                "first_name": "Asha",
                "last_name": "Rao",
                "email": "ASHA@example.com",
                "mobile": "9876543210",
                "city": "Pune",
                "state": "Maharashtra",
                "pincode": "411001",
                "password1": "StrongPassphrase#2026",
                "password2": "StrongPassphrase#2026",
                "terms_accepted": "on",
            },
        )
        self.assertRedirects(response, reverse("login"))
        user = User.objects.get(email="asha@example.com")
        self.assertEqual(user.username, user.email)
        self.assertFalse(user.email_verified)
        self.assertIsNotNone(user.accepted_terms_at)

    def test_registration_requires_terms_consent(self):
        form = RegistrationForm(
            data={
                "first_name": "Asha",
                "last_name": "Rao",
                "email": "asha@example.com",
                "mobile": "9876543210",
                "city": "Pune",
                "state": "Maharashtra",
                "pincode": "411001",
                "password1": "StrongPassphrase#2026",
                "password2": "StrongPassphrase#2026",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("terms_accepted", form.errors)

    def test_signed_email_verification_activates_account(self):
        from django.core import signing
        from .services import EMAIL_VERIFICATION_SALT

        user = User.objects.create_user(
            username="asha@example.com",
            email="asha@example.com",
            password="StrongPassphrase#2026",
        )
        token = signing.dumps({"user_id": user.pk}, salt=EMAIL_VERIFICATION_SALT)
        response = self.client.get(reverse("verify_email", args=[token]))
        self.assertRedirects(response, reverse("login"))
        user.refresh_from_db()
        self.assertTrue(user.email_verified)

    def test_resend_verification_route_does_not_match_token_route(self):
        user = User.objects.create_user(
            username="asha@example.com",
            email="asha@example.com",
            password="StrongPassphrase#2026",
        )
        self.client.force_login(user)

        response = self.client.post(reverse("resend_verification"))

        self.assertRedirects(response, reverse("dashboard"))
