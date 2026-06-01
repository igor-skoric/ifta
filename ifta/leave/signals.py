from datetime import date
from decimal import Decimal

from django.db.models.signals import post_save
from django.dispatch import receiver

from office.models import OfficeDirectoryEmployee

from .models import LeaveAllowance


@receiver(post_save, sender=OfficeDirectoryEmployee)
def create_default_leave_allowance_for_new_employee(sender, instance, created, **kwargs):
    if not created:
        return
    LeaveAllowance.objects.get_or_create(
        employee=instance,
        year=date.today().year,
        defaults={"granted_days": Decimal("20.0")},
    )
