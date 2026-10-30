from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from django.urls import reverse


EMAIL_VERIFICATION_SALT = "accounts.email-verification"


def send_verification_email(user, request):
    token = signing.dumps({"user_id": user.pk}, salt=EMAIL_VERIFICATION_SALT)
    verification_url = request.build_absolute_uri(
        reverse("verify_email", kwargs={"token": token})
    )
    send_mail(
        "Verify your MediShare email address",
        f"Confirm your email address using this link: {verification_url}\n"
        "If you did not create this account, you can ignore this message.",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
