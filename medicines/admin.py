from django.contrib import admin, messages

from exchange.models import Notification

from .models import MedicineImage, MedicineListing


class MedicineImageInline(admin.TabularInline):
    model = MedicineImage
    extra = 0
    readonly_fields = ("uploaded_at",)


@admin.register(MedicineListing)
class MedicineListingAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "brand_name",
        "owner",
        "city",
        "expiry_date",
        "quantity_available",
        "status",
        "created_at",
    )
    list_filter = (
        "status",
        "city",
        "prescription_required",
        "controlled_or_restricted",
        "recall_status_confirmed",
    )
    search_fields = ("name", "brand_name", "generic_name", "batch_number", "owner__email")
    readonly_fields = ("owner", "created_at", "updated_at", "status")
    inlines = [MedicineImageInline]
    actions = ("mark_under_review", "approve_eligible_listings", "reject_listings")

    def has_module_permission(self, request):
        return request.user.is_superuser or (
            request.user.is_staff and request.user.is_pharmacist_verified
        )

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_change_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    @admin.action(description="Approve eligible selected listings")
    def approve_eligible_listings(self, request, queryset):
        approved = 0
        for listing in queryset:
            if listing.is_eligible_for_review and listing.status in {
                MedicineListing.Status.SUBMITTED,
                MedicineListing.Status.UNDER_REVIEW,
            }:
                listing.status = MedicineListing.Status.APPROVED
                listing.reviewer_notes = ""
                listing.save(update_fields=["status", "reviewer_notes", "updated_at"])
                Notification.objects.create(
                    recipient=listing.owner,
                    title="Your medicine submission was reviewed",
                    body=f"{listing.name} was approved for eligible listing discovery. "
                    "This is not a guarantee of safety or legal transfer authority.",
                    url="/my-listings/",
                )
                approved += 1
        self.message_user(
            request,
            f"{approved} eligible listing(s) approved. Approval does not establish legal transfer authority.",
            level=messages.SUCCESS if approved else messages.WARNING,
        )

    @admin.action(description="Reject selected listings")
    def reject_listings(self, request, queryset):
        selected = queryset.filter(
            status__in=[
                MedicineListing.Status.SUBMITTED,
                MedicineListing.Status.UNDER_REVIEW,
                MedicineListing.Status.RESTRICTED,
            ]
        )
        for listing in selected:
            listing.status = MedicineListing.Status.REJECTED
            listing.save(update_fields=["status", "updated_at"])
            Notification.objects.create(
                recipient=listing.owner,
                title="Your medicine submission was reviewed",
                body=f"{listing.name} was not approved for discovery.",
                url="/my-listings/",
            )
        self.message_user(request, f"{selected.count()} listing(s) rejected.")

    @admin.action(description="Mark selected submissions under review")
    def mark_under_review(self, request, queryset):
        updated = queryset.filter(status=MedicineListing.Status.SUBMITTED).update(
            status=MedicineListing.Status.UNDER_REVIEW
        )
        self.message_user(request, f"{updated} submission(s) marked under review.")
