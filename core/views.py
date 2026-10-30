from django.contrib import messages
from django.db import IntegrityError, transaction
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core import signing
from django.utils.http import url_has_allowed_host_and_scheme
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import User
from accounts.forms import RegistrationForm
from accounts.services import EMAIL_VERIFICATION_SALT, send_verification_email
from exchange.forms import ListingReportForm, MedicineRequestForm
from exchange.models import ListingReport, MedicineRequest, Notification, SavedMedicine
from medicines.forms import MedicineListingForm
from medicines.models import MedicineListing
from medicines.services import publicly_discoverable_listings

from .decorators import verified_email_required


def landing(request):
    return render(request, "landing.html")


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        user.accepted_terms_at = timezone.now()
        user.save(update_fields=["accepted_terms_at"])
        send_verification_email(user, request)
        messages.success(
            request,
            "Account created. Check your email for a verification link before continuing.",
        )
        return redirect("login")
    return render(request, "accounts/register.html", {"form": form})


def verify_email(request, token):
    try:
        payload = signing.loads(
            token,
            salt=EMAIL_VERIFICATION_SALT,
            max_age=settings.EMAIL_VERIFICATION_MAX_AGE,
        )
        user = User.objects.get(pk=payload["user_id"])
    except (signing.BadSignature, signing.SignatureExpired, User.DoesNotExist, KeyError):
        messages.error(request, "That verification link is invalid or has expired.")
        return redirect("login")
    if not user.email_verified:
        user.email_verified = True
        user.save(update_fields=["email_verified"])
    messages.success(request, "Email verified. You can now sign in.")
    return redirect("login")


@login_required
def dashboard(request):
    user = request.user
    listings = MedicineListing.objects.filter(owner=user)
    requests = MedicineRequest.objects.filter(requester=user)
    context = {
        "listing_count": listings.count(),
        "active_listing_count": listings.filter(
            status__in=[
                MedicineListing.Status.SUBMITTED,
                MedicineListing.Status.UNDER_REVIEW,
                MedicineListing.Status.APPROVED,
            ]
        ).count(),
        "pending_listing_count": listings.filter(
            status__in=[
                MedicineListing.Status.SUBMITTED,
                MedicineListing.Status.UNDER_REVIEW,
            ]
        ).count(),
        "requests_received_count": MedicineRequest.objects.filter(
            listing__owner=user
        ).count(),
        "requests_submitted_count": requests.count(),
        "completed_count": requests.filter(status=MedicineRequest.Status.COMPLETED).count()
        + MedicineRequest.objects.filter(
            listing__owner=user, status=MedicineRequest.Status.COMPLETED
        ).count(),
        "recent_listings": listings[:4],
        "recent_requests": requests.select_related("listing")[:4],
    }
    return render(request, "dashboard.html", context)


@verified_email_required
def discover(request):
    listings = publicly_discoverable_listings().select_related("owner").prefetch_related("images")

    query = request.GET.get("q", "").strip()
    city = request.GET.get("city", "").strip()
    pincode = request.GET.get("pincode", "").strip()
    if query:
        listings = listings.filter(
            Q(name__icontains=query)
            | Q(brand_name__icontains=query)
            | Q(generic_name__icontains=query)
            | Q(active_ingredient__icontains=query)
            | Q(composition__icontains=query)
            | Q(strength__icontains=query)
            | Q(dosage_form__icontains=query)
            | Q(manufacturer__icontains=query)
        )
    if city:
        listings = listings.filter(city__icontains=city)
    if pincode:
        listings = listings.filter(pincode__icontains=pincode)
    saved_ids = set(
        SavedMedicine.objects.filter(user=request.user).values_list("listing_id", flat=True)
    )
    return render(
        request,
        "medicines/discover.html",
        {
            "listings": listings[:100],
            "query": query,
            "city": city,
            "pincode": pincode,
            "saved_ids": saved_ids,
            "result_count": listings.count(),
        },
    )


