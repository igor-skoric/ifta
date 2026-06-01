from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import EmailAuthenticationForm, RoleForm, UserCreateForm, UserThemeForm
from .models import EmailVerificationToken, Role, UserProfile


class EmailLoginView(LoginView):
    template_name = "registration/login.html"
    authentication_form = EmailAuthenticationForm

    def form_valid(self, form):
        user = form.get_user()
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if not profile.email_verified:
            messages.error(self.request, "Morate potvrditi email pre prijave.")
            return redirect("accounts:verification_required")
        if not profile.can_login:
            messages.error(self.request, "Vas nalog je deaktiviran.")
            return redirect("accounts:login")
        login(self.request, user)
        return redirect(self.get_success_url())


def verification_required(request):
    return render(request, "accounts/verification_required.html", {"hide_header_and_footer": True})


def verify_email(request, token):
    token_obj = get_object_or_404(EmailVerificationToken, token=token)
    if not token_obj.is_valid:
        messages.error(request, "Link za potvrdu email-a vise nije vazeci.")
        return redirect("accounts:login")
    profile, _ = UserProfile.objects.get_or_create(user=token_obj.user)
    profile.email_verified = True
    profile.save(update_fields=["email_verified", "updated_at"])
    from django.utils import timezone

    token_obj.consumed_at = timezone.now()
    token_obj.save(update_fields=["consumed_at"])
    messages.success(request, "Email je uspesno potvrden. Sada mozete da se prijavite.")
    return redirect("accounts:login")


@login_required
def resend_verification(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if profile.email_verified:
        messages.info(request, "Email je vec potvrden.")
        return redirect("ifta:home")
    token = EmailVerificationToken.create_for_user(request.user)
    verification_link = request.build_absolute_uri(reverse("accounts:verify_email", args=[str(token.token)]))
    send_mail(
        subject="Potvrda email adrese",
        message=f"Potvrdite vas nalog: {verification_link}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[request.user.email],
        fail_silently=False,
    )
    messages.success(request, "Poslali smo novi link za verifikaciju.")
    return redirect("accounts:verification_required")


@login_required
def user_settings(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = UserThemeForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Settings saved.")
            return redirect("accounts:user_settings")
    else:
        form = UserThemeForm(instance=profile)
    return render(
        request,
        "accounts/user_settings.html",
        {"form": form, "hide_header_and_footer": False},
    )


def _is_super_admin(user):
    return user.is_authenticated and user.is_superuser


@user_passes_test(_is_super_admin)
def admin_dashboard(request):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    users = User.objects.all().select_related("profile").prefetch_related("role_assignments__role")
    roles = Role.objects.all()
    return render(request, "accounts/admin/dashboard.html", {"users": users, "roles": roles, "hide_header_and_footer": False})


@user_passes_test(_is_super_admin)
def admin_users_create(request):
    form = UserCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        token = EmailVerificationToken.create_for_user(user)
        verification_link = request.build_absolute_uri(reverse("accounts:verify_email", args=[str(token.token)]))
        if user.email:
            send_mail(
                subject="Aktivirajte nalog",
                message=f"Kliknite da verifikujete email: {verification_link}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        messages.success(request, "Nalog je kreiran i poslat je verifikacioni email.")
        return redirect("accounts:admin_dashboard")
    return render(request, "accounts/admin/user_form.html", {"form": form, "hide_header_and_footer": False})


@user_passes_test(_is_super_admin)
def admin_roles_list(request):
    roles = Role.objects.prefetch_related("permissions", "allowed_departments").all()
    return render(request, "accounts/admin/role_list.html", {"roles": roles, "hide_header_and_footer": False})


@user_passes_test(_is_super_admin)
def admin_roles_create(request):
    form = RoleForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Rola je uspesno kreirana.")
        return redirect("accounts:admin_roles")
    return render(request, "accounts/admin/role_form.html", {"form": form, "is_edit": False, "hide_header_and_footer": False})


@user_passes_test(_is_super_admin)
def admin_roles_edit(request, pk):
    role = get_object_or_404(Role, pk=pk)
    initial = {"permission_codes": list(role.permissions.values_list("code", flat=True))}
    form = RoleForm(request.POST or None, instance=role, initial=initial)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Rola je uspesno izmenjena.")
        return redirect("accounts:admin_roles")
    return render(
        request,
        "accounts/admin/role_form.html",
        {"form": form, "is_edit": True, "role": role, "hide_header_and_footer": False},
    )

