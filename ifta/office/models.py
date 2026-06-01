# app/models.py
from django.conf import settings
from django.db import models


class Department(models.Model):
    """Firma departmani — dodaju se kroz admin ili migracije, bez hardkodiranih choices."""

    code = models.SlugField(max_length=64, unique=True)
    name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class OfficeDirectoryEmployee(models.Model):
    class LoginType(models.TextChoices):
        COMPANY = "company", "Company"
        NATIVE = "native", "Native"
        CONTRACTOR = "contractor", "Contractor"
        OTHER = "other", "Other"

    employee_id = models.CharField(max_length=12, unique=True, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    work_email = models.EmailField(blank=True, null=True)
    private_email = models.EmailField(blank=True, null=True)
    work_phone = models.CharField(max_length=30, blank=True, null=True)
    private_phone = models.CharField(max_length=30, blank=True, null=True)
    login_type = models.CharField(max_length=20, choices=LoginType.choices, default=LoginType.COMPANY)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees",
    )
    location = models.CharField(max_length=120, blank=True)
    position = models.CharField(max_length=80, blank=True)
    is_active = models.BooleanField(default=True)
    is_dispatcher = models.BooleanField(
        default=False,
        help_text="If true, appears on Dispatch load planner and can own driver rows.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        db_table = "app_employee"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and not self.employee_id:
            self.employee_id = f"EMP{self.pk:05d}"
            type(self).objects.filter(pk=self.pk).update(employee_id=self.employee_id)

    def __str__(self):
        return f"{self.employee_id} - {self.first_name} {self.last_name}"


class OfficeEquipmentItem(models.Model):
    class EquipmentType(models.TextChoices):
        COMPUTER = "computer", "Computer"
        MONITOR = "monitor", "Monitor"
        LAPTOP = "laptop", "Laptop"
        PRINTER = "printer", "Printer"
        ROUTER = "router", "Router"
        TV = "tv", "Television"
        OTHER = "other", "Other"

    class ItemState(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        IN_SERVICE = "in_service", "In service"
        BROKEN = "broken", "Broken"
        MAINTENANCE = "maintenance", "Maintenance"
        RETIRED = "retired", "Retired"

    asset_id = models.CharField(max_length=40, unique=True)
    equipment_type = models.CharField(max_length=20, choices=EquipmentType.choices, default=EquipmentType.COMPUTER)
    brand_model = models.CharField(max_length=140, blank=True)
    serial_number = models.CharField(max_length=120, blank=True)
    state = models.CharField(max_length=20, choices=ItemState.choices, default=ItemState.DRAFT)
    notes = models.TextField(blank=True)
    assigned_employee = models.ForeignKey(
        OfficeDirectoryEmployee,
        on_delete=models.SET_NULL,
        related_name="equipment_items",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["asset_id"]
        db_table = "app_equipmentitem"

    def save(self, *args, **kwargs):
        if self.assigned_employee_id is None:
            self.state = self.ItemState.DRAFT
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.asset_id} ({self.get_equipment_type_display()})"


class OfficeEquipmentItemNote(models.Model):
    """Hronološki zapis beleški za jednu stavku inventara (pored polja notes na samoj stavci)."""

    item = models.ForeignKey(
        OfficeEquipmentItem,
        on_delete=models.CASCADE,
        related_name="note_entries",
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="equipment_item_notes",
    )

    class Meta:
        ordering = ["-created_at"]
        db_table = "app_equipmentitemnote"

    def __str__(self):
        return f"{self.item_id} @ {self.created_at:%Y-%m-%d}"
