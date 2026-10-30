from django.contrib import admin, messages

from .models import ListingReport, MedicineRequest, Notification, SavedMedicine
from .services import reject_request, reserve_request


@admin.register(MedicineRequest)
class MedicineRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "listing", "requester", "quantity", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("listing__name", "requester__email", "listing__owner__email")
    readonly_fields = (
        "requester",
        "listing",
        "quantity",
        "note",
        "status",
        "created_at",
        "updated_at",
    )
    actions = ("reserve_selected_requests", "reject_selected_requests")

    def has_module_permission(self, request):
        return request.user.is_superuser or (
            request.user.is_staff and request.user.is_pharmacist_verified
        )

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_change_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    @admin.action(description="Approve and reserve selected requests")
    def reserve_selected_requests(self, request, queryset):
        reserved = 0
        for medicine_request in queryset:
            try:
                reserve_request(medicine_request.pk, request.user)
            except (PermissionError, ValueError) as error:
                self.message_user(
                    request,
                    f"Request #{medicine_request.pk}: {error}",
                    level=messages.WARNING,
                )
            else:
                reserved += 1
        if reserved:
            self.message_user(request, f"{reserved} request(s) reserved.")

    @admin.action(description="Reject selected pending requests")
    def reject_selected_requests(self, request, queryset):
        rejected = 0
        for medicine_request in queryset:
            try:
                reject_request(medicine_request.pk, request.user)
            except (PermissionError, ValueError) as error:
                self.message_user(
                    request,
                    f"Request #{medicine_request.pk}: {error}",
                    level=messages.WARNING,
                )
            else:
                rejected += 1
        self.message_user(request, f"{rejected} request(s) rejected.")


@admin.register(ListingReport)
class ListingReportAdmin(admin.ModelAdmin):
    list_display = ("id", "listing", "reported_by", "reason", "status", "created_at")
    list_filter = ("status", "reason")
    search_fields = ("listing__name", "reported_by__email", "details")
    readonly_fields = ("reported_by", "listing", "reason", "details", "created_at")

    def has_module_permission(self, request):
        return request.user.is_staff

    def has_add_permission(self, request):
        return False


admin.site.register(SavedMedicine)
admin.site.register(Notification)
