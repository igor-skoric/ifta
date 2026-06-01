from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.utils.text import slugify

from office.models import Department

from .constants import PERMISSION_CHOICES
from .models import Role, RolePermission, UserProfile, UserRole


class UserThemeForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ("ui_theme",)
        labels = {"ui_theme": "Tema aplikacije"}
        widgets = {
            "ui_theme": forms.RadioSelect,
        }


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={"autofocus": True}))


class UserCreateForm(forms.Form):
    email = forms.EmailField()
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    password = forms.CharField(widget=forms.PasswordInput)
    department = forms.ModelChoiceField(queryset=Department.objects.filter(is_active=True), required=False)
    is_staff = forms.BooleanField(required=False)
    is_superuser = forms.BooleanField(required=False)
    role_ids = forms.ModelMultipleChoiceField(queryset=Role.objects.all(), required=False)

    def save(self):
        User = get_user_model()
        email = self.cleaned_data["email"].strip().lower()
        user = User.objects.create_user(
            username=email,
            email=email,
            password=self.cleaned_data["password"],
            first_name=self.cleaned_data.get("first_name", ""),
            last_name=self.cleaned_data.get("last_name", ""),
            is_staff=self.cleaned_data.get("is_staff", False),
            is_superuser=self.cleaned_data.get("is_superuser", False),
        )
        UserProfile.objects.update_or_create(
            user=user,
            defaults={"department": self.cleaned_data.get("department"), "email_verified": False, "can_login": True},
        )
        selected_roles = self.cleaned_data.get("role_ids")
        if selected_roles:
            UserRole.objects.bulk_create([UserRole(user=user, role=role) for role in selected_roles], ignore_conflicts=True)
        return user


class RoleForm(forms.ModelForm):
    permission_codes = forms.MultipleChoiceField(
        choices=PERMISSION_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    allowed_departments = forms.ModelMultipleChoiceField(
        queryset=Department.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Role
        fields = ["name", "slug", "description", "allowed_departments"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["allowed_departments"].queryset = Department.objects.filter(is_active=True).order_by("sort_order", "name")

    def clean_slug(self):
        slug = self.cleaned_data.get("slug", "").strip()
        name = self.cleaned_data.get("name", "").strip()
        return slug or slugify(name)

    def save(self, commit=True):
        role = super().save(commit=commit)
        selected_codes = self.cleaned_data.get("permission_codes", [])
        role.permissions.exclude(code__in=selected_codes).delete()
        existing = set(role.permissions.values_list("code", flat=True))
        for code in selected_codes:
            if code not in existing:
                RolePermission.objects.create(role=role, code=code)
        return role

