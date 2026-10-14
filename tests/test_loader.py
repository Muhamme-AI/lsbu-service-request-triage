import pytest

from tests.conftest import SAMPLE_CSV
from triage.loader import LoaderError, load_requests, parse_csv_text


def test_supplied_sample_loads_ten_requests_and_strips_bom():
    loaded = load_requests(SAMPLE_CSV)
    assert len(loaded.requests) == 10
    assert loaded.missing_columns == []
    # The supplied file begins with a UTF-8 BOM; the first header must still be recognised.
    assert loaded.requests[0].request_id == "REQ-001"
    assert loaded.requests[0].row_number == 2


def test_header_aliases_and_whitespace_are_tolerated():
    text = "ID , Date,Role,Summary,PRIORITY,channel,Status\nREQ-9,01/10/2026,Lecturer,  Create a   dashboard  ,high,Teams,New\n"
    loaded = parse_csv_text(text)
    assert len(loaded.requests) == 1
    req = loaded.requests[0]
    assert req.request_id == "REQ-9"
    assert req.request_summary == "Create a dashboard"  # internal whitespace collapsed
    assert req.priority == "high"
    assert loaded.missing_columns == ["Request Type"]


def test_blank_rows_are_skipped_and_unknown_columns_ignored():
    text = "Request ID,Request Summary,Extra Column\nREQ-1,Automate reminders,ignored\n,,\n\nREQ-2,Publish a guide,x\n"
    loaded = parse_csv_text(text)
    assert [r.request_id for r in loaded.requests] == ["REQ-1", "REQ-2"]
    assert loaded.blank_rows_skipped == 2  # one row of empty cells, one empty line
    assert loaded.ignored_columns == ["Extra Column"]


def test_file_without_summary_column_is_rejected_with_clear_message():
    with pytest.raises(LoaderError) as excinfo:
        parse_csv_text("Name,Email\nJo,jo@example.com\n")
    assert "Request Summary" in str(excinfo.value)


def test_empty_file_is_rejected():
    with pytest.raises(LoaderError):
        parse_csv_text("")
