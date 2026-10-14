from datetime import date

from triage.categoriser import categorise
from triage.models import ValidationIssue
from triage.review import assess, detect_personal_data, needs_review


def flags_for(make_request, rules, as_of, *, issues=None, duplicates=None, **overrides):
    req = make_request(**overrides)
    category = categorise(req.request_summary, rules)
    submitted = date(2026, 10, 1) if req.submitted_date == "01/10/2026" else None
    return assess(req, issues or [], category, submitted, as_of, rules, duplicate_ids=duplicates or set())


def codes(flags):
    return [f.code for f in flags]


def test_clean_medium_priority_request_needs_no_review(make_request, rules, as_of):
    flags = flags_for(make_request, rules, as_of)
    assert not needs_review(flags), codes(flags)


def test_missing_information_is_critical(make_request, rules, as_of):
    flags = flags_for(make_request, rules, as_of, issues=[ValidationIssue("Priority", "missing", "x")])
    assert flags[0].code == "MISSING_OR_INVALID_INFO" and flags[0].severity == "critical"
    assert needs_review(flags)


def test_personal_data_and_credentials_are_detected(make_request, rules, as_of):
    summary = "Please reset the password for student j.bloggs@example.ac.uk (ID 12345678) who cannot log in."
    flags = flags_for(make_request, rules, as_of, request_summary=summary)
    assert "POSSIBLE_PERSONAL_DATA" in codes(flags)
    assert "CREDENTIALS" in codes(flags)
    kinds = detect_personal_data(summary, rules["review"]["personal_data_patterns"])
    assert "email address" in kinds and "ID number" in kinds
    # Reasons never echo the personal data itself.
    assert "j.bloggs" not in " ".join(f.reason for f in flags)


def test_sensitive_content_is_critical(make_request, rules, as_of):
    flags = flags_for(make_request, rules, as_of, request_summary="Record adjustments for a student who has disclosed a disability on the module page.")
    sensitive = [f for f in flags if f.code == "SENSITIVE_CONTENT"]
    assert sensitive and sensitive[0].severity == "critical"


def test_external_access_is_flagged_only_for_access_requests(make_request, rules, as_of):
    flags = flags_for(make_request, rules, as_of, request_summary="Set up controlled access for external collaborators to a project document library.")
    assert "EXTERNAL_ACCESS" in codes(flags)
    flags = flags_for(make_request, rules, as_of, request_summary="Publish a guide for external examiners about the intranet.")
    assert "EXTERNAL_ACCESS" not in codes(flags)


def test_high_priority_and_overdue(make_request, rules, as_of):
    flags = flags_for(make_request, rules, as_of, priority="High", status="New")
    assert "HIGH_PRIORITY" in codes(flags)
    assert "OVERDUE" in codes(flags)  # submitted 1 Oct, assessed 8 Oct, still New
    flags = flags_for(make_request, rules, as_of, priority="Medium", status="Assigned")
    assert "OVERDUE" not in codes(flags)


def test_category_mismatch_and_blank_type(make_request, rules, as_of):
    flags = flags_for(make_request, rules, as_of, request_type="Content & Guidance", request_summary="Automate the weekly export of attendance data into the reporting dashboard.")
    assert "CATEGORY_MISMATCH" in codes(flags)
    flags = flags_for(make_request, rules, as_of, request_type="")
    info = [f for f in flags if f.code == "CATEGORY_ASSIGNED"]
    assert info and info[0].severity == "info"
    assert not needs_review(flags)


def test_duplicate_id_and_uncategorised(make_request, rules, as_of):
    flags = flags_for(make_request, rules, as_of, duplicates={"REQ-001"}, request_summary="Need help with something please.", request_type="")
    assert "DUPLICATE_ID" in codes(flags)
    assert "UNCATEGORISED" in codes(flags)


def test_flags_are_ordered_by_severity(make_request, rules, as_of):
    flags = flags_for(make_request, rules, as_of, priority="High", issues=[ValidationIssue("Priority", "missing", "x")])
    severities = [f.severity for f in flags]
    assert severities == sorted(severities, key={"critical": 0, "warning": 1, "info": 2}.get)
