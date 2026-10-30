from datetime import timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from medicines.models import MedicineListing

from .models import MedicineRequest, Notification, SavedMedicine
from .services import reserve_request


class RequestWorkflowTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner@example.com",
            email="owner@example.com",
            password="StrongPassphrase#2026",
            email_verified=True,
        )
        self.requester = User.objects.create_user(
            username="requester@example.com",
            email="requester@example.com",
            password="StrongPassphrase#2026",
            email_verified=True,
        )
        self.listing = MedicineListing.objects.create(
            owner=self.owner,
            name="Reviewed medicine",
            strength="10 mg",
            expiry_date=timezone.localdate() + timedelta(days=120),
            quantity_available=3,
            prescription_required=False,
            controlled_or_restricted=False,
            original_packaging=True,
            seal_intact=True,
            packaging_opened=False,
            packaging_damaged=False,
            stored_as_instructed=True,
            recall_status_confirmed=True,
            requires_cold_chain=False,
            visible_damage=False,
            city="Pune",
            pincode="411001",
            status=MedicineListing.Status.APPROVED,
        )

    @override_settings(MEDISHARE_REQUEST_WORKFLOWS_ENABLED=True)
    def test_member_request_is_persisted_and_listing_owner_notified(self):
        self.client.force_login(self.requester)

        response = self.client.post(
            reverse("listing_detail", args=[self.listing.pk]),
            {"quantity": 2, "note": "Please review", "request_medicine": "1"},
        )

        self.assertRedirects(response, reverse("my_requests"))
        medicine_request = MedicineRequest.objects.get()
        self.assertEqual(medicine_request.requester, self.requester)
        self.assertEqual(medicine_request.status, MedicineRequest.Status.PENDING_REVIEW)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.owner, title="A medicine request needs review"
            ).exists()
        )

    @override_settings(MEDISHARE_REQUEST_WORKFLOWS_ENABLED=False)
    def test_request_workflow_is_blocked_when_feature_flag_is_off(self):
        self.client.force_login(self.requester)

        response = self.client.post(
            reverse("listing_detail", args=[self.listing.pk]),
            {"quantity": 1, "request_medicine": "1"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(MedicineRequest.objects.exists())

    @override_settings(MEDISHARE_REQUEST_WORKFLOWS_ENABLED=True)
    def test_duplicate_active_request_is_rejected(self):
        self.client.force_login(self.requester)
        url = reverse("listing_detail", args=[self.listing.pk])
        payload = {"quantity": 1, "request_medicine": "1"}

        self.client.post(url, payload)
        self.client.post(url, payload)

        self.assertEqual(MedicineRequest.objects.filter(requester=self.requester).count(), 1)

    @override_settings(MEDISHARE_REQUEST_WORKFLOWS_ENABLED=True)
    def test_authorized_reviewer_reserves_inventory_atomically(self):
        reviewer = User.objects.create_user(
            username="reviewer@example.com",
            email="reviewer@example.com",
            password="StrongPassphrase#2026",
            is_staff=True,
            is_pharmacist_verified=True,
            role=User.Role.VERIFIER,
        )
        medicine_request = MedicineRequest.objects.create(
            requester=self.requester,
            listing=self.listing,
            quantity=2,
            status=MedicineRequest.Status.PENDING_REVIEW,
        )

        result = reserve_request(medicine_request.pk, reviewer)

        self.listing.refresh_from_db()
        self.assertEqual(result.status, MedicineRequest.Status.RESERVED)
        self.assertEqual(self.listing.quantity_available, 1)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.requester, title="Your request has been reserved"
            ).exists()
        )

    @override_settings(MEDISHARE_REQUEST_WORKFLOWS_ENABLED=True)
    def test_reservation_rejects_insufficient_quantity_without_changing_stock(self):
        reviewer = User.objects.create_user(
            username="reviewer@example.com",
            email="reviewer@example.com",
            password="StrongPassphrase#2026",
            is_staff=True,
            is_pharmacist_verified=True,
            role=User.Role.VERIFIER,
        )
        medicine_request = MedicineRequest.objects.create(
            requester=self.requester,
            listing=self.listing,
            quantity=5,
            status=MedicineRequest.Status.PENDING_REVIEW,
        )

        with self.assertRaisesMessage(ValueError, "not enough available quantity"):
            reserve_request(medicine_request.pk, reviewer)

        self.listing.refresh_from_db()
        medicine_request.refresh_from_db()
        self.assertEqual(self.listing.quantity_available, 3)
        self.assertEqual(medicine_request.status, MedicineRequest.Status.PENDING_REVIEW)

    def test_saved_listing_can_be_removed_after_it_becomes_unavailable(self):
        self.client.force_login(self.requester)
        SavedMedicine.objects.create(user=self.requester, listing=self.listing)
        self.listing.status = MedicineListing.Status.WITHDRAWN
        self.listing.save(update_fields=["status", "updated_at"])

        response = self.client.post(
            reverse("save_listing", args=[self.listing.pk]),
            {"next": "https://example.invalid/"},
        )

        self.assertRedirects(response, reverse("discover"))
        self.assertFalse(SavedMedicine.objects.filter(user=self.requester).exists())

    def test_owner_withdrawing_listing_cancels_pending_requests(self):
        medicine_request = MedicineRequest.objects.create(
            requester=self.requester,
            listing=self.listing,
            quantity=1,
            status=MedicineRequest.Status.PENDING_REVIEW,
        )
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse("withdraw_listing", args=[self.listing.pk])
        )

        self.assertRedirects(response, reverse("my_listings"))
        self.listing.refresh_from_db()
        medicine_request.refresh_from_db()
        self.assertEqual(self.listing.status, MedicineListing.Status.WITHDRAWN)
        self.assertEqual(medicine_request.status, MedicineRequest.Status.CANCELLED)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.requester,
                title="A listing you requested was withdrawn",
            ).exists()
        )

    def test_member_cancelling_request_notifies_listing_owner(self):
        medicine_request = MedicineRequest.objects.create(
            requester=self.requester,
            listing=self.listing,
            quantity=1,
            status=MedicineRequest.Status.PENDING_REVIEW,
        )
        self.client.force_login(self.requester)

        response = self.client.post(
            reverse("cancel_request", args=[medicine_request.pk])
        )

        self.assertRedirects(response, reverse("my_requests"))
        medicine_request.refresh_from_db()
        self.assertEqual(medicine_request.status, MedicineRequest.Status.CANCELLED)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.owner, title="A medicine request was cancelled"
            ).exists()
        )
