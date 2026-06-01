import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class UserProfile(models.Model):
    class UiTheme(models.TextChoices):
        DARK = "dark", "Noćni (tamni)"
        LIGHT = "light", "Dnevni (svetli)"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    department = models.ForeignKey(
        "office.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="member_profiles",
    )
    email_verified = models.BooleanField(default=False)
    can_login = models.BooleanField(default=True)
    ui_theme = models.CharField(
        max_length=16,
        choices=UiTheme.choices,
        default=UiTheme.DARK,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} profile"


class Role(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True, default="")
    is_system = models.BooleanField(default=False)
    allowed_departments = models.ManyToManyField(
        "office.Department",
        blank=True,
        related_name="roles",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class RolePermission(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="permissions")
    code = models.CharField(max_length=120)

    class Meta:
        unique_together = ("role", "code")
        ordering = ["code"]

    def __str__(self):
        return f"{self.role.slug}:{self.code}"


class UserRole(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="role_assignments")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="user_assignments")
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="granted_roles",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "role")
        ordering = ["user_id", "role__name"]

    def __str__(self):
        return f"{self.user.username} -> {self.role.slug}"


class EmailVerificationToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="email_tokens")
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @classmethod
    def create_for_user(cls, user, hours_valid=24):
        return cls.objects.create(
            user=user,
            expires_at=timezone.now() + timedelta(hours=hours_valid),
        )

    @property
    def is_valid(self):
        return self.consumed_at is None and self.expires_at >= timezone.now()
