from datetime import date, datetime, time

from django.conf import settings
from django.db import models
from django.utils import timezone

from office.models import OfficeDirectoryEmployee

from .load_docs_status import PODStatus, RCStatus
from .load_status import LoadStatus


class DispatchLoad(models.Model):
    """One dispatch load (lane + money) assigned to a driver on the planner."""

    driver = models.ForeignKey(
        "DispatchDriver",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="loads",
    )
    planner_date = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Planner grid day (delivery day) for the assigned driver.",
    )
    broker_or_customer = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Load ID",
        help_text="Primary reference for this load (broker load #, internal ID, etc.).",
    )
    status = models.CharField(
        max_length=32,
        choices=LoadStatus.choices,
        default=LoadStatus.LOAD_BOOKED,
        db_index=True,
    )
    rc_status = models.CharField(
        max_length=32,
        choices=RCStatus.choices,
        default=RCStatus.NOT_SENT,
        db_index=True,
        verbose_name="RC status",
        help_text="Rate confirmation: sent, not sent, or uploaded.",
    )
    pod_status = models.CharField(
        max_length=32,
        choices=PODStatus.choices,
        default=PODStatus.NOT_SENT,
        db_index=True,
        verbose_name="POD status",
        help_text="Proof of delivery: sent, not sent, not delivered, or delivered.",
    )
    rate_confirmation_source = models.CharField(
        max_length=512,
        blank=True,
        help_text="Optional: filename, URL, or document id for future AI (rate confirmation).",
    )
    equipment_type = models.CharField(max_length=64, blank=True)
    pickup_city = models.CharField(max_length=120, blank=True)
    pickup_state = models.CharField(max_length=64, blank=True)
    delivery_city = models.CharField(max_length=120, blank=True)
    delivery_state = models.CharField(max_length=64, blank=True)
    pickup_window = models.CharField(
        max_length=200,
        blank=True,
        help_text="Appointment / window text until structured fields exist.",
    )
    delivery_window = models.CharField(max_length=200, blank=True)
    pickup_datetime = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Scheduled pick-up date and time for this load.",
    )
    delivery_datetime = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Scheduled delivery date and time (optional; complements free-text delivery window).",
    )
    loaded_miles = models.PositiveIntegerField(null=True, blank=True)
    linehaul_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    bol_number = models.CharField(max_length=64, blank=True)
    po_number = models.CharField(max_length=64, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-planner_date", "-created_at", "pk"]
        indexes = [
            models.Index(fields=["driver", "planner_date"]),
        ]

    def pickup_display(self) -> str:
        """Single-line pickup (e.g. Lexington, SC)."""
        city = (self.pickup_city or "").strip()
        state = (self.pickup_state or "").strip()
        if city and state and "," not in city:
            return f"{city}, {state}"
        return city or state

    def pickup_planner_date(self) -> date | None:
        if self.pickup_datetime:
            return self.pickup_datetime.date()
        return None

    def delivery_planner_date(self) -> date | None:
        if self.delivery_datetime:
            return self.delivery_datetime.date()
        return self.planner_date

    def planner_grid_date(self) -> date | None:
        """Day this load appears on the planner grid (= delivery day)."""
        return self.delivery_planner_date()

    def delivery_display(self) -> str:
        """Single-line delivery (e.g. Eastover, SC)."""
        city = (self.delivery_city or "").strip()
        state = (self.delivery_state or "").strip()
        if city and state and "," not in city:
            return f"{city}, {state}"
        return city or state

    def load_id_display(self) -> str:
        return (self.broker_or_customer or "").strip()

    def rate_per_mile(self):
        """Linehaul ÷ loaded miles when both are set."""
        from decimal import Decimal

        if (
            self.loaded_miles
            and self.loaded_miles > 0
            and self.linehaul_amount is not None
        ):
            return self.linehaul_amount / Decimal(self.loaded_miles)
        return None

    def rate_per_mile_display(self) -> str:
        rpm = self.rate_per_mile()
        if rpm is None:
            return ""
        return f"${rpm:,.2f}"

    def status_badge_css_class(self) -> str:
        from .load_status import load_status_badge_class

        return load_status_badge_class(self.status)

    def rc_status_badge_css_class(self) -> str:
        from .load_docs_status import rc_status_badge_class

        return rc_status_badge_class(self.rc_status)

    def pod_status_badge_css_class(self) -> str:
        from .load_docs_status import pod_status_badge_class

        return pod_status_badge_class(self.pod_status)

    def planner_status_css_class(self) -> str:
        from .load_status import load_status_planner_class

        return load_status_planner_class(self.status)

    @classmethod
    def terminal_planner_statuses(cls) -> frozenset[str]:
        return frozenset({LoadStatus.DELIVERED, LoadStatus.CANCELLED})

    def default_pickup_datetime(self) -> datetime | None:
        if not self.planner_date:
            return None
        naive = datetime.combine(self.planner_date, time.min)
        tz = timezone.get_default_timezone()
        if timezone.is_naive(naive):
            return timezone.make_aware(naive, tz)
        return naive

    def pickup_datetime_display(self):
        if self.pickup_datetime:
            return self.pickup_datetime
        return self.default_pickup_datetime()

    def planner_span(self) -> tuple[date | None, date | None]:
        d = self.planner_grid_date()
        return d, d

    def display_title(self) -> str:
        label = self.summary_label()
        return label if label else f"Load #{self.pk}"

    def summary_label(self) -> str:
        """Short label for lists and planner (load ID first when set)."""
        load_id = self.load_id_display()
        a = self.pickup_display()
        b = self.delivery_display()
        if load_id and (a or b):
            return f"{load_id} · {a or '—'} → {b or '—'}"
        if load_id:
            return load_id[:120]
        if a or b:
            return f"{a or '—'} → {b or '—'}"
        notes = (self.notes or "").strip()
        if notes:
            return notes.splitlines()[0][:120]
        return ""

    def __str__(self):
        return self.summary_label() or f"Load #{self.pk}"


class DispatchLoadComment(models.Model):
    """Chronological comments on a dispatch load (planner + load detail)."""

    load = models.ForeignKey(
        DispatchLoad,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dispatch_load_comments",
    )

    class Meta:
        ordering = ["-created_at", "-pk"]
        indexes = [
            models.Index(fields=["load", "-created_at"]),
        ]

    def __str__(self):
        preview = (self.body or "").strip().replace("\n", " ")[:60]
        return f"Comment on load {self.load_id}: {preview}"


class DispatchLoadStatusHistory(models.Model):
    """Append-only log of load status changes."""

    load = models.ForeignKey(
        DispatchLoad,
        on_delete=models.CASCADE,
        related_name="status_history",
    )
    from_status = models.CharField(
        max_length=32,
        choices=LoadStatus.choices,
        blank=True,
        help_text="Empty for the initial status on create or backfill.",
    )
    to_status = models.CharField(max_length=32, choices=LoadStatus.choices)
    changed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dispatch_load_status_changes",
    )
    source = models.CharField(max_length=32, blank=True)

    class Meta:
        ordering = ["-changed_at", "-pk"]
        indexes = [
            models.Index(fields=["load", "-changed_at"]),
        ]
        verbose_name = "load status history"
        verbose_name_plural = "load status history"

    def __str__(self):
        return f"Load {self.load_id}: {self.from_status or '—'} → {self.to_status}"

    def from_status_display(self) -> str:
        if not self.from_status:
            return "—"
        return self.get_from_status_display()

    def to_status_badge_css_class(self) -> str:
        from .load_status import load_status_badge_class

        return load_status_badge_class(self.to_status)

    def from_status_badge_css_class(self) -> str:
        if not self.from_status:
            return ""
        from .load_status import load_status_badge_class

        return load_status_badge_class(self.from_status)

    def source_display(self) -> str:
        from .status_history import source_label

        return source_label(self.source)


