from ..models import WeeklyDriverData, WeeklyDayData, ActiveTrucksFinalGross, SheetConfig
from ..sheets.fetch_sheets import company_drivers_weekly


# Code = COMPANY_DRIVERS
def sync_weekly_driver_data():
    config = SheetConfig.objects.filter(code='COMPANY_DRIVERS').first()
    company_drivers_id = config.sheet_id
    range = config.sheet_range
    tab_name = config.tab_name

    sheet = f"{tab_name}{range}"

    rows = company_drivers_weekly(company_drivers_id, sheet)

    if not rows or len(rows) < 2:
        return

    headers = rows[0]
    data_rows = rows[1:]

    # Briše sve stare podatke
    WeeklyDriverData.objects.all().delete()

    # Upisuje nove
    for row in data_rows:
        # popuni prazna polja sa ""
        while len(row) < len(headers):
            row.append("")

        WeeklyDriverData.objects.create(
            driver_pay_percent=row[0],
            fuel=row[1],
            tolls=row[2],
            ifta=row[3],
            dispatch_factoring=row[4],
            insurance=row[5],
            truck_trailer=row[6],
            admin=row[7],
            empty_col=row[8],
            driver=row[9],
            dispatch=row[10],
            miles=row[11],
            avg=row[12],
            gross=row[13],
            driver_gross=row[14],
            cut=row[15],
            salary=row[16],
            truck=row[17],
            profit_loss=row[18],
            mpg=row[19],
            idle_time=row[20],
            idle_percent=row[21],
        )


def sync_weekly_sheet():
    config = SheetConfig.objects.filter(code='LIVEBOARD').first()
    company_drivers_id = config.sheet_id
    range = config.sheet_range
    tab_name = config.tab_name

    sheet = f'{tab_name}{range}'

    rows = company_drivers_weekly(company_drivers_id, sheet)
    if not rows or len(rows) < 2:
        return

    # Briše stare podatke
    WeeklyDayData.objects.all().delete()

    for row in rows[1:]:  # preskačemo header
        while len(row) < 5:
            row.append("0")  # popuni prazna polja

        day = row[0].strip()
        gross = float(row[1].replace("$", "").replace(",", "")) if row[1] else 0.0
        cut = float(row[2].replace("$", "").replace(",", "")) if row[2] else 0.0
        miles = int(row[3]) if row[3] else 0
        rate = float(row[4].replace("$", "")) if len(row) > 4 and row[4] else 0.0

        WeeklyDayData.objects.create(
            day=day,
            gross=gross,
            cut=cut,
            miles=miles,
            rate_per_mile=rate
        )


def sync_active_trucks_final():
    config = SheetConfig.objects.filter(code='ACTIVE_TRUCK_FINAL_GROSS').first()

    company_drivers_id = config.sheet_id
    range = config.sheet_range
    tab_name = config.tab_name

    sheet = f"{tab_name}{range}"
    rows = company_drivers_weekly(company_drivers_id, sheet)
    if not rows:
        return

    # Obrisi stare podatke (najjednostavnije)
    ActiveTrucksFinalGross.objects.all().delete()

    for row in rows:
        # Range nema obavezno header, ali ako se pojavi — preskoči
        first = (row[0] if len(row) > 0 else "").strip().upper()
        if first in ("", "GLOBAL", "GLOBAL MANAGER", "GLOBAL MANAGER UNIT COUNT", "TOTALS"):
            # "TOTALS" stavi ako ti nekad ubaci totals header, slobodno obriši ovu liniju
            if first != "TOTAL":  # da ne preskoči pravi TOTAL red
                continue

        # popuni na 6 kolona (label, global, unit, count, manager, last_update)
        # iako je range 5 kolona, ovo ti daje fleksibilnost ako nekad proširiš
        while len(row) < 6:
            row.append("")

        label = (row[0] or "").strip()
        unit_value = str(row[1] or "").strip()
        count_value = str(row[2] or "").strip()
        manager = str(row[3] or "").strip()
        last_update = str(row[4] or "").strip()  # u ovom range-u će uglavnom biti ""

        if not label:
            continue

        ActiveTrucksFinalGross.objects.create(
            label=label,
            unit_value=unit_value,
            count_value=count_value,
            manager=manager,
            last_update=last_update,
        )




