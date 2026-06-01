from django.db import models


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

    year = models.PositiveIntegerField(help_text="ISO week year")
    iso_week = models.PositiveSmallIntegerField(help_text="ISO week number (1–53)")
    day = models.CharField(max_length=10, choices=DAY_CHOICES)
    gross = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    cut = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    miles = models.IntegerField(default=0)
    rate_per_mile = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["year", "iso_week", "day"],
                name="statistic_weeklydaydata_year_iso_week_day_uniq",
            ),
        ]
        indexes = [
            models.Index(
                fields=["year", "iso_week"],
                name="statistic_wdd_yr_wk_idx",
            ),
        ]

    def __str__(self):
        return f"{self.year}-W{self.iso_week} {self.day} - Gross: {self.gross}"

    @classmethod
    def get_totals(cls, year=None, iso_week=None):
        """Totals po kolonama za sve dane osim TOTALS; podrazumevano tekuća nedelja ako se prosledi."""
        qs = cls.objects.all()
        if year is not None and iso_week is not None:
            qs = qs.filter(year=year, iso_week=iso_week)
        totals = qs.exclude(day="TOTALS").aggregate(
            total_gross=models.Sum("gross"),
            total_cut=models.Sum("cut"),
            total_miles=models.Sum("miles"),
        )
        total_rate = 0
        if totals["total_miles"]:
            total_rate = totals["total_gross"] / totals["total_miles"]
        totals["total_rate_per_mile"] = total_rate
        return totals


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
        help_text="Npr: statistic.DispatcherSheetRow"
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
    year = models.PositiveIntegerField(help_text="ISO week year")
    iso_week = models.PositiveSmallIntegerField(help_text="ISO week number (1–53)")
    dispatcher = models.CharField(max_length=200, blank=True, default="")
    gross = models.CharField(max_length=50, blank=True, default="")
    cut = models.CharField(max_length=50, blank=True, default="")
    miles = models.CharField(max_length=50, blank=True, default="")
    rpm = models.CharField(max_length=50, blank=True, default="")
    gpu = models.CharField(max_length=50, blank=True, default="")
    drpm = models.CharField(max_length=50, blank=True, default="")

    imported_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["year", "iso_week", "dispatcher"],
                name="statistic_dispatchersheet_year_week_dispatcher_uniq",
            ),
        ]
        indexes = [
            models.Index(
                fields=["year", "iso_week"],
                name="statistic_dsr_yr_wk_idx",
            ),
        ]

    def __str__(self):
        return f"{self.year}-W{self.iso_week} {self.dispatcher} - {self.gross} - {self.cut} - {self.miles} - {self.rpm}"