class DispatchDriver(models.Model):
    """Driver; dispatcher (OfficeDirectoryEmployee) is optional until assigned."""

    class DriverooStatus(models.TextChoices):
        YES = "yes", "Yes"
        NO = "no", "No"
        REQ = "req", "Req"

    class CompOoLocalLegal(models.TextChoices):
        LOCAL_IL = "local_il", "LOCAL (IL)"
        LOCAL_IL_HOOK = "local_il_hook", "LOCAL (IL + HOOK)"
        OO = "oo", "OO"
        COMP_FROM_525 = "comp_from_525", "COMP FROM 5/25"
        COMP_30 = "comp_30", "COMP 30%"
        COMP_35 = "comp_35", "COMP 35%"
        COMP_32 = "comp_32", "COMP 32%"
        COMP_065_CPM = "comp_065_cpm", "COMP 0.65 CPM"
        COMP_075_CPM = "comp_075_cpm", "COMP 0.75 CPM"
        COMP_30_BONUS = "comp_30_bonus", "COMP %30+BONUS"

    class FleetCompany(models.TextChoices):
        FULLY_TRIUMPH = "fully_triumph", "FULLY TRIUMPH"
        FULLY_ILIM = "fully_ilim", "FULLY ILIM"
        FULLY_GNS = "fully_gns", "FULLY GNS"
        TRIUMPH_ILIM = "triumph_ilim", "TRIUMPH/ILIM"
        TRIUMPH_FERRUM="triumph_ferrum","TRIUMPH/FERRUM"
        GNS_FERRUM="gns_ferrum","GNS/FERRUM"
        GNS_ILIM = "gns_ilim", "GNS/ILIM"
        ILIM_FERRUM = "ilim_ferrum","ILIM/FERRUM"

    dispatcher = models.ForeignKey(
        OfficeDirectoryEmployee,
        on_delete=models.CASCADE,
        related_name="dispatch_drivers",
        null=True,
        blank=True,
    )
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    legacy_driver_id = models.CharField(
        max_length=64,
        blank=True,
        db_index=True,
        help_text="Legacy ID from the previous system (for data migration).",
    )
    hire_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date the driver was hired.",
    )
    driveroo_status = models.CharField(
        max_length=8,
        choices=DriverooStatus.choices,
        blank=True,
        help_text="Driveroo app: Yes / No / Req.",
    )
    comp_oo_local_legal = models.CharField(
        max_length=32,
        choices=CompOoLocalLegal.choices,
        blank=True,
        help_text="COMP / OO / LOCAL / LEGAL classification.",
    )
    fleet_company = models.CharField(
        max_length=32,
        choices=FleetCompany.choices,
        blank=True,
        help_text="Operating company (dropdown).",
    )
    phone = models.CharField(max_length=40, blank=True, help_text="Driver cell or primary phone (optional).")
    email = models.EmailField(blank=True, help_text="Driver email (optional).")
    rts_fuel_card = models.BooleanField(
        default=False,
        help_text="Whether the driver has an RTS fuel card.",
    )
    notes = models.TextField(blank=True, help_text="Internal notes for dispatch.")
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "last_name", "first_name"]
        indexes = [
            models.Index(fields=["dispatcher", "is_active"]),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip() or f"Driver #{self.pk}"

    @property
    def display_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def truck(self):
        from .assignments import get_driver_truck

        return get_driver_truck(self)

    @property
    def trailers(self):
        from .assignments import _CurrentTrailerRelated

        return _CurrentTrailerRelated(self)


class DriverUnavailability(models.Model):
    """Date range when a driver cannot be scheduled on the load planner."""

    class Reason(models.TextChoices):
        VACATION = "vacation", "Vacation / time off"
        SICK = "sick", "Sick"
        CANNOT_DRIVE = "cannot_drive", "Cannot drive"
        OTHER = "other", "Other"

    driver = models.ForeignKey(
        DispatchDriver,
        on_delete=models.CASCADE,
        related_name="unavailability_entries",
    )
    reason = models.CharField(max_length=20, choices=Reason.choices, default=Reason.VACATION)
    start_date = models.DateField()
    end_date = models.DateField()
    note = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date", "-pk"]
        indexes = [
            models.Index(fields=["driver", "start_date", "end_date"]),
        ]
        verbose_name_plural = "driver unavailability entries"

    def clean(self):
        super().clean()
        if self.end_date and self.start_date and self.end_date < self.start_date:
            from django.core.exceptions import ValidationError

            raise ValidationError({"end_date": "End date cannot be before start date."})

    def __str__(self):
        return f"{self.driver} · {self.get_reason_display()} · {self.start_date} – {self.end_date}"

    @property
    def planner_short_label(self) -> str:
        labels = {
            self.Reason.VACATION: "Off",
            self.Reason.SICK: "Sick",
            self.Reason.CANNOT_DRIVE: "N/A",
            self.Reason.OTHER: "Away",
        }
        return labels.get(self.reason, "Off")

    @property
    def planner_css_class(self) -> str:
        return f"day-cell--unavailable-{self.reason}"


class DispatchTruck(models.Model):
    """Truck unit; driver link is via DispatchAssignment (history)."""

    unit_number = models.CharField(max_length=64)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["unit_number"]

    def __str__(self):
        return self.unit_number

    @property
    def driver(self):
        from .assignments import get_truck_driver

        return get_truck_driver(self)

    @property
    def trailers(self):
        from .assignments import get_truck_trailers

        return get_truck_trailers(self)


class DispatchTrailer(models.Model):
    """Trailer unit; driver link is via DispatchAssignment (history)."""

    unit_number = models.CharField(max_length=64)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["unit_number"]

    def __str__(self):
        return self.unit_number

    @property
    def driver(self):
        from .assignments import get_trailer_driver

        return get_trailer_driver(self)

    @property
    def truck(self):
        from .assignments import get_trailer_truck

        return get_trailer_truck(self)


class DispatchAssignment(models.Model):
    """Historical link between driver, truck, and trailer; ended_at null = current."""

    driver = models.ForeignKey(
        DispatchDriver,
        on_delete=models.CASCADE,
        related_name="assignments",
        null=True,
        blank=True,
    )
    truck = models.ForeignKey(
        DispatchTruck,
        on_delete=models.SET_NULL,
        related_name="assignments",
        null=True,
        blank=True,
    )
    trailer = models.ForeignKey(
        DispatchTrailer,
        on_delete=models.SET_NULL,
        related_name="assignments",
        null=True,
        blank=True,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True, db_index=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at", "-pk"]
        indexes = [
            models.Index(fields=["driver", "ended_at"]),
            models.Index(fields=["truck", "ended_at"]),
            models.Index(fields=["trailer", "ended_at"]),
        ]
        verbose_name = "dispatch assignment"
        verbose_name_plural = "dispatch assignments"

    def __str__(self):
        parts = [self.driver.display_name] if self.driver_id else ["no driver"]
        if self.truck_id:
            parts.append(f"truck {self.truck.unit_number}")
        if self.trailer_id:
            parts.append(f"trailer {self.trailer.unit_number}")
        status = "current" if self.ended_at is None else "ended"
        return f"{' · '.join(parts)} ({status})"

    @property
    def is_current(self) -> bool:
        return self.ended_at is None
