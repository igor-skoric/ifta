from django import forms
from core.ui_classes import APP_CHECKBOX, APP_INPUT
from office.models import OfficeDirectoryEmployee

from .assignments import (
    assign_driver_trailer,
    assign_driver_truck,
    drivers_without_current_truck,
    get_trailer_driver,
    get_truck_driver,
)
from .load_docs_status import PODStatus, RCStatus
from .load_status import LoadStatus
from .models import DispatchDriver, DispatchLoad, DispatchTrailer, DispatchTruck, DriverUnavailability

_CTRL = APP_INPUT
_CTRL_PH = APP_INPUT


class DispatchLoadForm(forms.ModelForm):
    pickup = forms.CharField(
        required=False,
        label="Pick up",
        widget=forms.TextInput(
            attrs={
                "class": _CTRL_PH,
                "placeholder": "e.g. Lexington, SC",
            }
        ),
    )
    delivery = forms.CharField(
        required=False,
        label="Delivery",
        widget=forms.TextInput(
            attrs={
                "class": _CTRL_PH,
                "placeholder": "e.g. Eastover, SC",
            }
        ),
    )

    class Meta:
        model = DispatchLoad
        fields = (
            "status",
            "rc_status",
            "pod_status",
            "broker_or_customer",
            "pickup_datetime",
            "delivery_datetime",
            "loaded_miles",
            "linehaul_amount",
            "notes",
        )
        widgets = {
            "status": forms.Select(attrs={"class": _CTRL}),
            "rc_status": forms.Select(attrs={"class": _CTRL}),
            "pod_status": forms.Select(attrs={"class": _CTRL}),
            "broker_or_customer": forms.TextInput(
                attrs={
                    "class": _CTRL_PH,
                    "placeholder": "e.g. 1048821",
                }
            ),
            "pickup_datetime": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={
                    "type": "datetime-local",
                    "step": "60",
                    "class": _CTRL,
                },
            ),
            "delivery_datetime": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={
                    "type": "datetime-local",
                    "step": "60",
                    "class": _CTRL,
                },
            ),
            "loaded_miles": forms.NumberInput(
                attrs={"class": _CTRL_PH, "placeholder": "Miles"}
            ),
            "linehaul_amount": forms.NumberInput(
                attrs={"class": _CTRL_PH, "placeholder": "0.00", "step": "0.01"}
            ),
            "notes": forms.Textarea(
                attrs={
                    "rows": 2,
                    "class": _CTRL_PH,
                    "placeholder": "Optional notes",
                }
            ),
        }

    def __init__(self, *args, pickup_date=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["broker_or_customer"].label = "Load ID"
        self.fields["broker_or_customer"].required = False
        self.fields["status"].required = True
        self.fields["rc_status"].required = True
        self.fields["pod_status"].required = True
        self.fields["pickup_datetime"].required = False
        self.fields["delivery_datetime"].required = False
        self.fields["loaded_miles"].required = False
        self.fields["linehaul_amount"].required = False
        self.fields["notes"].required = False
        dt_formats = [
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
        ]
        self.fields["pickup_datetime"].input_formats = dt_formats
        self.fields["delivery_datetime"].input_formats = dt_formats
        if self.instance.pk:
            self.fields["pickup"].initial = self.instance.pickup_display()
            self.fields["delivery"].initial = self.instance.delivery_display()
        elif pickup_date and not self.initial.get("pickup_datetime"):
            from datetime import datetime, time

            from django.utils import timezone

            naive = datetime.combine(pickup_date, time(hour=8, minute=0))
            tz = timezone.get_default_timezone()
            if timezone.is_naive(naive):
                self.initial["pickup_datetime"] = timezone.make_aware(naive, tz)

    def save(self, commit=True):
        load = super().save(commit=False)
        load.pickup_city = (self.cleaned_data.get("pickup") or "").strip()
        load.pickup_state = ""
        load.delivery_city = (self.cleaned_data.get("delivery") or "").strip()
        load.delivery_state = ""
        if load.delivery_datetime:
            load.planner_date = load.delivery_datetime.date()
        else:
            load.planner_date = None
        if not load.status:
            load.status = LoadStatus.LOAD_BOOKED
        if not load.rc_status:
            load.rc_status = RCStatus.NOT_SENT
        if not load.pod_status:
            load.pod_status = PODStatus.NOT_SENT
        if commit:
            load.save()
        return load


class DispatchDriverForm(forms.ModelForm):
    class Meta:
        model = DispatchDriver
        fields = (
            "first_name",
            "last_name",
            "legacy_driver_id",
            "hire_date",
            "driveroo_status",
            "comp_oo_local_legal",
            "fleet_company",
            "phone",
            "email",
            "rts_fuel_card",
            "notes",
            "dispatcher",
            "is_active",
            "sort_order",
        )
        widgets = {
            "first_name": forms.TextInput(attrs={"class": _CTRL_PH, "autocomplete": "given-name"}),
            "last_name": forms.TextInput(attrs={"class": _CTRL_PH, "autocomplete": "family-name"}),
            "legacy_driver_id": forms.TextInput(
                attrs={
                    "class": _CTRL_PH,
                    "placeholder": "Legacy system ID (migration)",
                    "autocomplete": "off",
                }
            ),
            "hire_date": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "type": "date",
                    "class": _CTRL,
                },
            ),
            "driveroo_status": forms.Select(attrs={"class": _CTRL}),
            "comp_oo_local_legal": forms.Select(attrs={"class": _CTRL}),
            "fleet_company": forms.Select(attrs={"class": _CTRL}),
            "phone": forms.TextInput(attrs={"class": _CTRL_PH, "autocomplete": "tel", "inputmode": "tel"}),
            "email": forms.EmailInput(attrs={"class": _CTRL_PH, "autocomplete": "email"}),
            "rts_fuel_card": forms.CheckboxInput(
                attrs={"class": APP_CHECKBOX}
            ),
            "notes": forms.Textarea(attrs={"rows": 3, "class": _CTRL_PH}),
            "dispatcher": forms.Select(attrs={"class": _CTRL}),
            "is_active": forms.CheckboxInput(
                attrs={"class": APP_CHECKBOX}
            ),
            "sort_order": forms.NumberInput(attrs={"class": _CTRL_PH, "min": "0"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["dispatcher"].queryset = (
            OfficeDirectoryEmployee.objects.filter(is_active=True, is_dispatcher=True)
            .order_by("last_name", "first_name")
        )
        self.fields["dispatcher"].required = False
        self.fields["legacy_driver_id"].required = False
        self.fields["hire_date"].required = False
        self.fields["hire_date"].input_formats = ["%Y-%m-%d"]
        self.fields["driveroo_status"].required = False
        self.fields["comp_oo_local_legal"].required = False
        self.fields["fleet_company"].required = False
        self.fields["phone"].required = False
        self.fields["email"].required = False
        self.fields["notes"].required = False
        for name in ("driveroo_status", "comp_oo_local_legal", "fleet_company"):
            f = self.fields[name]
            pairs = [(k, v) for k, v in f.choices if k != ""]
            f.choices = [("", "—")] + pairs


class DispatchTruckForm(forms.ModelForm):
    driver = forms.ModelChoiceField(
        queryset=DispatchDriver.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": _CTRL}),
        label="Driver",
    )

    class Meta:
        model = DispatchTruck
        fields = ("unit_number", "notes", "is_active")
        widgets = {
            "unit_number": forms.TextInput(attrs={"class": _CTRL_PH}),
            "notes": forms.Textarea(
                attrs={"rows": 3, "class": _CTRL_PH},
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": APP_CHECKBOX}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        exclude_id = None
        current = get_truck_driver(self.instance) if self.instance.pk else None
        if current:
            exclude_id = current.pk
            self.fields["driver"].initial = current
        self.fields["driver"].queryset = drivers_without_current_truck(exclude_driver_id=exclude_id)

    def save(self, commit=True):
        truck = super().save(commit=commit)
        if commit:
            assign_driver_truck(
                self.cleaned_data.get("driver"),
                truck,
                carry_trailers=True,
            )
        return truck


class DispatchTrailerForm(forms.ModelForm):
    driver = forms.ModelChoiceField(
        queryset=DispatchDriver.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": _CTRL}),
        label="Driver",
    )

    class Meta:
        model = DispatchTrailer
        fields = ("unit_number", "notes", "is_active")
        widgets = {
            "unit_number": forms.TextInput(attrs={"class": _CTRL_PH}),
            "notes": forms.Textarea(
                attrs={"rows": 3, "class": _CTRL_PH},
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": APP_CHECKBOX}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current = get_trailer_driver(self.instance) if self.instance.pk else None
        if current:
            self.fields["driver"].initial = current
        self.fields["driver"].queryset = DispatchDriver.objects.filter(is_active=True).order_by(
            "sort_order", "last_name", "first_name"
        )

    def save(self, commit=True):
        trailer = super().save(commit=commit)
        if commit:
            assign_driver_trailer(self.cleaned_data.get("driver"), trailer)
        return trailer


class DriverUnavailabilityForm(forms.ModelForm):
    class Meta:
        model = DriverUnavailability
        fields = ["reason", "start_date", "end_date", "note"]
        widgets = {
            "start_date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date", "class": _CTRL}),
            "end_date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date", "class": _CTRL}),
            "reason": forms.Select(attrs={"class": _CTRL}),
            "note": forms.TextInput(
                attrs={"class": _CTRL_PH, "placeholder": "Optional note (visible to dispatchers)"}
            ),
        }

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_date")
        end = cleaned.get("end_date")
        if start and end and end < start:
            raise forms.ValidationError("End date cannot be before start date.")
        return cleaned
