"""Checks on text before it is sent to a model, and on the reply before it is kept.

A failed check never becomes the acknowledgement. The caller keeps the template.
The same checks are the cases in ``python -m triage.evals``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Same shapes as config/rules.json. The reason names the kind of data, never the value.
OUTPUT_PERSONAL_DATA = {
    "email address": r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+",
    "phone number": r"(?:\+44\s?\d{3,4}|\(?0\d{3,4}\)?)\s?\d{3}\s?\d{3,4}",
    "national insurance number": r"\b[A-CEGHJ-PR-TW-Z]{2}\s?\d{2}\s?\d{2}\s?\d{2}\s?[A-D]\b",
    "ID number": r"\b\d{7,9}\b",
}

INJECTION_PATTERNS = (
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"disregard\s+(the\s+|your\s+)?(system|rules|instructions)",
    r"you\s+are\s+now",
    r"system\s+prompt",
    r"<\s*/?\s*script",
    r"<\s*/?\s*iframe",
)

MIN_RESPONSE_CHARS = 40
MAX_RESPONSE_CHARS = 1500


@dataclass(frozen=True)
class Breach:
    code: str
    message: str


def _clean(text: str) -> str:
    return re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text or "").strip()


def _matches(text: str, pattern: str) -> bool:
    try:
        return re.search(pattern, text, re.IGNORECASE) is not None
    except re.error:
        return False


def review_input(summary: str) -> list[Breach]:
    """Block a model call when the summary tries to override the instructions."""
    text = _clean(summary)
    if not text:
        return [Breach("EMPTY_SUMMARY", "the summary is empty")]
    for pattern in INJECTION_PATTERNS:
        if _matches(text, pattern):
            return [Breach("PROMPT_INJECTION", "the summary tries to override the instructions")]
    return []


def review_output(text: str, *, request_id: str = "", team_name: str = "") -> list[Breach]:
    """Reject a model reply that is the wrong shape, leaks data, or follows an injection."""
    cleaned = _clean(text)
    breaches: list[Breach] = []
    if len(cleaned) < MIN_RESPONSE_CHARS:
        breaches.append(Breach("TOO_SHORT", "AI reply was empty or too short"))
    if len(cleaned) > MAX_RESPONSE_CHARS:
        breaches.append(Breach("TOO_LONG", f"AI reply exceeded {MAX_RESPONSE_CHARS} characters"))
    if request_id and request_id not in cleaned:
        breaches.append(Breach("MISSING_REFERENCE", "AI reply did not quote the request reference"))
    other_ids = [found for found in re.findall(r"REQ-\d+", cleaned) if found != request_id]
    if other_ids:
        breaches.append(Breach("WRONG_REFERENCE", "AI reply quoted a different request reference"))
    lowered = cleaned.lower()
    if "```" in cleaned or lowered.startswith("subject:") or re.search(r"<\s*/?\s*[a-z][^>]*>", cleaned, re.IGNORECASE):
        breaches.append(Breach("NOT_PLAIN_TEXT", "AI reply was not plain text"))
    if cleaned and not lowered.startswith("dear colleague"):
        breaches.append(Breach("WRONG_OPENING", "AI reply did not start with the required greeting"))
    if team_name and team_name.lower() not in lowered:
        breaches.append(Breach("MISSING_SIGN_OFF", "AI reply did not use the team name"))
    for label, pattern in OUTPUT_PERSONAL_DATA.items():
        if _matches(cleaned, pattern):
            breaches.append(Breach("PERSONAL_DATA", f"AI reply contained a {label}"))
            break
    if re.search(r"\bpassword\b", cleaned, re.IGNORECASE):
        breaches.append(Breach("CREDENTIAL", "AI reply repeated a credential"))
    for pattern in INJECTION_PATTERNS:
        if _matches(cleaned, pattern):
            breaches.append(Breach("PROMPT_INJECTION", "AI reply followed an instruction from the request"))
            break
    return breaches
