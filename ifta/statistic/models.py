from django.db import models


class WeeklyDriverData(models.Model):
    driver_pay_percent = models.CharField(max_length=10, blank=True, null=True)
    fuel = models.CharField(max_length=50, blank=True, null=True)
    tolls = models.CharField(max_length=50, blank=True, null=True)
    ifta = models.CharField(max_length=50, blank=True, null=True)
    dispatch_factoring = models.CharField(max_length=50, blank=True, null=True)
    insurance = models.CharField(max_length=50, blank=True, null=True)
    truck_trailer = models.CharField(max_length=50, blank=True, null=True)
    admin = models.CharField(max_length=50, blank=True, null=True)
    empty_col = models.CharField(max_length=50, blank=True, null=True)
    driver = models.CharField(max_length=100, blank=True, null=True)
    dispatch = models.CharField(max_length=100, blank=True, null=True)
    miles = models.CharField(max_length=50, blank=True, null=True)
    avg = models.CharField(max_length=50, blank=True, null=True)
    gross = models.CharField(max_length=50, blank=True, null=True)
    driver_gross = models.CharField(max_length=50, blank=True, null=True)
    cut = models.CharField(max_length=50, blank=True, null=True)
    salary = models.CharField(max_length=50, blank=True, null=True)
    truck = models.CharField(max_length=50, blank=True, null=True)
    profit_loss = models.CharField(max_length=50, blank=True, null=True)
    mpg = models.CharField(max_length=50, blank=True, null=True)
    idle_time = models.CharField(max_length=50, blank=True, null=True)
    idle_percent = models.CharField(max_length=10, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.driver} - {self.profit_loss}"

    @property
    def profit_loss_float(self):
        """
        Konvertuje profit_loss u float odmah pri pozivu.
        Uklanja $ i , ako ih ima.
        """
        if not self.profit_loss:
            return 0.0
        try:
            return float(self.profit_loss.replace("$", "").replace(",", ""))
        except ValueError:
            return 0.0

    @classmethod
    def total_profit_loss(cls):
        """
        Sumira sve profit_loss vrednosti u tabeli.
        """
        return sum(obj.profit_loss_float for obj in cls.objects.all())


class WeeklyDayData(models.Model):
    DAY_CHOICES = [
        ('Mon', 'Monday'),
        ('Tue', 'Tuesday'),
        ('Wed', 'Wednesday'),
        ('Thu', 'Thursday'),
        ('Fri', 'Friday'),
        ('Sat', 'Saturday'),
        ('Sun', 'Sunday'),
        ('TOTALS', 'Totals'),
    ]

    day = models.CharField(max_length=10, choices=DAY_CHOICES, unique=True)
    gross = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    cut = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    miles = models.IntegerField(default=0)
    rate_per_mile = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)

    def __str__(self):
        return f"{self.day} - Gross: {self.gross}"

    @classmethod
    def get_totals(cls):
        """Automatski računa totals po kolonama za sve dane osim TOTALS"""
        totals = cls.objects.exclude(day='TOTALS').aggregate(
            total_gross=models.Sum('gross'),
            total_cut=models.Sum('cut'),
            total_miles=models.Sum('miles'),
        )
        # Rate per mile se može izračunati prosečno ili weighted
        total_rate = 0
        if totals['total_miles']:
            total_rate = totals['total_gross'] / totals['total_miles']
        totals['total_rate_per_mile'] = total_rate
        return totals


class ActiveTrucksFinalGross(models.Model):
    """
    Jedan red iz Excel/Google Sheet tabele.
    Sve vrednosti su string.
    """

    # Stabilan ključ za update (npr. "TOTAL", "HOME", ...)
    label = models.CharField(max_length=255, unique=True)

    global_value = models.CharField(max_length=255, blank=True, default="")
    unit_value = models.CharField(max_length=255, blank=True, default="")
    count_value = models.CharField(max_length=255, blank=True, default="")

    manager = models.CharField(max_length=255, blank=True, default="")
    last_update = models.CharField(max_length=255, blank=True, default="")

    # POSTAVITI redni broj da mogu da ga orderujem, ako uspe da radi po ID-u je vec

    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.label


class SheetConfig(models.Model):
    """
    Konfiguracija za jedan deljeni Excel / Google Sheet.
    Služi samo za metadata + sync parametre.
    """

    # Ljudski naziv (za admin / debug)
    title = models.CharField(
        max_length=255,
        help_text="Npr: Active Trucks – Final Gross"
    )

    # Kratki kod (za programsku upotrebu)
    code = models.SlugField(
        max_length=100,
        unique=True,
        help_text="Npr: ACTIVE_TRUCKS_FINAL_GROSS"
    )

    # Google Sheet ID ili Excel file ID
    sheet_id = models.CharField(
        max_length=255,
        help_text="Google Sheet ID ili putanja do Excel fajla"
    )

    # Range koji se čita (npr: N113:R121)
    sheet_range = models.CharField(
        max_length=50,
        help_text="Npr: N113:R121"
    )

    # Ime taba (ako koristiš)
    tab_name = models.CharField(
        max_length=120,
        blank=True,
        default=""
    )

    # Da li je aktivan (da ga sync job čita ili preskoči)
    is_active = models.BooleanField(default=True)

    # Koliko često se sync-uje (u minutima)
    sync_interval_minutes = models.PositiveIntegerField(
        default=2,
        help_text="Koliko često se radi sync (u minutima)"
    )

    # Koji model puni (informativno, ne za refleksiju)
    target_model = models.CharField(
        max_length=255,
        blank=True,
        help_text="Npr: statistic.ActiveTrucksFinalGross"
    )

    # Poslednji uspešan sync
    last_synced_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return f"{self.title} ({self.code})"


class DispatcherSheetRow(models.Model):
    dispatcher = models.CharField(max_length=200, blank=True, default="")
    gross = models.CharField(max_length=50, blank=True, default="")
    cut = models.CharField(max_length=50, blank=True, default="")
    miles = models.CharField(max_length=50, blank=True, default="")
    rpm = models.CharField(max_length=50, blank=True, default="")

    imported_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.dispatcher} - {self.gross} - {self.cut} - {self.miles} - {self.rpm}"