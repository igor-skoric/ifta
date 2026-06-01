"""Create realistic demo loads for UI/planner testing."""

from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from dispatch.load_status import LoadStatus
from dispatch.models import DispatchDriver, DispatchLoad
from dispatch.status_history import SOURCE_DEMO, record_load_status_change

LANES = [
    (("Lexington", "SC"), ("Eastover", "SC")),
    (("Chicago", "IL"), ("Dallas", "TX")),
    (("Atlanta", "GA"), ("Charlotte", "NC")),
    (("Memphis", "TN"), ("Nashville", "TN")),
    (("Indianapolis", "IN"), ("Columbus", "OH")),
    (("Houston", "TX"), ("San Antonio", "TX")),
    (("Jacksonville", "FL"), ("Miami", "FL")),
    (("Denver", "CO"), ("Salt Lake City", "UT")),
    (("Kansas City", "MO"), ("Omaha", "NE")),
    (("Louisville", "KY"), ("Cincinnati", "OH")),
    (("Phoenix", "AZ"), ("Los Angeles", "CA")),
    (("Birmingham", "AL"), ("Mobile", "AL")),
    (("Green Bay", "WI"), ("Minneapolis", "MN")),
    (("Richmond", "VA"), ("Baltimore", "MD")),
    (("Laredo", "TX"), ("El Paso", "TX")),
]

LOAD_STATUSES = [
    LoadStatus.LOAD_BOOKED,
    LoadStatus.HEADING_TO_PICKUP,
    LoadStatus.LOADED,
    LoadStatus.IN_TRANSIT,
    LoadStatus.AT_DELIVERY,
    LoadStatus.DELIVERED,
]

LOAD_NOTES = [
    "FCFS pickup until 1600.",
    "Appointment required · confirm 24h ahead.",
    "Lumper receipt required.",
    "",
]


def _monday_of_week(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _planner_days(weeks: int, *, anchor: date) -> list[date]:
    start = _monday_of_week(anchor)
    return [start + timedelta(days=offset) for offset in range(7 * weeks)]


def _aware(dt: datetime) -> datetime:
    tz = timezone.get_default_timezone()
    if timezone.is_naive(dt):
        return timezone.make_aware(dt, tz)
    return dt


def _status_chain(final_status: str, rng: random.Random) -> list[str]:
    order = [s.value for s in LoadStatus]
    if final_status not in order:
        final_status = LoadStatus.LOAD_BOOKED
    end_idx = order.index(final_status)
    start_idx = max(0, end_idx - rng.randint(1, 3))
    chain = order[start_idx : end_idx + 1]
    return chain or [final_status]


def _seed_load_history(load: DispatchLoad, final_status: str, rng: random.Random) -> None:
    prev = ""
    for status in _status_chain(final_status, rng):
        record_load_status_change(
            load=load,
            from_status=prev,
            to_status=status,
            source=SOURCE_DEMO,
        )
        prev = status


def _create_demo_load(
    *,
    driver: DispatchDriver,
    planner_date: date,
    rng: random.Random,
) -> DispatchLoad:
    """planner_date = grid column = delivery day."""
    (pick_city, pick_state), (del_city, del_state) = rng.choice(LANES)
    delivery_dt = _aware(
        datetime.combine(
            planner_date,
            time(hour=rng.randint(8, 18), minute=rng.choice([0, 30])),
        )
    )
    pickup_dt = delivery_dt - timedelta(days=rng.randint(0, 2), hours=rng.randint(4, 12))
    load_status = rng.choice(LOAD_STATUSES)

    load = DispatchLoad.objects.create(
        driver=driver,
        planner_date=delivery_dt.date(),
        broker_or_customer=f"DEMO-{rng.randint(1000000, 9999999)}",
        status=load_status,
        pickup_city=pick_city,
        pickup_state=pick_state,
        delivery_city=del_city,
        delivery_state=del_state,
        pickup_datetime=pickup_dt,
        delivery_datetime=delivery_dt,
        loaded_miles=rng.randint(180, 1150),
        linehaul_amount=Decimal(str(rng.randint(850, 4800))),
        bol_number=f"BOL{rng.randint(100000, 999999)}",
        po_number=f"PO{rng.randint(10000, 99999)}" if rng.random() > 0.4 else "",
        notes=rng.choice(LOAD_NOTES),
    )
    _seed_load_history(load, load_status, rng)
    return load


class Command(BaseCommand):
    help = (
        "Seed demo dispatch loads (broker IDs as numeric refs). "
        "Use --planner-weeks 2 to fill every day this week and next."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--loads",
            type=int,
            default=0,
            help="Random demo loads (ignored when --planner-weeks is set).",
        )
        parser.add_argument(
            "--planner-weeks",
            type=int,
            default=0,
            help="Fill planner days starting this Monday (2 = this week + next).",
        )
        parser.add_argument(
            "--drivers-per-day",
            type=int,
            default=12,
            help="How many drivers get a demo load on each planner day (default 12).",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Random seed for reproducible data (default 42).",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing demo loads before seeding.",
        )

    def handle(self, *args, **options):
        planner_weeks: int = options["planner_weeks"]
        load_count: int = options["loads"]
        drivers_per_day: int = options["drivers_per_day"]

        if load_count < 0 or planner_weeks < 0:
            raise CommandError("--loads and --planner-weeks cannot be negative.")
        if drivers_per_day < 1:
            raise CommandError("--drivers-per-day must be at least 1.")

        rng = random.Random(options["seed"])
        today = timezone.localdate()

        with transaction.atomic():
            if options["clear"]:
                deleted, _ = DispatchLoad.objects.filter(
                    broker_or_customer__startswith="DEMO-"
                ).delete()
                self.stdout.write(self.style.WARNING(f"Removed {deleted} demo load(s)."))
                if planner_weeks == 0 and load_count == 0:
                    return

            if planner_weeks == 0 and load_count == 0:
                raise CommandError(
                    "Nothing to do. Use --planner-weeks 2 and/or --loads N, or --clear --loads 0."
                )

            drivers = list(
                DispatchDriver.objects.filter(is_active=True).order_by("sort_order", "last_name", "pk")
            )
            if not drivers:
                raise CommandError(
                    "No active drivers found. Import or create drivers first, then run this command again."
                )

            created_loads = 0

            if planner_weeks > 0:
                days = _planner_days(planner_weeks, anchor=today)
                per_day = min(drivers_per_day, len(drivers))
                driver_pool = drivers[: max(per_day, min(len(drivers), 40))]

                for planner_date in days:
                    day_drivers = rng.sample(driver_pool, k=min(per_day, len(driver_pool)))
                    for driver in day_drivers:
                        _create_demo_load(driver=driver, planner_date=planner_date, rng=rng)
                        created_loads += 1

                week_start = days[0]
                week_end = days[-1]
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Planner fill: {created_loads} load(s) "
                        f"across {len(days)} days ({week_start} … {week_end}), "
                        f"~{per_day} driver(s) per day."
                    )
                )
            else:
                for i in range(load_count):
                    driver = drivers[i % len(drivers)]
                    planner_date = today + timedelta(days=rng.randint(-4, 10))
                    _create_demo_load(driver=driver, planner_date=planner_date, rng=rng)
                    created_loads += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created {created_loads} demo load(s) (random dates around {today})."
                    )
                )

        self.stdout.write(
            "Clear demo loads: python manage.py seed_dispatch_demo --clear --loads 0"
        )
