"""Decides which requests need a person to look at them, and why.

Each flag has a code, a severity and a plain-English reason. A request needs
human review when it carries at least one ``warning`` or ``critical`` flag;
``info`` flags are shown for transparency but do not block automatic handling.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from .models import CategoryResult, Request, ReviewFlag, ValidationIssue

SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}
REVIEW_SEVERITIES = {"critical", "warning"}


def _prefix_pattern(keyword: str) -> re.Pattern[str]:
    # Prefix match so "pregnan" catches "pregnancy" and "pregnant".
    return re.compile(r"(?<!\w)" + re.escape(keyword), re.IGNORECASE)


def _find_keywords(text: str, keywords: list[str]) -> list[str]:
    return [kw for kw in keywords if _prefix_pattern(kw).search(text)]


def detect_personal_data(text: str, patterns: dict[str, str]) -> list[str]:
    """Return the kinds of personal data whose pattern matches (never the values)."""
    kinds: list[str] = []
    for label, pattern in patterns.items():
        try:
            if re.search(pattern, text):
                kinds.append(label)
        except re.error:
            continue
    return kinds


def assess(
    request: Request,
    issues: list[ValidationIssue],
    category: CategoryResult,
    submitted: date | None,
    as_of: date,
    rules: dict[str, Any],
    *,
    duplicate_ids: set[str] | None = None,
    priority: str | None = None,
    status: str | None = None,
) -> list[ReviewFlag]:
    cfg = rules["review"]
    flags: list[ReviewFlag] = []
    summary = request.request_summary or ""
    priority = priority if priority is not None else request.priority
    status = status if status is not None else request.status

    if issues:
        fields = ", ".join(sorted({i.field for i in issues}))
        flags.append(ReviewFlag("MISSING_OR_INVALID_INFO", "critical", f"Required information missing or invalid: {fields}"))

    kinds = detect_personal_data(summary, cfg.get("personal_data_patterns", {}))
    if kinds:
        flags.append(
            ReviewFlag(
                "POSSIBLE_PERSONAL_DATA",
                "critical",
                f"Summary appears to contain personal data ({', '.join(kinds)}); check before storing or forwarding",
            )
        )

    sensitive = _find_keywords(summary, cfg.get("sensitive_keywords", []))
    if sensitive:
        flags.append(
            ReviewFlag(
                "SENSITIVE_CONTENT",
                "critical",
                f"Mentions '{sensitive[0]}' which may involve special category or confidential data; handle under data protection guidance",
            )
        )

    credentials = _find_keywords(summary, cfg.get("credential_keywords", []))
    if credentials:
        flags.append(
            ReviewFlag(
                "CREDENTIALS",
                "warning",
                f"Mentions '{credentials[0]}'; credentials must never be shared through requests, use the self-service reset route",
            )
        )

    if duplicate_ids and request.request_id in duplicate_ids:
        flags.append(ReviewFlag("DUPLICATE_ID", "warning", f"Request ID {request.request_id} appears more than once in the file"))

    if category.confidence == "none":
        flags.append(ReviewFlag("UNCATEGORISED", "warning", "No category rule matched the summary"))
    elif category.confidence == "low":
        flags.append(ReviewFlag("LOW_CONFIDENCE", "warning", f"Category match is weak: {category.rationale}"))

    submitted_type = (request.request_type or "").strip()
    if submitted_type and category.confidence != "none" and submitted_type.casefold() != category.category.casefold():
        flags.append(
            ReviewFlag(
                "CATEGORY_MISMATCH",
                "warning",
                f"Submitted type '{submitted_type}' differs from rule-based category '{category.category}'",
            )
        )
    elif not submitted_type and category.confidence != "none":
        flags.append(ReviewFlag("CATEGORY_ASSIGNED", "info", f"Request Type was blank; rules assigned '{category.category}'"))

    if category.category.casefold() == "access & permissions":
        external = _find_keywords(summary, cfg.get("external_access_keywords", []))
        if external:
            flags.append(
                ReviewFlag(
                    "EXTERNAL_ACCESS",
                    "warning",
                    f"Access for an external party ('{external[0]}') needs an information-governance check before approval",
                )
            )

    attention = [p.casefold() for p in cfg.get("attention_priorities", ["High"])]
    if (priority or "").casefold() in attention:
        flags.append(ReviewFlag("HIGH_PRIORITY", "warning", f"{priority} priority: confirm urgency and assign an owner today"))

    overdue_statuses = [s.casefold() for s in cfg.get("overdue_statuses", ["New"])]
    overdue_days = int(cfg.get("overdue_days", 5))
    if submitted is not None and (status or "").casefold() in overdue_statuses:
        age = (as_of - submitted).days
        if age > overdue_days:
            flags.append(
                ReviewFlag(
                    "OVERDUE",
                    "warning",
                    f"Still '{status}' after {age} days (threshold {overdue_days}); nobody has picked this up",
                )
            )

    flags.sort(key=lambda f: SEVERITY_ORDER.get(f.severity, 9))
    return flags


def needs_review(flags: list[ReviewFlag]) -> bool:
    return any(f.severity in REVIEW_SEVERITIES for f in flags)
