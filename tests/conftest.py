"""Shared fixtures for the triage test-suite."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from triage.config import load_ack_config, load_rules  # noqa: E402
from triage.models import Request  # noqa: E402

DATA_DIR = PROJECT_ROOT / "data"
SAMPLE_CSV = DATA_DIR / "requests.csv"
EDGE_CSV = DATA_DIR / "requests_edge_cases.csv"

# The latest submission date in the supplied sample file. Tests pass it
# explicitly so results never depend on the day they are run.
AS_OF = date(2026, 10, 8)


@pytest.fixture(scope="session")
def rules():
    return load_rules()


@pytest.fixture(scope="session")
def ack_config():
    return load_ack_config()


@pytest.fixture
def as_of():
    return AS_OF


@pytest.fixture
def make_request():
    def _make(**overrides) -> Request:
        base = dict(
            row_number=2,
            request_id="REQ-001",
            submitted_date="01/10/2026",
            requester_role="Student Services Officer",
            request_type="Access & Permissions",
            request_summary="Request access to the student enquiries dashboard for weekly reporting.",
            priority="Medium",
            channel="Service Portal",
            status="Assigned",
        )
        base.update(overrides)
        return Request(**base)

    return _make
