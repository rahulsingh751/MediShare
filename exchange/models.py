from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from medicines.models import MedicineListing


class MedicineRequest(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        PENDING_REVIEW = "pending_review", "Pending review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        RESERVED = "reserved", "Reserved"
        HANDOVER_SCHEDULED = "handover_scheduled", "Handover scheduled"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"

    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="medicine_requests",
    )
    listing = models.ForeignKey(
        MedicineListing, on_delete=models.PROTECT, related_name="requests"
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    note = models.CharField(max_length=500, blank=True)
    status = models.CharField(
        max_length=24, choices=Status.choices, default=Status.PENDING_REVIEW, db_index=True
    )
    reviewer_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gt=0), name="request_quantity_must_be_positive"
            ),
            models.UniqueConstraint(
                fields=["requester", "listing"],
                condition=Q(
                    status__in=[
                        "submitted",
                        "pending_review",
                        "approved",
                        "reserved",
                        "handover_scheduled",
                    ]
                ),
                name="one_active_request_per_member_listing",
            ),
        ]

    def __str__(self):
        return f"Request #{self.pk} for {self.listing}"


class SavedMedicine(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_medicines"
    )
    listing = models.ForeignKey(
        MedicineListing, on_delete=models.CASCADE, related_name="saved_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "listing"], name="unique_saved_listing")
        ]
        ordering = ["-created_at"]


class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    title = models.CharField(max_length=140)
    body = models.CharField(max_length=320)
    url = models.CharField(max_length=240, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class ListingReport(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        REVIEWING = "reviewing", "Reviewing"
        RESOLVED = "resolved", "Resolved"
        DISMISSED = "dismissed", "Dismissed"

    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="listing_reports",
    )
    listing = models.ForeignKey(
        MedicineListing, on_delete=models.PROTECT, related_name="reports"
    )
    reason = models.CharField(max_length=24)
    details = models.TextField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Report #{self.pk} on listing {self.listing_id}"
