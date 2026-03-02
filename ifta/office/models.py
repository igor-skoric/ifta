# app/models.py
from django.db import models
from django.utils import timezone


class Seat(models.Model):
    svg_id = models.CharField(max_length=120, unique=True)
    dept = models.CharField(max_length=20, blank=True, default="")
    zone = models.CharField(max_length=20, blank=True, default="")
    seat_no = models.CharField(max_length=20, blank=True, default="")
    label = models.CharField(max_length=50, blank=True, default="")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.svg_id


class Employee(models.Model):
    alias = models.CharField(max_length=50, unique=True)  # npr. "user0a" / "igor" / "dispatch01"
    name = models.CharField(max_length=80, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=30, blank=True, default="")

    company_name = models.CharField(max_length=80, blank=True, default="")
    company_phone = models.CharField(max_length=30, blank=True, default="")
    company_email = models.EmailField(blank=True, default="")

    is_active = models.BooleanField(default=False)

    def __str__(self):
        name = f"{self.name} {self.email}".strip()
        return f"{name} ({self.alias})" if self.alias else name


class Asset(models.Model):
    class AssetType(models.TextChoices):
        LAPTOP = "LAPTOP", "Laptop"
        DESKTOP = "DESKTOP", "Desktop/PC"
        MONITOR = "MONITOR", "Monitor"
        HEADSET = "HEADSET", "Headset"
        KEYBOARD = "KEYBOARD", "Keyboard"
        MOUSE = "MOUSE", "Mouse"
        DOCK = "DOCK", "Dock/Hub"
        PHONE = "PHONE", "Phone"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        IN_USE = "IN_USE", "In use"
        IN_STOCK = "IN_STOCK", "In stock"
        BROKEN = "BROKEN", "Broken"
        LOST = "LOST", "Lost"
        RETIRED = "RETIRED", "Retired"
        PRIVATE = "PRIVATE", "Private"

    asset_type = models.CharField(max_length=20, choices=AssetType.choices)
    brand = models.CharField(max_length=80, blank=True, default="")
    model = models.CharField(max_length=80, blank=True, default="")
    serial_number = models.CharField(max_length=80, blank=True, default="")
    inventory_tag = models.CharField(max_length=50, blank=True, default="")  # nalepnica/asset tag
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_USE)
    notes = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        core = f"{self.get_asset_type_display()}"
        extra = " ".join([x for x in [self.brand, self.model] if x]).strip()
        sn = f"SN:{self.serial_number}" if self.serial_number else ""
        return " ".join([x for x in [core, extra, sn] if x])


class AssetAssignment(models.Model):
    """
    Ko trenutno zadužuje opremu.
    end_at = NULL => aktivno zaduženje.
    """
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="assignments")
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="asset_assignments")

    start_at = models.DateTimeField(default=timezone.now)
    end_at = models.DateTimeField(null=True, blank=True)

    assigned_by = models.CharField(max_length=80, blank=True, default="")  # ko je zadužio (opciono)
    note = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["employee", "end_at"]),
            models.Index(fields=["asset", "end_at"]),
        ]

    def __str__(self):
        return f"{self.asset} -> {self.employee}"


class SeatAssignment(models.Model):
    seat = models.ForeignKey(Seat, on_delete=models.PROTECT, related_name="assignments")
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="seat_assignments")

    start_at = models.DateTimeField(default=timezone.now)
    end_at = models.DateTimeField(null=True, blank=True)

    note = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["seat"],
                condition=models.Q(end_at__isnull=True),
                name="uniq_active_seat_assignment_per_seat",
            )
        ]

    def __str__(self):
        return f"{self.employee} @ {self.seat}"
