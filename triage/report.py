"""Output writers: CSV, JSON and Markdown summaries."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .models import TriageResult

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .pipeline import TriageRun

CSV_COLUMNS = [
    "Request ID",
    "Submitted Date",
    "Submitted Date (ISO)",
    "Requester Role",
    "Submitted Type",
    "Rule Category",
    "Confidence",
    "Matched Keywords",
    "Category Mismatch",
    "Valid",
    "Validation Issues",
    "Priority",
    "Channel",
    "Status",
    "Needs Human Review",
    "Review Flags",
    "Acknowledgement Source",
    "Acknowledgement",
]


def _yes_no(value: bool) -> str:
    return "Yes" if value else "No"


def result_row(result: TriageResult) -> dict[str, str]:
    req = result.request
    return {
        "Request ID": req.request_id,
        "Submitted Date": req.submitted_date,
        "Submitted Date (ISO)": result.submitted_date_iso or "",
        "Requester Role": req.requester_role,
        "Submitted Type": result.submitted_type,
        "Rule Category": result.category.category,
        "Confidence": result.category.confidence,
        "Matched Keywords": "; ".join(result.category.matched_keywords),
        "Category Mismatch": _yes_no(result.category_mismatch),
        "Valid": _yes_no(result.is_valid),
        "Validation Issues": "; ".join(i.message for i in result.validation_issues),
        "Priority": req.priority,
        "Channel": req.channel,
        "Status": req.status,
        "Needs Human Review": _yes_no(result.needs_human_review),
        "Review Flags": "; ".join(f"{f.code}: {f.reason}" for f in result.review_flags),
        "Acknowledgement Source": result.ack_source,
        "Acknowledgement": result.acknowledgement.strip(),
    }


def write_csv(results: list[TriageResult], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for result in results:
            writer.writerow(result_row(result))


def summarise(results: list[TriageResult]) -> dict[str, Any]:
    by_category = Counter(r.category.category for r in results)
    by_priority = Counter((r.request.priority or "Unspecified") for r in results)
    by_channel = Counter((r.request.channel or "Unspecified") for r in results)
    by_status = Counter((r.request.status or "Unspecified") for r in results)
    flag_counts = Counter(f.code for r in results for f in r.review_flags if f.severity != "info")
    ack_sources = Counter(r.ack_source for r in results)
    return {
        "total": len(results),
        "valid": sum(1 for r in results if r.is_valid),
        "invalid": sum(1 for r in results if not r.is_valid),
        "needs_human_review": sum(1 for r in results if r.needs_human_review),
        "auto_acknowledged": sum(1 for r in results if not r.needs_human_review),
        "category_mismatches": sum(1 for r in results if r.category_mismatch),
        "by_category": dict(by_category.most_common()),
        "by_priority": dict(by_priority.most_common()),
        "by_channel": dict(by_channel.most_common()),
        "by_status": dict(by_status.most_common()),
        "review_flags": dict(flag_counts.most_common()),
        "acknowledgement_sources": dict(ack_sources),
    }


def run_to_dict(run: "TriageRun") -> dict[str, Any]:
    return {
        "generated_at": run.generated_at,
        "input_file": run.input_name,
        "rules_version": run.rules_version,
        "as_of": run.as_of.isoformat(),
        "as_of_source": run.as_of_source,
        "ai_enabled": run.ai_enabled,
        "ai_provider": run.ai_provider,
        "columns_found": run.columns_found,
        "missing_columns": run.missing_columns,
        "ignored_columns": run.ignored_columns,
        "blank_rows_skipped": run.blank_rows_skipped,
        "summary": run.summary,
        "results": [r.to_dict() for r in run.results],
    }


def write_json(run: "TriageRun", path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(run_to_dict(run), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    def clean(cell: str) -> str:
        return str(cell).replace("|", "\\|").replace("\n", " ")

    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(" --- " for _ in headers) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(clean(c) for c in row) + " |")
    return "\n".join(lines)


def _counts_table(title: str, counts: dict[str, int]) -> str:
    rows = [[name, str(count)] for name, count in counts.items()]
    return f"### {title}\n\n" + _md_table(["Value", "Requests"], rows)


def summary_markdown(run: "TriageRun") -> str:
    s = run.summary
    lines: list[str] = []
    lines.append("# Service request triage summary")
    lines.append("")
    lines.append(f"Generated {run.generated_at} from `{run.input_name}` using rules v{run.rules_version}.")
    lines.append(f"Dates assessed as of **{run.as_of.isoformat()}** ({run.as_of_source}).")
    if run.ai_enabled:
        lines.append(f"AI acknowledgement drafting: **enabled** ({run.ai_provider}).")
    else:
        lines.append("AI acknowledgement drafting: **off** (template text only; no data left this machine).")
    lines.append("")
    lines.append("## Headline")
    lines.append("")
    lines.append(f"- Requests read: **{s['total']}**")
    lines.append(f"- Complete and valid: **{s['valid']}**; with missing or invalid information: **{s['invalid']}**")
    lines.append(f"- Needing human review: **{s['needs_human_review']}**; acknowledged automatically: **{s['auto_acknowledged']}**")
    lines.append(f"- Rule category differs from submitted type: **{s['category_mismatches']}**")
    sources = ", ".join(f"{k}: {v}" for k, v in s["acknowledgement_sources"].items())
    lines.append(f"- Acknowledgement source: {sources}")
    if run.missing_columns:
        lines.append(f"- Columns absent from the file: {', '.join(run.missing_columns)}")
    if run.ignored_columns:
        lines.append(f"- Columns ignored: {', '.join(run.ignored_columns)}")
    if run.blank_rows_skipped:
        lines.append(f"- Blank rows skipped: {run.blank_rows_skipped}")
    lines.append("")
    lines.append("## Breakdown")
    lines.append("")
    lines.append(_counts_table("By rule category", s["by_category"]))
    lines.append("")
    lines.append(_counts_table("By priority", s["by_priority"]))
    lines.append("")
    lines.append(_counts_table("By channel", s["by_channel"]))
    lines.append("")
    if s["review_flags"]:
        lines.append(_counts_table("Review flags raised", s["review_flags"]))
        lines.append("")

    lines.append("## Human review queue")
    lines.append("")
    queue = [r for r in run.results if r.needs_human_review]
    if not queue:
        lines.append("No requests need human review.")
    else:
        rows = []
        for r in queue:
            reasons = "<br>".join(f"**{f.code}** - {f.reason}" for f in r.review_flags if f.severity != "info")
            rows.append([r.request.display_id, r.request.priority or "-", r.category.category, reasons])
        lines.append(_md_table(["Request", "Priority", "Category", "Why it needs a person"], rows))
    lines.append("")

    lines.append("## All requests")
    lines.append("")
    rows = []
    for r in run.results:
        rows.append(
            [
                r.request.display_id,
                r.request.requester_role or "-",
                r.submitted_type or "(blank)",
                f"{r.category.category} ({r.category.confidence})",
                r.request.priority or "-",
                "Yes" if r.is_valid else "No",
                "Yes" if r.needs_human_review else "No",
                r.ack_source,
            ]
        )
    lines.append(_md_table(["Request", "Role", "Submitted type", "Rule category (confidence)", "Priority", "Valid", "Review", "Ack"], rows))
    lines.append("")

    invalid = [r for r in run.results if r.validation_issues]
    if invalid:
        lines.append("## Validation issues")
        lines.append("")
        rows = [[r.request.display_id, "<br>".join(i.message for i in r.validation_issues)] for r in invalid]
        lines.append(_md_table(["Request", "Issues"], rows))
        lines.append("")

    lines.append("## How categories were decided")
    lines.append("")
    rows = [[r.request.display_id, r.category.rationale] for r in run.results]
    lines.append(_md_table(["Request", "Rationale"], rows))
    lines.append("")
    return "\n".join(lines)


def acknowledgements_markdown(run: "TriageRun") -> str:
    lines = ["# Suggested acknowledgements", ""]
    lines.append(
        "One draft per request. Requests marked *needs human review* should be checked by a person before anything is sent."
    )
    lines.append("")
    for r in run.results:
        status = "needs human review" if r.needs_human_review else "ready to send"
        lines.append(f"## {r.request.display_id} - {r.category.category} - {status} - source: {r.ack_source}")
        if r.ai_note:
            lines.append("")
            lines.append(f"_AI note: {r.ai_note}_")
        lines.append("")
        lines.append("```text")
        lines.append(r.acknowledgement.strip())
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def write_markdown(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
