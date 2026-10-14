"""Reading requests from CSV text or files.

Design notes
------------
* The supplied sample file starts with a UTF-8 byte-order mark, so files are
  opened with ``utf-8-sig``; the BOM is also stripped from header text in case
  the CSV arrives as an in-memory string.
* Header matching is case- and whitespace-insensitive and accepts a few common
  aliases, so a spreadsheet exported with slightly different headings still
  loads. Unknown columns are ignored; missing columns become empty values and
  are reported by validation rather than crashing the run.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO

from .models import FIELD_ATTRIBUTES, Request

HEADER_ALIASES: dict[str, str] = {
    "request id": "request_id",
    "requestid": "request_id",
    "id": "request_id",
    "reference": "request_id",
    "submitted date": "submitted_date",
    "submitted": "submitted_date",
    "date submitted": "submitted_date",
    "date": "submitted_date",
    "requester role": "requester_role",
    "requester": "requester_role",
    "role": "requester_role",
    "request type": "request_type",
    "type": "request_type",
    "category": "request_type",
    "request summary": "request_summary",
    "summary": "request_summary",
    "description": "request_summary",
    "details": "request_summary",
    "priority": "priority",
    "channel": "channel",
    "source": "channel",
    "status": "status",
}

ATTRIBUTE_LABELS = {attr: label for label, attr in FIELD_ATTRIBUTES.items()}


class LoaderError(Exception):
    """Raised when the CSV cannot be interpreted as a request list."""


@dataclass
class LoadResult:
    requests: list[Request]
    columns_found: list[str] = field(default_factory=list)
    missing_columns: list[str] = field(default_factory=list)
    ignored_columns: list[str] = field(default_factory=list)
    blank_rows_skipped: int = 0


def normalise_header(header: str | None) -> str:
    if header is None:
        return ""
    return " ".join(header.replace("\ufeff", "").strip().lower().split())


def map_headers(headers: list[str]) -> tuple[dict[int, str], list[str]]:
    """Return {column index: attribute} plus the list of ignored header names."""
    mapping: dict[int, str] = {}
    ignored: list[str] = []
    seen: set[str] = set()
    for index, header in enumerate(headers):
        attr = HEADER_ALIASES.get(normalise_header(header))
        if attr and attr not in seen:
            mapping[index] = attr
            seen.add(attr)
        elif header is not None and header.strip():
            ignored.append(header.strip())
    return mapping, ignored


def parse_csv_text(text: str) -> LoadResult:
    text = text.lstrip("\ufeff")
    reader = csv.reader(io.StringIO(text))
    try:
        headers = next(reader)
    except StopIteration as exc:
        raise LoaderError("The CSV file is empty") from exc

    mapping, ignored = map_headers(headers)
    found_attrs = set(mapping.values())
    if "request_summary" not in found_attrs:
        found = ", ".join(sorted(ATTRIBUTE_LABELS[a] for a in found_attrs)) or "none"
        raise LoaderError(
            "The CSV does not contain a 'Request Summary' column, so it does not "
            f"look like a request list (recognised columns: {found})."
        )

    requests: list[Request] = []
    blank_rows = 0
    for row_number, row in enumerate(reader, start=2):  # row 1 is the header
        if not any(cell.strip() for cell in row):
            blank_rows += 1
            continue
        values = {attr: "" for attr in FIELD_ATTRIBUTES.values()}
        for index, attr in mapping.items():
            if index < len(row):
                values[attr] = " ".join(row[index].split())
        requests.append(Request(row_number=row_number, **values))

    missing = [label for label, attr in FIELD_ATTRIBUTES.items() if attr not in found_attrs]
    columns_found = [ATTRIBUTE_LABELS[a] for a in FIELD_ATTRIBUTES.values() if a in found_attrs]
    return LoadResult(
        requests=requests,
        columns_found=columns_found,
        missing_columns=missing,
        ignored_columns=ignored,
        blank_rows_skipped=blank_rows,
    )


def load_requests(source: str | Path | IO[str] | IO[bytes]) -> LoadResult:
    """Load requests from a file path or an open text/bytes stream."""
    if isinstance(source, (str, Path)):
        path = Path(source)
        if not path.exists():
            raise LoaderError(f"Input file not found: {path}")
        text = path.read_text(encoding="utf-8-sig")
        return parse_csv_text(text)

    data = source.read()
    if isinstance(data, bytes):
        text = data.decode("utf-8-sig")
    else:
        text = data
    return parse_csv_text(text)
