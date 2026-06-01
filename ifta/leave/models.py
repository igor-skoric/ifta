from django.db import models

from office.models import OfficeDirectoryEmployee


class LeaveEntry(models.Model):
    class LeaveType(models.TextChoices):
        VACATION_FULL = "L", "Vacation Leave (Full Day)"
        VACATION_MORNING = "L1", "Vacation Leave (Morning)"
        VACATION_AFTERNOON = "L2", "Vacation Leave (Afternoon)"
        SICKNESS_FULL = "S", "Sickness Leave (Full Day)"
        SICKNESS_MORNING = "S1", "Sickness Leave (Morning)"
        SICKNESS_AFTERNOON = "S2", "Sickness Leave (Afternoon)"
        MATERNITY_PATERNITY = "P", "Maternity or Paternity"
        COMPASSIONATE = "C", "Compassionate Leave"
        TOIL = "T", "TOIL (Time Off In Lieu)"
        WORK_FROM_HOME = "W", "Work From Home"
        BANK_HOLIDAY = "B", "Bank Holiday"

    employee = models.ForeignKey(
        OfficeDirectoryEmployee,
        on_delete=models.CASCADE,
        related_name="leave_entries",
    )
    leave_type = models.CharField(max_length=2, choices=LeaveType.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    note = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date", "employee__last_name", "employee__first_name"]

    def clean(self):
        super().clean()
        if self.end_date and self.start_date and self.end_date < self.start_date:
            from django.core.exceptions import ValidationError

            raise ValidationError({"end_date": "End date ne moze biti pre start date."})
        if self.leave_type in {self.LeaveType.VACATION_MORNING, self.LeaveType.VACATION_AFTERNOON}:
            if self.start_date and self.end_date and self.start_date != self.end_date:
                from django.core.exceptions import ValidationError

                raise ValidationError({"end_date": "Morning/Afternoon leave mora biti jedan dan."})

    def __str__(self):
        return f"{self.employee} {self.leave_type} {self.start_date} - {self.end_date}"


class LeaveAllowance(models.Model):
    employee = models.ForeignKey(
        OfficeDirectoryEmployee,
        on_delete=models.CASCADE,
        related_name="leave_allowances",
    )
    year = models.PositiveIntegerField()
    granted_days = models.DecimalField(max_digits=5, decimal_places=1, default=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("employee", "year")
        ordering = ["-year", "employee__last_name", "employee__first_name"]

    def __str__(self):
        return f"{self.employee} - {self.year} ({self.granted_days})"

