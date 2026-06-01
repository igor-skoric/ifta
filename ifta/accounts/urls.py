from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("settings/", views.user_settings, name="user_settings"),
    path("login/", views.EmailLoginView.as_view(), name="login"),
    path("verification-required/", views.verification_required, name="verification_required"),
    path("verify/<uuid:token>/", views.verify_email, name="verify_email"),
    path("resend-verification/", views.resend_verification, name="resend_verification"),
    path("admin-panel/", views.admin_dashboard, name="admin_dashboard"),
    path("admin-panel/users/new/", views.admin_users_create, name="admin_users_create"),
    path("admin-panel/roles/", views.admin_roles_list, name="admin_roles"),
    path("admin-panel/roles/new/", views.admin_roles_create, name="admin_roles_create"),
    path("admin-panel/roles/<int:pk>/edit/", views.admin_roles_edit, name="admin_roles_edit"),
]

