from django import forms

from core.ui_classes import APP_CHECKBOX, APP_INPUT

from .models import Department, OfficeDirectoryEmployee, OfficeEquipmentItem, OfficeEquipmentItemNote


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = OfficeDirectoryEmployee
        fields = [
            "first_name",
            "last_name",
            "work_email",
            "private_email",
            "work_phone",
            "private_phone",
            "login_type",
            "department",
            "location",
            "position",
            "is_active",
            "is_dispatcher",
        ]
        help_texts = {
            "is_dispatcher": "Shows this person on Dispatch load planner; add their drivers via Admin or inline on this employee.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department"].queryset = Department.objects.filter(is_active=True).order_by("sort_order", "name")
        for name, field in self.fields.items():
            if name in ("is_active", "is_dispatcher"):
                field.widget.attrs.update({"class": APP_CHECKBOX})
            else:
                field.widget.attrs.update({"class": APP_INPUT})

    def clean(self):
        cleaned_data = super().clean()
        for name in ("work_email", "private_email", "work_phone", "private_phone"):
            if cleaned_data.get(name) == "":
                cleaned_data[name] = None
        return cleaned_data


class EmployeeExcelImportForm(forms.Form):
    file = forms.FileField(
        label="Excel (.xlsx)",
        allow_empty_file=False,
        widget=forms.ClearableFileInput(
            attrs={
                "accept": ".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "class": "block w-full text-sm text-slate-300 file:mr-3 file:rounded-lg file:border-0 file:bg-indigo-500 file:px-3 file:py-2 file:font-semibold file:text-white hover:file:bg-indigo-400",
            }
        ),
    )

    def clean_file(self):
        f = self.cleaned_data["file"]
        name = (f.name or "").lower()
        if not name.endswith(".xlsx"):
            raise forms.ValidationError("Dozvoljen je samo .xlsx format.")
        return f


class EquipmentItemNoteForm(forms.ModelForm):
    class Meta:
        model = OfficeEquipmentItemNote
        fields = ["body"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["body"].widget = forms.Textarea(
            attrs={"rows": 4, "class": APP_INPUT, "placeholder": "Dodaj belešku u istoriju…"}
        )


class EquipmentItemForm(forms.ModelForm):
    class Meta:
        model = OfficeEquipmentItem
        fields = ["asset_id", "equipment_type", "state", "brand_model", "serial_number", "assigned_employee", "notes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": APP_INPUT})
