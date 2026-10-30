from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        MEMBER = "member", "Community member"
        ORGANIZATION = "organization", "Healthcare organization"
        VERIFIER = "verifier", "Medical verifier"

    email = models.EmailField(unique=True)
    mobile = models.CharField(max_length=20, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    email_verified = models.BooleanField(default=False)
    is_pharmacist_verified = models.BooleanField(default=False)
    accepted_terms_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.get_full_name() or self.email
