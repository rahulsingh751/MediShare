from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import TemplateView

from accounts.forms import EmailLoginForm
from . import views


urlpatterns = [
    path("", views.landing, name="landing"),
    path(
        "terms/",
        TemplateView.as_view(template_name="legal/terms.html"),
        name="terms",
    ),
    path(
        "privacy/",
        TemplateView.as_view(template_name="legal/privacy.html"),
        name="privacy",
    ),
    path("register/", views.register, name="register"),
    path("verify-email/resend/", views.resend_verification, name="resend_verification"),
    path("verify-email/<str:token>/", views.verify_email, name="verify_email"),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="accounts/login.html",
            authentication_form=EmailLoginForm,
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="accounts/password_reset.html",
            email_template_name="accounts/password_reset_email.txt",
        ),
        name="password_reset",
    ),
    path(
        "password-reset/sent/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="accounts/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "password-reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),
    path(
        "password-reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("discover/", views.discover, name="discover"),
    path("search-suggestions/", views.search_suggestions, name="search_suggestions"),
    path("medicines/submit/", views.submit_listing, name="submit_listing"),
    path("medicines/<int:pk>/", views.listing_detail, name="listing_detail"),
    path("medicines/<int:pk>/save/", views.save_listing, name="save_listing"),
    path("medicines/<int:pk>/report/", views.report_listing, name="report_listing"),
    path("my-listings/", views.my_listings, name="my_listings"),
    path("my-listings/<int:pk>/withdraw/", views.withdraw_listing, name="withdraw_listing"),
    path("my-requests/", views.my_requests, name="my_requests"),
    path("my-requests/<int:pk>/cancel/", views.cancel_request, name="cancel_request"),
    path("wishlist/", views.wishlist, name="wishlist"),
    path("notifications/", views.notifications, name="notifications"),
]