@login_required
@verified_email_required
def search_suggestions(request):
    query = request.GET.get("q", "").strip()
    if len(query) < 2:
        return JsonResponse({"suggestions": []})
    listings = publicly_discoverable_listings().filter(
        Q(name__icontains=query)
        | Q(brand_name__icontains=query)
        | Q(generic_name__icontains=query)
        | Q(active_ingredient__icontains=query)
    )
    suggestions = list(listings.values_list("name", "brand_name", "strength").distinct()[:8])
    return JsonResponse(
        {
            "suggestions": [
                {
                    "label": " · ".join(part for part in item if part),
                    "query": item[0],
                }
                for item in suggestions
            ]
        }
    )


@verified_email_required
def submit_listing(request):
    form = MedicineListingForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        listing = form.save(owner=request.user)
        if listing.status == MedicineListing.Status.RESTRICTED:
            messages.warning(
                request,
                "This submission was restricted from discovery based on the information "
                "provided. It cannot be requested or redistributed.",
            )
        else:
            messages.success(
                request,
                "Submission received. It remains hidden while an authorized reviewer assesses it.",
            )
        return redirect("dashboard")
    return render(request, "medicines/submit.html", {"form": form})


@verified_email_required
def listing_detail(request, pk):
    listing = get_object_or_404(
        publicly_discoverable_listings()
        .select_related("owner")
        .prefetch_related("images"),
        pk=pk,
    )
    form = MedicineRequestForm(request.POST or None)
    saved = SavedMedicine.objects.filter(user=request.user, listing=listing).exists()
    if request.method == "POST" and "request_medicine" in request.POST:
        if not settings.MEDISHARE_REQUEST_WORKFLOWS_ENABLED:
            messages.error(
                request,
                "Medicine request workflows are disabled until the applicable legal and "
                "professional review is complete.",
            )
        elif listing.owner_id == request.user.id:
            messages.error(request, "You cannot request your own listing.")
        elif form.is_valid() and form.cleaned_data["quantity"] > listing.quantity_available:
            form.add_error("quantity", "That quantity is no longer available.")
        elif form.is_valid():
            medicine_request = form.save(commit=False)
            medicine_request.requester = request.user
            medicine_request.listing = listing
            medicine_request.status = MedicineRequest.Status.PENDING_REVIEW
            try:
                with transaction.atomic():
                    locked_listing = MedicineListing.objects.select_for_update().get(
                        pk=listing.pk
                    )
                    if (
                        locked_listing.status != MedicineListing.Status.APPROVED
                        or not locked_listing.is_eligible_for_review
                        or medicine_request.quantity > locked_listing.quantity_available
                    ):
                        raise ValueError(
                            "The listing changed and is no longer available for that request."
                        )
                    medicine_request.listing = locked_listing
                    medicine_request.save()
            except IntegrityError:
                messages.warning(request, "You already have an active request for this listing.")
            except ValueError as error:
                messages.error(request, str(error))
            else:
                Notification.objects.create(
                    recipient=listing.owner,
                    title="A medicine request needs review",
                    body=f"{request.user.get_full_name() or request.user.email} requested "
                    f"{medicine_request.quantity} unit(s) of {listing.name}.",
                    url=reverse("my_requests"),
                )
                messages.success(
                    request,
                    "Request submitted for review. It is not a reservation or authorization to transfer.",
                )
                return redirect("my_requests")
    return render(
        request,
        "medicines/detail.html",
        {"listing": listing, "form": form, "saved": saved},
    )


@verified_email_required
def my_listings(request):
    listings = MedicineListing.objects.filter(owner=request.user).prefetch_related("images")
    return render(request, "medicines/my_listings.html", {"listings": listings})


