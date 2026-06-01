from django import forms

from core.ui_classes import APP_INPUT

from .models import LeaveAllowance, LeaveEntry


class LeaveEntryForm(forms.ModelForm):
    class Meta:
        model = LeaveEntry
        fields = ["employee", "leave_type", "start_date", "end_date", "note"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": APP_INPUT})


class LeaveAllowanceForm(forms.ModelForm):
    class Meta:
        model = LeaveAllowance
        fields = ["employee", "year", "granted_days"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": APP_INPUT})

