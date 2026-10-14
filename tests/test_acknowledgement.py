from datetime import date

from triage.acknowledgement import build_acknowledgement, response_target
from triage.models import ValidationIssue


def test_response_target_follows_priority(ack_config):
    assert response_target("High", ack_config) == "1 working day"
    assert response_target("medium", ack_config) == "3 working days"
    assert response_target("", ack_config) == "5 working days"


def test_acknowledgement_contains_key_facts(make_request, ack_config):
    text = build_acknowledgement(make_request(), "Access & Permissions", date(2026, 10, 1), [], ack_config)
    assert "REQ-001" in text
    assert "1 October 2026" in text
    assert "Service Portal" in text
    assert "Access & Permissions" in text
    assert "3 working days" in text
    assert "data protection" in text  # category-specific note
    assert "\n\n\n" not in text


def test_incomplete_requests_get_a_follow_up_note(make_request, ack_config):
    issues = [ValidationIssue("Requester Role", "missing", "x"), ValidationIssue("Priority", "invalid", "y")]
    text = build_acknowledgement(make_request(request_id="", priority="Urgent"), "Process Automation", None, issues, ack_config)
    assert "(reference pending)" in text
    assert "on an unrecorded date" in text
    assert "missing or invalid (Priority, Requester Role)" in text


def test_uncategorised_requests_say_a_person_will_review(make_request, ack_config):
    text = build_acknowledgement(make_request(), "Uncategorised", date(2026, 10, 1), [], ack_config)
    assert "could not automatically determine" in text
