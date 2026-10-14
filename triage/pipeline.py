"""Orchestrates load -> validate -> categorise -> acknowledge -> review -> report."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable

from . import __version__
from .acknowledgement import build_acknowledgement, format_date, response_target
from .ai import AIDraftError, AISettings, describe_chain, draft_acknowledgement
from .guardrails import review_input
from .categoriser import categorise
from .config import DEFAULT_OUTPUT_DIR, load_ack_config, load_rules
from .loader import LoadResult, load_requests, parse_csv_text
from .models import Request, TriageResult
from .report import (
    acknowledgements_markdown,
    summarise,
    summary_markdown,
    write_csv,
    write_json,
    write_markdown,
)
from .review import assess, needs_review
from .validation import canonical_value, find_duplicate_ids, parse_date, validate

AI_BLOCKING_FLAGS = {"POSSIBLE_PERSONAL_DATA", "SENSITIVE_CONTENT"}


@dataclass
class TriageRun:
    results: list[TriageResult]
    as_of: date
    as_of_source: str
    generated_at: str
    input_name: str
    rules_version: str
    columns_found: list[str] = field(default_factory=list)
    missing_columns: list[str] = field(default_factory=list)
    ignored_columns: list[str] = field(default_factory=list)
    blank_rows_skipped: int = 0
    ai_enabled: bool = False
    ai_provider: str | None = None
    summary: dict[str, Any] = field(default_factory=dict)


def determine_as_of(requests: list[Request], rules: dict[str, Any], explicit: date | None = None) -> tuple[date, str]:
    """Pick the date used for 'future date' and 'overdue' checks.

    Default is the latest parseable submission date in the batch (ignoring any
    date after today, which is invalid data rather than a clue about when the
    batch was exported) so that committed outputs are reproducible. Pass
    ``explicit`` (e.g. today) for a live run.
    """
    if explicit is not None:
        return explicit, "specified"
    today = date.today()
    formats = rules["validation"]["date_formats"]
    dates = [d for d in (parse_date(r.submitted_date, formats) for r in requests) if d is not None and d <= today]
    if dates:
        return max(dates), "latest submission date in the batch"
    return today, "today"


def ai_eligible(result: TriageResult) -> tuple[bool, str | None]:
    """AI drafting is skipped when the summary may carry personal/sensitive data."""
    blocking = [f.code for f in result.review_flags if f.code in AI_BLOCKING_FLAGS]
    if blocking:
        return False, f"AI drafting skipped because of {', '.join(blocking)}; template used"
    if not result.request.request_summary.strip():
        return False, "AI drafting skipped because the summary is empty; template used"
    return True, None


def ai_facts(result: TriageResult, ack_config: dict[str, Any], submitted: date | None) -> dict[str, Any]:
    req = result.request
    unknown = ack_config.get("unknown_values", {})
    return {
        "request_id": req.request_id or unknown.get("request_id", "(reference pending)"),
        "submitted_date": format_date(submitted, unknown.get("submitted_date", "on an unrecorded date")),
        "channel": req.channel or unknown.get("channel", "an unrecorded channel"),
        "category": result.category.category,
        "priority": req.priority or unknown.get("priority", "standard"),
        "response_target": response_target(req.priority, ack_config),
        "request_summary": req.request_summary,
        "information_missing": sorted({i.field for i in result.validation_issues}),
        "team_name": ack_config.get("sender", "Digital Services Team"),
    }


def _as_chain(settings: AISettings | Sequence[AISettings]) -> list[AISettings]:
    if isinstance(settings, AISettings):
        return [settings]
    return list(settings)


def apply_ai(
    result: TriageResult,
    ack_config: dict[str, Any],
    settings: AISettings | Sequence[AISettings],
    *,
    opener: Callable[..., Any] | None = None,
) -> TriageResult:
    """Try each configured provider, then keep the template if they all fail.

    Groq is first when it is the selected provider. Azure OpenAI and OpenAI
    are only present in ``settings`` when their keys were set, so they act as
    the fallback rather than the default.
    """
    eligible, note = ai_eligible(result)
    if not eligible:
        result.ai_note = note
        return result
    blocked = review_input(result.request.request_summary)
    if blocked:
        result.ai_note = f"AI drafting skipped because of {blocked[0].code}; template used"
        return result
    submitted = date.fromisoformat(result.submitted_date_iso) if result.submitted_date_iso else None
    facts = ai_facts(result, ack_config, submitted)
    errors: list[str] = []
    for current in _as_chain(settings):
        try:
            text, model = draft_acknowledgement(facts, result.acknowledgement, current, opener=opener)
        except AIDraftError as exc:
            errors.append(f"{current.provider}: {exc}")
            continue
        result.acknowledgement = text
        result.ack_source = "ai"
        if errors:
            result.ai_note = (
                f"Drafted by {current.provider} model {model} after {'; '.join(errors)}; template kept as fallback"
            )
        else:
            result.ai_note = f"Drafted by {current.provider} model {model}; template kept as fallback"
        return result
    result.ai_note = f"AI drafting failed ({'; '.join(errors)}); template used"
    return result


def triage_requests(
    requests: list[Request],
    rules: dict[str, Any],
    ack_config: dict[str, Any],
    as_of: date,
    *,
    ai_settings: AISettings | Sequence[AISettings] | None = None,
    ai_opener: Callable[..., Any] | None = None,
) -> list[TriageResult]:
    validation_cfg = rules["validation"]
    duplicates = find_duplicate_ids(requests)
    results: list[TriageResult] = []

    for request in requests:
        issues = validate(request, rules, as_of)
        submitted = parse_date(request.submitted_date, validation_cfg["date_formats"])
        submitted_iso = submitted.isoformat() if submitted else None

        # Normalise casing of controlled values when they match an allowed option.
        priority = canonical_value(request.priority, validation_cfg.get("allowed_priorities", [])) or request.priority
        channel = canonical_value(request.channel, validation_cfg.get("allowed_channels", [])) or request.channel
        status = canonical_value(request.status, validation_cfg.get("allowed_statuses", [])) or request.status

        category = categorise(request.request_summary, rules)
        submitted_type = request.request_type.strip()
        mismatch = bool(submitted_type) and category.confidence != "none" and submitted_type.casefold() != category.category.casefold()

        acknowledgement = build_acknowledgement(
            request, category.category, submitted, issues, ack_config, priority=priority, channel=channel
        )
        flags = assess(
            request, issues, category, submitted, as_of, rules,
            duplicate_ids=duplicates, priority=priority, status=status,
        )

        result = TriageResult(
            request=request,
            submitted_date_iso=submitted_iso,
            is_valid=not issues,
            validation_issues=issues,
            category=category,
            submitted_type=submitted_type,
            category_mismatch=mismatch,
            acknowledgement=acknowledgement,
            ack_source="template",
            ai_note=None,
            needs_human_review=needs_review(flags),
            review_flags=flags,
        )
        if ai_settings is not None:
            apply_ai(result, ack_config, ai_settings, opener=ai_opener)
        results.append(result)

    return results


def _build_run(
    loaded: LoadResult,
    input_name: str,
    rules: dict[str, Any],
    ack_config: dict[str, Any],
    *,
    as_of: date | None,
    ai_settings: AISettings | Sequence[AISettings] | None,
    ai_opener: Callable[..., Any] | None,
) -> TriageRun:
    as_of_date, source = determine_as_of(loaded.requests, rules, as_of)
    chain = _as_chain(ai_settings) if ai_settings is not None else None
    results = triage_requests(loaded.requests, rules, ack_config, as_of_date, ai_settings=chain, ai_opener=ai_opener)
    run = TriageRun(
        results=results,
        as_of=as_of_date,
        as_of_source=source,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        input_name=input_name,
        rules_version=str(rules.get("version", __version__)),
        columns_found=loaded.columns_found,
        missing_columns=loaded.missing_columns,
        ignored_columns=loaded.ignored_columns,
        blank_rows_skipped=loaded.blank_rows_skipped,
        ai_enabled=chain is not None,
        ai_provider=describe_chain(chain) if chain else None,
    )
    run.summary = summarise(results)
    return run


def run(
    input_path: str | Path,
    *,
    as_of: date | None = None,
    ai_settings: AISettings | Sequence[AISettings] | None = None,
    rules_path: str | Path | None = None,
    ack_path: str | Path | None = None,
    ai_opener: Callable[..., Any] | None = None,
) -> TriageRun:
    rules = load_rules(rules_path)
    ack_config = load_ack_config(ack_path)
    loaded = load_requests(input_path)
    return _build_run(loaded, Path(input_path).name, rules, ack_config, as_of=as_of, ai_settings=ai_settings, ai_opener=ai_opener)


def run_from_text(
    csv_text: str,
    input_name: str = "upload.csv",
    *,
    as_of: date | None = None,
    ai_settings: AISettings | Sequence[AISettings] | None = None,
    rules: dict[str, Any] | None = None,
    ack_config: dict[str, Any] | None = None,
    ai_opener: Callable[..., Any] | None = None,
) -> TriageRun:
    rules = rules or load_rules()
    ack_config = ack_config or load_ack_config()
    loaded = parse_csv_text(csv_text)
    return _build_run(loaded, input_name, rules, ack_config, as_of=as_of, ai_settings=ai_settings, ai_opener=ai_opener)


def write_outputs(run_result: TriageRun, output_dir: str | Path | None = None) -> dict[str, Path]:
    out = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "csv": out / "triage_results.csv",
        "json": out / "triage_results.json",
        "summary": out / "summary.md",
        "acknowledgements": out / "acknowledgements.md",
    }
    write_csv(run_result.results, paths["csv"])
    write_json(run_result, paths["json"])
    write_markdown(summary_markdown(run_result), paths["summary"])
    write_markdown(acknowledgements_markdown(run_result), paths["acknowledgements"])
    return paths
