from datetime import date

from triage.validation import canonical_value, find_duplicate_ids, parse_date, validate


def issues_by_field(issues):
    return {(i.field, i.problem) for i in issues}


def test_complete_request_has_no_issues(make_request, rules, as_of):
    assert validate(make_request(), rules, as_of) == []


def test_missing_required_fields_are_reported(make_request, rules, as_of):
    req = make_request(requester_role="", request_summary="", priority="")
    found = issues_by_field(validate(req, rules, as_of))
    assert ("Requester Role", "missing") in found
    assert ("Request Summary", "missing") in found
    assert ("Priority", "missing") in found


def test_request_type_is_optional(make_request, rules, as_of):
    assert validate(make_request(request_type=""), rules, as_of) == []


def test_invalid_and_future_dates_are_reported(make_request, rules, as_of):
    invalid = validate(make_request(submitted_date="31/02/2026"), rules, as_of)
    assert ("Submitted Date", "invalid") in issues_by_field(invalid)
    future = validate(make_request(submitted_date="01/12/2026"), rules, as_of)
    assert any("after the assessment date" in i.message for i in future)


def test_iso_dates_are_accepted(make_request, rules, as_of):
    assert validate(make_request(submitted_date="2026-10-07"), rules, as_of) == []
    assert parse_date("2026-10-07", rules["validation"]["date_formats"]) == date(2026, 10, 7)


def test_controlled_values_and_short_summary(make_request, rules, as_of):
    req = make_request(priority="Urgent", channel="Fax", status="Done", request_summary="Dashboard")
    found = issues_by_field(validate(req, rules, as_of))
    assert ("Priority", "invalid") in found
    assert ("Channel", "invalid") in found
    assert ("Status", "invalid") in found
    assert ("Request Summary", "invalid") in found


def test_controlled_values_are_case_insensitive(make_request, rules, as_of):
    assert validate(make_request(priority="high", channel="teams"), rules, as_of) == []
    assert canonical_value("high", rules["validation"]["allowed_priorities"]) == "High"


def test_request_id_format(make_request, rules, as_of):
    assert ("Request ID", "invalid") in issues_by_field(validate(make_request(request_id="TICKET1"), rules, as_of))


def test_duplicate_ids_are_found(make_request):
    requests = [make_request(request_id="REQ-108"), make_request(request_id="REQ-108"), make_request(request_id="REQ-109")]
    assert find_duplicate_ids(requests) == {"REQ-108"}
