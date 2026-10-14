import csv
import json
from datetime import date

from tests.conftest import AS_OF, EDGE_CSV, SAMPLE_CSV
from triage.loader import load_requests
from triage.pipeline import determine_as_of, run, run_from_text, write_outputs


def test_sample_batch_end_to_end(tmp_path):
    result = run(SAMPLE_CSV, as_of=AS_OF)
    s = result.summary
    assert s["total"] == 10 and s["valid"] == 10 and s["category_mismatches"] == 0
    assert s["needs_human_review"] == 6 and s["auto_acknowledged"] == 4
    assert set(s["by_category"]) == {"Access & Permissions", "Process Automation", "Reporting & Analytics", "System Integration", "Content & Guidance"}
    assert s["acknowledgement_sources"] == {"template": 10}

    paths = write_outputs(result, tmp_path)
    assert {p.name for p in paths.values()} == {"triage_results.csv", "triage_results.json", "summary.md", "acknowledgements.md"}
    with paths["csv"].open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 10
    assert rows[0]["Request ID"] == "REQ-001" and rows[0]["Needs Human Review"] == "Yes"
    data = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert data["summary"]["total"] == 10 and len(data["results"]) == 10
    assert "Human review queue" in paths["summary"].read_text(encoding="utf-8")


def test_edge_case_batch_flags_every_deliberate_defect():
    result = run(EDGE_CSV, as_of=AS_OF)
    by_id = {}
    for r in result.results:
        by_id.setdefault(r.request.request_id, r)
    flags = {rid: {f.code for f in r.review_flags} for rid, r in by_id.items()}

    assert "MISSING_OR_INVALID_INFO" in flags["REQ-101"]  # blank role
    assert "UNCATEGORISED" in flags["REQ-102"]  # blank summary
    assert "MISSING_OR_INVALID_INFO" in flags["REQ-103"]  # 31 Feb
    assert "MISSING_OR_INVALID_INFO" in flags["REQ-104"]  # future date
    assert "MISSING_OR_INVALID_INFO" in flags["REQ-105"]  # priority "Urgent"
    assert "UNCATEGORISED" in flags["REQ-106"]
    assert {"POSSIBLE_PERSONAL_DATA", "CREDENTIALS"} <= flags["REQ-107"]
    assert {"DUPLICATE_ID", "CATEGORY_MISMATCH"} <= flags["REQ-108"]
    assert "EXTERNAL_ACCESS" in flags["REQ-109"]
    assert "OVERDUE" in flags["REQ-110"]
    assert "LOW_CONFIDENCE" in flags["REQ-111"]
    assert "CATEGORY_ASSIGNED" in flags["REQ-112"] and not by_id["REQ-112"].needs_human_review
    assert "SENSITIVE_CONTENT" in flags["REQ-113"]
    assert "MISSING_OR_INVALID_INFO" in flags[""]  # blank request id
    assert result.summary["invalid"] == 7


def test_default_as_of_ignores_future_dates(rules):
    requests = load_requests(EDGE_CSV).requests
    as_of, source = determine_as_of(requests, rules)
    assert as_of == date(2026, 10, 8)
    assert source == "latest submission date in the batch"
    assert determine_as_of(requests, rules, date(2026, 10, 13)) == (date(2026, 10, 13), "specified")


def test_run_from_text_normalises_controlled_values():
    text = "Request ID,Submitted Date,Requester Role,Request Type,Request Summary,Priority,Channel,Status\nREQ-500,07/10/2026,Lecturer,,Publish a guide to the new intranet pages for staff.,low,teams,assigned\n"
    result = run_from_text(text, "inline.csv", as_of=AS_OF)
    r = result.results[0]
    assert r.is_valid  # lower-case controlled values are accepted
    assert r.category.category == "Content & Guidance"
    assert "5 working days" in r.acknowledgement  # low -> Low
    assert not r.needs_human_review
    assert [f.code for f in r.review_flags] == ["CATEGORY_ASSIGNED"]
