"""Load status change logs (append-only)."""

from __future__ import annotations

from django.db import transaction

from .models import DispatchLoad, DispatchLoadStatusHistory

SOURCE_PLANNER = "planner"
SOURCE_LOAD_FORM = "load_form"
SOURCE_LOAD_CREATE = "load_create"
SOURCE_LOAD_DETAIL = "load_detail"
SOURCE_BACKFILL = "backfill"
SOURCE_DEMO = "demo_seed"

SOURCE_LABELS: dict[str, str] = {
    SOURCE_PLANNER: "Planner",
    SOURCE_LOAD_FORM: "Load form",
    SOURCE_LOAD_CREATE: "Load created",
    SOURCE_LOAD_DETAIL: "Load detail",
    SOURCE_BACKFILL: "Imported",
    SOURCE_DEMO: "Demo seed",
}


def source_label(source: str) -> str:
    if not source:
        return "—"
    return SOURCE_LABELS.get(source, source.replace("_", " ").title())


def record_load_status_change(
    *,
    load: DispatchLoad,
    from_status: str,
    to_status: str,
    user=None,
    source: str = "",
) -> DispatchLoadStatusHistory | None:
    if from_status == to_status:
        return None
    return DispatchLoadStatusHistory.objects.create(
        load=load,
        from_status=from_status or "",
        to_status=to_status,
        changed_by=user,
        source=source,
    )


@transaction.atomic
def apply_load_status_change(
    *,
    load: DispatchLoad,
    to_status: str,
    from_status: str | None = None,
    user=None,
    source: str = "",
) -> DispatchLoadStatusHistory | None:
    if from_status is None:
        from_status = load.status
    if from_status == to_status:
        return None
    load.status = to_status
    load.save(update_fields=["status", "updated_at"])
    return record_load_status_change(
        load=load,
        from_status=from_status,
        to_status=to_status,
        user=user,
        source=source,
    )


def load_status_history_for_load(load: DispatchLoad, *, limit: int = 20):
    return load.status_history.select_related("changed_by").order_by("-changed_at", "-pk")[:limit]
