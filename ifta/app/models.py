from django.db import models


class State(models.Model):
    code = models.CharField(max_length=2, unique=True)
    name = models.CharField(max_length=50)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code}"


class StateTaxRate(models.Model):
    state = models.ForeignKey(State, on_delete=models.CASCADE)
    fuel_type = models.CharField(max_length=20, default="diesel")
    rate = models.DecimalField(max_digits=6, decimal_places=4)  # npr 0.3890
    valid_from = models.DateField()
    valid_to = models.DateField()

    class Meta:
        ordering = ["state", "valid_from"]

    def __str__(self):
        return f"{self.state.code} - {self.rate}"


class VehicleRecord(models.Model):
    vehicle = models.CharField(max_length=100)
    jurisdiction = models.CharField(max_length=10)
    total_miles = models.FloatField(null=True, blank=True)
    fuel_qty = models.FloatField(null=True, blank=True)

    file_name = models.CharField(max_length=255)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Vehicle Record"
        verbose_name_plural = "Vehicle Records"
        unique_together = ('vehicle', 'jurisdiction')
        ordering = ['vehicle', 'jurisdiction']

    def __str__(self):
        return f"{self.vehicle} - {self.jurisdiction} | Miles: {self.total_miles} | Fuel: {self.fuel_qty}"
