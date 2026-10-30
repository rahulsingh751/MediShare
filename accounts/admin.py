from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = (
        "email",
        "first_name",
        "last_name",
        "role",
        "email_verified",
        "is_pharmacist_verified",
        "is_staff",
    )
    list_filter = ("role", "email_verified", "is_pharmacist_verified", "is_staff")
    search_fields = ("email", "first_name", "last_name", "mobile")
    ordering = ("email",)
    fieldsets = DjangoUserAdmin.fieldsets + (
        (
            "MediShare profile",
            {
                "fields": (
                    "mobile",
                    "city",
                    "state",
                    "pincode",
                    "role",
                    "email_verified",
                    "is_pharmacist_verified",
                    "accepted_terms_at",
                )
            },
        ),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        (
            "MediShare profile",
            {"fields": ("email", "role", "mobile", "city", "state", "pincode")},
        ),
    )

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if request.user.is_superuser:
            return fieldsets
        filtered = []
        for title, options in fieldsets:
            fields = tuple(
                field
                for field in options.get("fields", ())
                if field
                not in {
                    "role",
                    "is_pharmacist_verified",
                    "email_verified",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                }
            )
            filtered.append((title, {**options, "fields": fields}))
        return filtered

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            readonly.extend(
                [
                    "role",
                    "is_pharmacist_verified",
                    "email_verified",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ]
            )
        return readonly
