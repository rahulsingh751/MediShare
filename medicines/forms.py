from PIL import Image, UnidentifiedImageError
from django import forms
from django.core.exceptions import ValidationError

from .models import MedicineImage, MedicineListing


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        if not data:
            return []
        files = data if isinstance(data, (list, tuple)) else [data]
        return [super(MultipleImageField, self).clean(item, initial) for item in files]


class MedicineListingForm(forms.ModelForm):
    safety_attestation = forms.BooleanField(
        required=True,
        label=(
            "I confirm this is not prescription-only, controlled or restricted, "
            "and that the packaging and storage details above are accurate."
        ),
    )
    quantity_available = forms.IntegerField(
        min_value=1,
        label="Available quantity",
        widget=forms.NumberInput(attrs={"min": "1"}),
    )
    images = MultipleImageField(
        required=False,
        label="Packaging photos",
        help_text="Up to 5 clear images. Maximum 5 MB each.",
    )

    class Meta:
        model = MedicineListing
        fields = (
            "name",
            "brand_name",
            "generic_name",
            "active_ingredient",
            "strength",
            "dosage_form",
            "manufacturer",
            "composition",
            "batch_number",
            "manufacturing_date",
            "expiry_date",
            "quantity_available",
            "prescription_required",
            "controlled_or_restricted",
            "original_packaging",
            "seal_intact",
            "packaging_opened",
            "packaging_damaged",
            "stored_as_instructed",
            "recall_status_confirmed",
            "requires_cold_chain",
            "visible_damage",
            "city",
            "locality",
            "pincode",
            "handover_preference",
        )
        widgets = {
            "manufacturing_date": forms.DateInput(attrs={"type": "date"}),
            "expiry_date": forms.DateInput(attrs={"type": "date"}),
            "composition": forms.Textarea(attrs={"rows": 3}),
            "handover_preference": forms.TextInput(
                attrs={"placeholder": "Preferred public or partner location"}
            ),
            "pincode": forms.TextInput(attrs={"inputmode": "numeric", "maxlength": "10"}),
        }
        labels = {
            "recall_status_confirmed": (
                "I confirmed this medicine is not recalled or withdrawn"
            )
        }

    def clean_images(self):
        uploaded = self.files.getlist("images")
        if len(uploaded) > 5:
            raise ValidationError("Upload no more than 5 images.")
        for image in uploaded:
            if image.size > 5 * 1024 * 1024:
                raise ValidationError("Each image must be 5 MB or smaller.")
            if image.content_type not in {"image/jpeg", "image/png", "image/webp"}:
                raise ValidationError("Only JPG, PNG and WebP images are accepted.")
            try:
                with Image.open(image) as opened_image:
                    if opened_image.format not in {"JPEG", "PNG", "WEBP"}:
                        raise ValidationError("Only JPG, PNG and WebP images are accepted.")
                    if opened_image.width * opened_image.height > 25_000_000:
                        raise ValidationError("Image dimensions are too large.")
                    extension = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}[
                        opened_image.format
                    ]
                    opened_image.verify()
            except (
                UnidentifiedImageError,
                OSError,
                Image.DecompressionBombError,
                Image.DecompressionBombWarning,
            ):
                raise ValidationError("One of the uploaded files is not a valid image.")
            image.name = f"upload.{extension}"
            image.seek(0)
        return uploaded

    def clean_pincode(self):
        pincode = self.cleaned_data["pincode"].strip()
        if not re.fullmatch(r"\d{6}", pincode):
            raise ValidationError("Enter a valid 6-digit PIN code.")
        return pincode

    def save(self, commit=True, *, owner):
        listing = super().save(commit=False)
        listing.owner = owner
        listing.status = (
            MedicineListing.Status.SUBMITTED
            if listing.is_eligible_for_review
            else MedicineListing.Status.RESTRICTED
        )
        listing.reviewer_notes = "; ".join(listing.ineligible_reasons)
        if commit:
            listing.save()
            self.save_m2m()
            for image in self.cleaned_data.get("images", []):
                MedicineImage.objects.create(listing=listing, image=image)
        return listing
import re
