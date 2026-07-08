"""Slice-1 DoD scenarios, driven only through the pipeline seam.

No test reaches into parser or threshold internals - fixture payloads plus
prior state in, assertions on state/changeset/changed out.
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from dashboard import render_dashboard
from pipeline import run_pipeline

FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 7, 8, tzinfo=timezone.utc)

MIXED = "gdacs_orange_red_green.json"
ALL_GREEN = "gdacs_all_green.json"

RED_ID = "gdacs-TC-1001279"  # Tropical Cyclone BAVI-26, Red
ORANGE_ID = "gdacs-EQ-1550684"  # Earthquake in Northern Molucca Sea, Orange
TEMPORARY_ID = "gdacs-EQ-1550675"  # Orange but istemporary
NO_ALERT_ID = "gdacs-EQ-1550674"  # empty alertlevel


def payload(name):
    return {"gdacs": (FIXTURES / name).read_bytes()}


def test_orange_plus_crosses_threshold():
    result = run_pipeline(payload(MIXED), {}, NOW)
    assert result.changed is True
    assert {e["disaster_id"] for e in result.changeset} == {RED_ID, ORANGE_ID}
    assert all(e["kind"] == "new" for e in result.changeset)
    assert set(result.state["disasters"]) == {RED_ID, ORANGE_ID}


def test_green_only_is_unchanged():
    result = run_pipeline(payload(ALL_GREEN), {}, NOW)
    assert result.changed is False
    assert result.changeset == []
    assert result.state["disasters"] == {}


def test_resurfaced_event_not_reannounced():
    first = run_pipeline(payload(MIXED), {}, NOW)
    later = datetime(2026, 7, 8, 6, tzinfo=timezone.utc)
    second = run_pipeline(payload(MIXED), first.state, later)
    assert second.changed is False
    assert second.changeset == []
    assert second.state == first.state


def test_malformed_payload_raises():
    with pytest.raises(ValueError):
        run_pipeline({"gdacs": b"<html>oops"}, {}, NOW)


def test_missing_alertlevel_not_surfaced():
    result = run_pipeline(payload(MIXED), {}, NOW)
    assert NO_ALERT_ID not in result.state["disasters"]


def test_temporary_event_skipped():
    result = run_pipeline(payload(MIXED), {}, NOW)
    assert TEMPORARY_ID not in result.state["disasters"]


def test_dashboard_orders_red_first_and_tags_new():
    result = run_pipeline(payload(MIXED), {}, NOW)
    page = render_dashboard(result.state, result.changeset)
    assert page.index("Tropical Cyclone BAVI-26") < page.index(
        "Earthquake in Northern Molucca Sea"
    )
    assert "NEW" in page
