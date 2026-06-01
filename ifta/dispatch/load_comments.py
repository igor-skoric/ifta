"""Load comment helpers."""

from __future__ import annotations

from django.contrib.auth import get_user_model

from .models import DispatchLoadComment

User = get_user_model()


def comment_author_display(user) -> str:
    if not user:
        return "Unknown"
    name = (user.get_full_name() or "").strip()
    return name or user.get_username()


def serialize_load_comment(comment: DispatchLoadComment) -> dict:
    return {
        "id": comment.pk,
        "body": comment.body,
        "created_at": comment.created_at.isoformat(),
        "author": comment_author_display(comment.created_by),
    }
