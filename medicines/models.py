from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


def listing_image_path(instance, filename):
    suffix = Path(filename).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        suffix = ".jpg"
    return f"listing-images/{instance.listing_id}/{uuid4().hex}{suffix}"


class MedicineListing(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under review"
        APPROVED = "approved", "Reviewed for discovery"
        REJECTED = "rejected", "Rejected"
        RESTRICTED = "restricted", "Restricted"
        RESERVED = "reserved", "Reserved"
        COMPLETED = "completed", "Completed"
        WITHDRAWN = "withdrawn", "Withdrawn"
        EXPIRED = "expired", "Expired"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="medicine_listings",
    )
    name = models.CharField(max_length=160)
    brand_name = models.CharField(max_length=160, blank=True)
    generic_name = models.CharField(max_length=160, blank=True)
    active_ingredient = models.CharField(max_length=240, blank=True)
    strength = models.CharField(max_length=100, blank=True)
    dosage_form = models.CharField(max_length=100, blank=True)
    manufacturer = models.CharField(max_length=160, blank=True)
    composition = models.TextField(blank=True)
    batch_number = models.CharField(max_length=100)
    manufacturing_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField()
    quantity_available = models.PositiveIntegerField()
    prescription_required = models.BooleanField(default=True)
    controlled_or_restricted = models.BooleanField(default=False)
    original_packaging = models.BooleanField(default=False)
    seal_intact = models.BooleanField(default=False)
    packaging_opened = models.BooleanField(default=True)
    packaging_damaged = models.BooleanField(default=False)
    stored_as_instructed = models.BooleanField(default=False)
    recall_status_confirmed = models.BooleanField(default=False)
    requires_cold_chain = models.BooleanField(default=True)
    visible_damage = models.BooleanField(default=False)
    city = models.CharField(max_length=100)
    locality = models.CharField(max_length=120, blank=True)
    pincode = models.CharField(max_length=10)
    handover_preference = models.CharField(max_length=160, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.SUBMITTED, db_index=True
    )
    reviewer_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "city"]),
            models.Index(fields=["name", "brand_name"]),
            models.Index(fields=["expiry_date"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.strength})".strip()

    @property
    def ineligible_reasons(self):
        reasons = []
        if self.quantity_available < 1:
            reasons.append("No available quantity")
        if self.expiry_date and self.expiry_date <= timezone.localdate():
            reasons.append("Expired or expiring today")
        if self.prescription_required:
            reasons.append("Prescription required")
        if self.controlled_or_restricted:
            reasons.append("Controlled or restricted medicine")
        if not self.original_packaging:
            reasons.append("Not in original packaging")
        if not self.seal_intact:
            reasons.append("Seal is not intact")
        if self.packaging_opened:
            reasons.append("Packaging has been opened")
        if self.packaging_damaged:
            reasons.append("Packaging is damaged")
        if not self.stored_as_instructed:
            reasons.append("Storage conditions are unconfirmed")
        if not self.recall_status_confirmed:
            reasons.append("Recall status is unconfirmed")
        if self.requires_cold_chain:
            reasons.append("Cold-chain handling is not supported")
        if self.visible_damage:
            reasons.append("Visible damage reported")
        return reasons

    @property
    def is_eligible_for_review(self):
        return not self.ineligible_reasons

    def clean(self):
        super().clean()
        if self.manufacturing_date and self.expiry_date:
            if self.manufacturing_date > self.expiry_date:
                raise ValidationError(
                    {"expiry_date": "Expiry date must be after the manufacturing date."}
                )
        if self.status == self.Status.APPROVED and self.ineligible_reasons:
            raise ValidationError(
                {"status": "This medicine does not meet the platform's minimum eligibility checks."}
            )

    def save(self, *args, **kwargs):
        if self.pk and self.status in {self.Status.APPROVED, self.Status.RESERVED}:
            if self.expiry_date and self.expiry_date <= timezone.localdate():
                self.status = self.Status.EXPIRED
        super().save(*args, **kwargs)


class MedicineImage(models.Model):
    listing = models.ForeignKey(
        MedicineListing, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to=listing_image_path)
    caption = models.CharField(max_length=80, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        super().clean()
        if self.image and self.image.size > 5 * 1024 * 1024:
            raise ValidationError({"image": "Image files must be 5 MB or smaller."})

    def __str__(self):
        return self.caption or f"Image for listing {self.listing_id}"