@verified_email_required
@require_POST
def withdraw_listing(request, pk):
    get_object_or_404(MedicineListing.objects.only("pk"), pk=pk, owner=request.user)
    with transaction.atomic():
        listing = get_object_or_404(
            MedicineListing.objects.select_for_update(), pk=pk, owner=request.user
        )
        locked_requests = list(
            MedicineRequest.objects.select_for_update()
            .filter(listing_id=pk)
            .select_related("requester")
            .order_by("pk")
        )
        if listing.status not in {
            MedicineListing.Status.DRAFT,
            MedicineListing.Status.SUBMITTED,
            MedicineListing.Status.UNDER_REVIEW,
            MedicineListing.Status.REJECTED,
            MedicineListing.Status.RESTRICTED,
            MedicineListing.Status.APPROVED,
        }:
            messages.error(request, "This listing can no longer be withdrawn.")
        elif any(
            medicine_request.status
            in {
                MedicineRequest.Status.APPROVED,
                MedicineRequest.Status.RESERVED,
                MedicineRequest.Status.HANDOVER_SCHEDULED,
            }
            for medicine_request in locked_requests
        ):
            messages.error(
                request, "This listing has a reserved request and cannot be withdrawn."
            )
        else:
            for medicine_request in locked_requests:
                if medicine_request.status not in {
                    MedicineRequest.Status.SUBMITTED,
                    MedicineRequest.Status.PENDING_REVIEW,
                }:
                    continue
                medicine_request.status = MedicineRequest.Status.CANCELLED
                medicine_request.save(update_fields=["status", "updated_at"])
                Notification.objects.create(
                    recipient=medicine_request.requester,
                    title="A listing you requested was withdrawn",
                    body=f"{listing.name} was withdrawn by its owner. No reservation or transfer occurred.",
                    url="/my-requests/",
                )
            listing.status = MedicineListing.Status.WITHDRAWN
            listing.save(update_fields=["status", "updated_at"])
            messages.success(request, "Listing withdrawn.")
    return redirect("my_listings")


@verified_email_required
def my_requests(request):
    received = MedicineRequest.objects.filter(listing__owner=request.user).select_related(
        "listing", "requester"
    )
    submitted = MedicineRequest.objects.filter(requester=request.user).select_related(
        "listing", "listing__owner"
    )
    return render(
        request, "exchange/my_requests.html", {"received": received, "submitted": submitted}
    )


@verified_email_required
@require_POST
def save_listing(request, pk):
    saved = SavedMedicine.objects.filter(user=request.user, listing_id=pk).first()
    if saved:
        saved.delete()
        messages.info(request, "Removed from your saved medicines.")
    else:
        listing = get_object_or_404(publicly_discoverable_listings(), pk=pk)
        SavedMedicine.objects.create(user=request.user, listing=listing)
        messages.success(request, "Saved to your medicines list.")
    next_url = request.POST.get("next", "")
    if url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(next_url)
    return redirect("discover")


@verified_email_required
def wishlist(request):
    saved = SavedMedicine.objects.filter(user=request.user).select_related("listing")
    return render(request, "exchange/wishlist.html", {"saved_medicines": saved})


@verified_email_required
def notifications(request):
    notifications_list = request.user.notifications.all()
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return render(
        request, "exchange/notifications.html", {"notifications": notifications_list}
    )


@verified_email_required
@require_POST
def cancel_request(request, pk):
    with transaction.atomic():
        listing_id = get_object_or_404(
            MedicineRequest.objects.filter(requester=request.user).only("listing_id"),
            pk=pk,
        ).listing_id
        listing = MedicineListing.objects.select_for_update().get(pk=listing_id)
        medicine_request = get_object_or_404(
            MedicineRequest.objects.select_for_update(),
            pk=pk,
            requester=request.user,
            status__in=[
                MedicineRequest.Status.SUBMITTED,
                MedicineRequest.Status.PENDING_REVIEW,
            ],
        )
        medicine_request.status = MedicineRequest.Status.CANCELLED
        medicine_request.save(update_fields=["status", "updated_at"])
        Notification.objects.create(
            recipient=listing.owner,
            title="A medicine request was cancelled",
            body=f"A member cancelled their request for {medicine_request.listing.name}.",
            url="/my-requests/",
        )
    messages.success(request, "Request cancelled.")
    return redirect("my_requests")


@verified_email_required
def report_listing(request, pk):
    listing = get_object_or_404(MedicineListing, pk=pk)
    form = ListingReportForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ListingReport.objects.create(
            reported_by=request.user,
            listing=listing,
            reason=form.cleaned_data["reason"],
            details=form.cleaned_data["details"],
        )
        messages.success(
            request,
            "Thanks. The concern has been added to the administrator review queue.",
        )
        return redirect("discover")
    return render(
        request, "medicines/report.html", {"form": form, "listing": listing}
    )


@login_required
@require_POST
def resend_verification(request):
    if request.user.email_verified:
        messages.info(request, "Your email is already verified.")
    else:
        send_verification_email(request.user, request)
        messages.success(request, "A new verification email has been sent.")
    return redirect("dashboard")
