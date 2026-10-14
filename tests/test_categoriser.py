import pytest

from tests.conftest import SAMPLE_CSV
from triage.categoriser import categorise, category_names
from triage.loader import load_requests


def sample_rows():
    return [(r.request_id, r.request_summary, r.request_type) for r in load_requests(SAMPLE_CSV).requests]


@pytest.mark.parametrize("request_id,summary,expected", sample_rows())
def test_rules_reproduce_the_submitted_type_for_every_sample_row(rules, request_id, summary, expected):
    result = categorise(summary, rules)
    assert result.category == expected, f"{request_id}: {result.rationale}"
    assert result.confidence in {"high", "medium"}
    assert result.matched_keywords


def test_no_keywords_means_uncategorised(rules):
    result = categorise("Need help with something please.", rules)
    assert result.category == "Uncategorised"
    assert result.confidence == "none"


def test_empty_summary_is_uncategorised(rules):
    assert categorise("", rules).confidence == "none"


def test_keywords_match_whole_words_only(rules):
    # "rapid" must not trigger the "api" keyword.
    result = categorise("A rapid response is needed for the reminders.", rules)
    assert "api" not in result.matched_keywords
    assert result.category == "Process Automation"


def test_tie_is_broken_by_opening_verb_and_marked_low_confidence(rules):
    result = categorise("Connect the purchase order form to the finance approval workflow.", rules)
    assert result.category == "System Integration"
    assert result.confidence == "low"
    assert "opens with" in result.rationale


def test_result_exposes_scores_for_every_category(rules):
    result = categorise("Create a dashboard showing module engagement.", rules)
    assert set(result.scores) == set(category_names(rules)) - {"Uncategorised"}
    assert result.scores["Reporting & Analytics"] > result.scores["Content & Guidance"]
