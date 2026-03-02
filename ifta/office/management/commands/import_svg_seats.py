import re
import xml.etree.ElementTree as ET

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from office.models import Seat


SEAT_RE = re.compile(r"^seat_(?P<dept>[A-Z]+)_(?P<zone>\d{2})_(?P<num>\d{2,3})$")


def _strip_ns(tag: str) -> str:
    # "{http://www.w3.org/2000/svg}g" -> "g"
    return tag.split("}", 1)[-1] if "}" in tag else tag


class Command(BaseCommand):
    help = "Import seats from an SVG file into the Seat table (by id prefix seat_)."

    def add_arguments(self, parser):
        parser.add_argument("svg_path", type=str, help="Path to .svg file")
        parser.add_argument(
            "--deactivate-missing",
            action="store_true",
            help="Mark seats missing from SVG as inactive (is_active=False).",
        )
        parser.add_argument(
            "--prefix",
            type=str,
            default="seat_",
            help="ID prefix to import (default: seat_).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        svg_path = options["svg_path"]
        prefix = options["prefix"]
        deactivate_missing = options["deactivate_missing"]

        try:
            tree = ET.parse(svg_path)
        except Exception as e:
            raise CommandError(f"Ne mogu da pročitam SVG: {e}")

        root = tree.getroot()

        found_ids = []
        for el in root.iter():
            el_id = el.attrib.get("id")
            if not el_id:
                continue
            if el_id.startswith(prefix):
                found_ids.append(el_id)

        found_ids = sorted(set(found_ids))

        if not found_ids:
            self.stdout.write(self.style.WARNING("Nisam našao nijedan seat id (seat_...)."))
            return

        created, updated = 0, 0

        for svg_id in found_ids:
            m = SEAT_RE.match(svg_id)
            dept = zone = seat_no = ""
            label = ""

            if m:
                dept = m.group("dept")
                zone = m.group("zone")
                seat_no = m.group("num")
                label = f"{dept}-{zone}-{seat_no}"
            else:
                # Ako ti se format razlikuje, i dalje importuje, samo bez parsiranja polja
                label = svg_id

            obj, is_created = Seat.objects.update_or_create(
                svg_id=svg_id,
                defaults={
                    "dept": dept,
                    "zone": zone,
                    "seat_no": seat_no,
                    "label": label,
                    "is_active": False,
                },
            )
            created += 1 if is_created else 0
            updated += 0 if is_created else 1

        if deactivate_missing:
            Seat.objects.exclude(svg_id__in=found_ids).update(is_active=False)

        self.stdout.write(self.style.SUCCESS(
            f"Import završен. Found: {len(found_ids)}, created: {created}, updated: {updated}"
        ))
