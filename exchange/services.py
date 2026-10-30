from django.db import transaction
from django.db.models import F
from django.conf import settings

from medicines.models import MedicineListing

from .models import MedicineRequest, Notification


@transaction.atomic
def reserve_request(request_id, reviewer):
    if not settings.MEDISHARE_REQUEST_WORKFLOWS_ENABLED:
        raise ValueError(
            "Request reservations are disabled until legal and professional review is complete."
        )
    if not reviewer.is_superuser and not (
        reviewer.is_staff and reviewer.is_pharmacist_verified
    ):
        raise PermissionError("Only an authorized medical reviewer can reserve a request.")
    listing_id = MedicineRequest.objects.only("listing_id").get(pk=request_id).listing_id
    listing = MedicineListing.objects.select_for_update().get(pk=listing_id)
    request = (
        MedicineRequest.objects.select_for_update()
        .select_related("requester")
        .get(pk=request_id)
    )
    if request.status not in {
        MedicineRequest.Status.PENDING_REVIEW,
        MedicineRequest.Status.SUBMITTED,
    }:
        raise ValueError("Only requests awaiting review can be approved.")
    if listing.status != MedicineListing.Status.APPROVED or not listing.is_eligible_for_review:
        raise ValueError("The listing is no longer approved and eligible.")
    if request.quantity > listing.quantity_available:
        raise ValueError("There is not enough available quantity for this request.")

    updated = MedicineListing.objects.filter(
        pk=listing.pk,
        status=MedicineListing.Status.APPROVED,
        quantity_available__gte=request.quantity,
    ).update(quantity_available=F("quantity_available") - request.quantity)
    if not updated:
        raise ValueError("The available quantity changed. Review the request again.")

    listing.refresh_from_db()
    if listing.quantity_available == 0:
        listing.status = MedicineListing.Status.RESERVED
        listing.save(update_fields=["status", "updated_at"])
    request.status = MedicineRequest.Status.RESERVED
    request.save(update_fields=["status", "updated_at"])
    Notification.objects.create(
        recipient=request.requester,
        title="Your request has been reserved",
        body=f"A reviewer reserved {request.quantity} unit(s) of {listing.name}. "
        "Handover details must still be coordinated through an authorized channel.",
        url="/my-requests/",
    )
    Notification.objects.create(
        recipient=listing.owner,
        title="A request was reserved",
        body=f"A reviewer reserved {request.quantity} unit(s) of {listing.name}. "
        "Coordinate only through an authorized, legally permitted channel.",
        url="/my-requests/",
    )
    return request


@transaction.atomic
def reject_request(request_id, reviewer):
    if not reviewer.is_superuser and not (
        reviewer.is_staff and reviewer.is_pharmacist_verified
    ):
        raise PermissionError("Only an authorized medical reviewer can reject a request.")
    listing_id = MedicineRequest.objects.only("listing_id").get(pk=request_id).listing_id
    MedicineListing.objects.select_for_update().get(pk=listing_id)
    request = (
        MedicineRequest.objects.select_for_update()
        .select_related("requester", "listing")
        .get(pk=request_id)
    )
    if request.status not in {
        MedicineRequest.Status.PENDING_REVIEW,
        MedicineRequest.Status.SUBMITTED,
    }:
        raise ValueError("Only requests awaiting review can be rejected.")
    request.status = MedicineRequest.Status.REJECTED
    request.save(update_fields=["status", "updated_at"])
    Notification.objects.create(
        recipient=request.requester,
        title="Your medicine request was reviewed",
        body=f"Your request for {request.listing.name} was not approved.",
        url="/my-requests/",
    )
    return request
