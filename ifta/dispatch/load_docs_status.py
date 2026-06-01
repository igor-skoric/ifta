"""RC (rate confirmation) and POD (proof of delivery) status choices and badge styles."""

from __future__ import annotations

from django.db import models


class RCStatus(models.TextChoices):
    NOT_SENT = "not_sent", "Not sent"
    SENT = "sent", "Sent"
    UPLOADED = "uploaded", "Uploaded"


class PODStatus(models.TextChoices):
    NOT_SENT = "not_sent", "Not sent"
    SENT = "sent", "Sent"
    NOT_DELIVERED = "not_delivered", "Not delivered"
    DELIVERED = "delivered", "Delivered"


DOC_STATUS_BADGE_STYLES: dict[str, dict[str, str]] = {
    "rc-not_sent": {
        "bg": "rgba(100, 116, 139, 0.35)",
        "border": "rgba(148, 163, 184, 0.5)",
        "text": "rgb(226, 232, 240)",
    },
    "rc-sent": {
        "bg": "rgba(59, 130, 246, 0.38)",
        "border": "rgba(96, 165, 250, 0.55)",
        "text": "rgb(219, 234, 254)",
    },
    "rc-uploaded": {
        "bg": "rgba(16, 185, 129, 0.38)",
        "border": "rgba(52, 211, 153, 0.55)",
        "text": "rgb(209, 250, 229)",
    },
    "pod-not_sent": {
        "bg": "rgba(100, 116, 139, 0.35)",
        "border": "rgba(148, 163, 184, 0.5)",
        "text": "rgb(226, 232, 240)",
    },
    "pod-sent": {
        "bg": "rgba(59, 130, 246, 0.38)",
        "border": "rgba(96, 165, 250, 0.55)",
        "text": "rgb(219, 234, 254)",
    },
    "pod-not_delivered": {
        "bg": "rgba(245, 158, 11, 0.4)",
        "border": "rgba(251, 191, 36, 0.55)",
        "text": "rgb(254, 243, 199)",
    },
    "pod-delivered": {
        "bg": "rgba(16, 185, 129, 0.38)",
        "border": "rgba(52, 211, 153, 0.55)",
        "text": "rgb(209, 250, 229)",
    },
}


def rc_status_badge_class(status: str) -> str:
    return f"doc-status-badge--rc-{status}"


def pod_status_badge_class(status: str) -> str:
    return f"doc-status-badge--pod-{status}"
