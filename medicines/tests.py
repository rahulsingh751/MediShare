from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from exchange.models import MedicineRequest, Notification

from .models import MedicineListing


class MedicineWorkflowTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user(
            username="member@example.com",
            email="member@example.com",
            password="StrongPassphrase#2026",
            first_name="Asha",
            email_verified=True,
        )

    def create_listing(self, **overrides):
        values = {
            "owner": self.member,
            "name": "Sample medicine",
            "brand_name": "Sample brand",
            "generic_name": "Sample generic",
            "active_ingredient": "Sample ingredient",
            "strength": "10 mg",
            "dosage_form": "Tablet",
            "manufacturer": "Example manufacturer",
            "batch_number": "B-100",
            "expiry_date": timezone.localdate() + timedelta(days=180),
            "quantity_available": 3,
            "prescription_required": False,
            "controlled_or_restricted": False,
            "original_packaging": True,
            "seal_intact": True,
            "packaging_opened": False,
            "packaging_damaged": False,
            "stored_as_instructed": True,
            "recall_status_confirmed": True,
            "requires_cold_chain": False,
            "visible_damage": False,
            "city": "Pune",
            "locality": "Kothrud",
            "pincode": "411038",
            "status": MedicineListing.Status.APPROVED,
        }
        values.update(overrides)
        return MedicineListing.objects.create(**values)

    def test_discovery_only_shows_reviewed_eligible_available_listings(self):
        self.create_listing()
        self.create_listing(name="Prescription item", prescription_required=True)
        self.create_listing(name="Restricted item", controlled_or_restricted=True)
        self.create_listing(
            name="Unavailable item", quantity_available=0
        )
        self.client.force_login(self.member)

        response = self.client.get(reverse("discover"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sample medicine")
        self.assertNotContains(response, "Prescription item")
        self.assertNotContains(response, "Restricted item")
        self.assertNotContains(response, "Unavailable item")

    def test_unverified_member_cannot_submit_listing(self):
        unverified = User.objects.create_user(
            username="unverified@example.com",
            email="unverified@example.com",
            password="StrongPassphrase#2026",
        )
        self.client.force_login(unverified)

        response = self.client.post(
            reverse("submit_listing"),
            {
                "name": "Unverified submission",
                "expiry_date": timezone.localdate() + timedelta(days=200),
                "quantity_available": 1,
                "city": "Pune",
                "pincode": "411001",
            },
        )

        self.assertRedirects(response, reverse("dashboard"))
        self.assertFalse(
            MedicineListing.objects.filter(name="Unverified submission").exists()
        )

    def test_prescription_listing_is_restricted_and_never_appears_in_discovery(self):
        self.client.force_login(self.member)
        response = self.client.post(
            reverse("submit_listing"),
            {
                "name": "Prescription listing",
                "batch_number": "B-101",
                "expiry_date": timezone.localdate() + timedelta(days=120),
                "quantity_available": 1,
                "prescription_required": "on",
                "safety_attestation": "on",
                "city": "Pune",
                "pincode": "411001",
            },
        )

        self.assertRedirects(response, reverse("dashboard"))
        listing = MedicineListing.objects.get(name="Prescription listing")
        self.assertEqual(listing.status, MedicineListing.Status.RESTRICTED)
        self.client.get(reverse("discover"))
        self.assertNotContains(
            self.client.get(reverse("discover")), "Prescription listing"
        )

    def test_suggestions_return_only_publicly_discoverable_medicines(self):
        self.create_listing()
        self.create_listing(name="Hidden prescription", prescription_required=True)
        self.client.force_login(self.member)

        response = self.client.get(reverse("search_suggestions"), {"q": "Sample"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"suggestions": [{"label": "Sample medicine · Sample brand · 10 mg", "query": "Sample medicine"}]},
        )
        hidden = self.client.get(reverse("search_suggestions"), {"q": "Hidden"})
        self.assertEqual(hidden.json(), {"suggestions": []})

    def test_listing_report_is_persisted_for_staff_review(self):
        listing = self.create_listing()
        self.client.force_login(self.member)

        response = self.client.post(
            reverse("report_listing", args=[listing.pk]),
            {"reason": "unsafe", "details": "Packaging appears damaged."},
        )

        self.assertRedirects(response, reverse("discover"))
        from exchange.models import ListingReport

        report = ListingReport.objects.get(listing=listing)
        self.assertEqual(report.reported_by, self.member)
        self.assertEqual(report.status, ListingReport.Status.OPEN)

    def test_invalid_image_upload_does_not_create_listing(self):
        self.client.force_login(self.member)

        response = self.client.post(
            reverse("submit_listing"),
            {
                "name": "Image validation test",
                "batch_number": "B-102",
                "expiry_date": timezone.localdate() + timedelta(days=120),
                "quantity_available": 1,
                "prescription_required": "",
                "controlled_or_restricted": "",
                "safety_attestation": "on",
                "original_packaging": "on",
                "seal_intact": "on",
                "packaging_opened": "",
                "packaging_damaged": "",
                "stored_as_instructed": "on",
                "recall_status_confirmed": "on",
                "requires_cold_chain": "",
                "visible_damage": "",
                "city": "Pune",
                "pincode": "411001",
                "images": SimpleUploadedFile(
                    "not-really-an-image.png",
                    b"not an image",
                    content_type="image/png",
                ),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            MedicineListing.objects.filter(name="Image validation test").exists()
        )
        self.assertIn("images", response.context["form"].errors)
