"""Plain data classes shared by the triage modules."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


# Maps the human-readable column label used in the CSV and in rules.json to
# the attribute name on ``Request``.
FIELD_ATTRIBUTES: dict[str, str] = {
    "Request ID": "request_id",
    "Submitted Date": "submitted_date",
    "Requester Role": "requester_role",
    "Request Type": "request_type",
    "Request Summary": "request_summary",
    "Priority": "priority",
    "Channel": "channel",
    "Status": "status",
}


@dataclass
class Request:
    """One row from the input spreadsheet, with whitespace trimmed."""

    row_number: int
    request_id: str = ""
    submitted_date: str = ""
    requester_role: str = ""
    request_type: str = ""
    request_summary: str = ""
    priority: str = ""
    channel: str = ""
    status: str = ""

    @property
    def display_id(self) -> str:
        return self.request_id or f"(row {self.row_number})"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationIssue:
    field: str
    problem: str  # "missing" or "invalid"
    message: str


@dataclass
class CategoryResult:
    category: str
    confidence: str  # "high", "medium", "low" or "none"
    score: int
    matched_keywords: list[str] = field(default_factory=list)
    scores: dict[str, int] = field(default_factory=dict)
    rationale: str = ""


@dataclass
class ReviewFlag:
    code: str
    severity: str  # "info", "warning" or "critical"
    reason: str


@dataclass
class TriageResult:
    request: Request
    submitted_date_iso: str | None
    is_valid: bool
    validation_issues: list[ValidationIssue]
    category: CategoryResult
    submitted_type: str
    category_mismatch: bool
    acknowledgement: str
    ack_source: str  # "template" or "ai"
    ai_note: str | None
    needs_human_review: bool
    review_flags: list[ReviewFlag]

    def to_dict(self) -> dict[str, Any]:
        return {
            "request": self.request.to_dict(),
            "submitted_date_iso": self.submitted_date_iso,
            "is_valid": self.is_valid,
            "validation_issues": [asdict(i) for i in self.validation_issues],
            "category": asdict(self.category),
            "submitted_type": self.submitted_type,
            "category_mismatch": self.category_mismatch,
            "acknowledgement": self.acknowledgement,
            "ack_source": self.ack_source,
            "ai_note": self.ai_note,
            "needs_human_review": self.needs_human_review,
            "review_flags": [asdict(f) for f in self.review_flags],
        }
