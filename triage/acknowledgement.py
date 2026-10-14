"""Template-based acknowledgement text."""

from __future__ import annotations

from datetime import date
from typing import Any

from .models import Request, ValidationIssue


def response_target(priority: str, ack_config: dict[str, Any]) -> str:
    targets = ack_config.get("response_targets", {})
    for name, value in targets.items():
        if name != "default" and name.casefold() == (priority or "").casefold():
            return value
    return targets.get("default", "5 working days")


def format_date(value: date | None, fallback: str) -> str:
    if value is None:
        return fallback
    return f"{value.day} {value.strftime('%B %Y')}"


def build_acknowledgement(
    request: Request,
    category: str,
    submitted: date | None,
    issues: list[ValidationIssue],
    ack_config: dict[str, Any],
    *,
    priority: str | None = None,
    channel: str | None = None,
) -> str:
    unknown = ack_config.get("unknown_values", {})
    notes = ack_config.get("category_notes", {})
    category_note = notes.get(category) or notes.get("Uncategorised", "")

    incomplete_note = ""
    if issues:
        fields = sorted({issue.field for issue in issues})
        incomplete_note = ack_config.get("incomplete_note", "").format(missing_fields=", ".join(fields))

    priority_text = (priority or request.priority or "").strip() or unknown.get("priority", "standard")
    channel_text = (channel or request.channel or "").strip() or unknown.get("channel", "an unrecorded channel")

    text = ack_config["template"].format(
        request_id=request.request_id or unknown.get("request_id", "(reference pending)"),
        submitted_date=format_date(submitted, unknown.get("submitted_date", "on an unrecorded date")),
        channel=channel_text,
        category=category,
        priority=priority_text,
        response_target=response_target(priority_text, ack_config),
        category_note=category_note,
        incomplete_note=incomplete_note,
        sender=ack_config.get("sender", "Digital Services Team"),
    )
    # Collapse runs of more than two newlines left behind by optional sections.
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text.strip() + "\n"
