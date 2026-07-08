"""Slice-3 DoD scenarios: the change lifecycle and staleness (issue #5).

Still driven only through the pipeline seam. Variant payloads are built by
mutating the checked-in fixture captures in memory - the seam always sees
raw bytes.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from pipeline import run_pipeline

FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 7, 8, tzinfo=timezone.utc)
LATER = datetime(2026, 7, 8, 6, tzinfo=timezone.utc)

MOLUCCA_ID = "gdacs-EQ-1550684"  # Orange EQ in the mixed GDACS fixture
BAVI_ID = "gdacs-TC-1001279"  # Red TC, GLIDE TC-2026-000099-GUM
TOBELO_ID = "usgs-EQ-us6000talg"  # M6.4 unscored in the USGS fixture
NZ_ID = "usgs-EQ-us6000tasa"  # PAGER yellow in the USGS fixture


def fixture_bytes(name):
    return (FIXTURES / name).read_bytes()


def gdacs_variant(eventid, **props):
    data = json.loads(fixture_bytes("gdacs_orange_red_green.json"))
    feature = next(f for f in data["features"] if f["properties"]["eventid"] == eventid)
    feature["properties"].update(props)
    return json.dumps(data).encode("utf-8")


def usgs_variant(feature_id, **props):
    data = json.loads(fixture_bytes("usgs_mixed.json"))
    feature = next(f for f in data["features"] if f["id"] == feature_id)
    feature["properties"].update(props)
    return json.dumps(data).encode("utf-8")


def kinds(result):
    return [(e["kind"], e["disaster_id"]) for e in result.changeset]


def test_new_episode_escalation_breaks_silence():
    first = run_pipeline({"gdacs": fixture_bytes("gdacs_orange_red_green.json")}, {}, NOW)
    escalated = gdacs_variant(
        1550684,
        alertlevel="Red",
        episodeid=1716999,
        episodealertlevel="Red",
        alertscore=3,
    )
    second = run_pipeline({"gdacs": escalated}, first.state, LATER)
    assert kinds(second) == [("escalation", MOLUCCA_ID)]
    assert second.changed is True
    disaster = second.state["disasters"][MOLUCCA_ID]
    assert disaster["severity"] == "Red"
    assert disaster["last_changed"] == LATER.isoformat()


def test_within_tier_wobble_stays_quiet():
    first = run_pipeline({"gdacs": fixture_bytes("gdacs_orange_red_green.json")}, {}, NOW)
    wobble = gdacs_variant(1550684, episodealertscore=2.3, alertscore=2)
    second = run_pipeline({"gdacs": wobble}, first.state, LATER)
    assert second.changeset == []
    assert second.changed is False
    assert second.state["disasters"][MOLUCCA_ID]["last_changed"] == NOW.isoformat()


def test_usgs_deletion_retracts_surfaced_disaster():
    first = run_pipeline({"usgs": fixture_bytes("usgs_mixed.json")}, {}, NOW)
    assert TOBELO_ID in first.state["disasters"]
    deleted = usgs_variant("us6000talg", status="deleted")
    second = run_pipeline({"usgs": deleted}, first.state, LATER)
    assert kinds(second) == [("retraction", TOBELO_ID)]
    assert second.changed is True
    assert second.state["disasters"][TOBELO_ID]["status"] == "retracted"
    # the same deletion seen again tomorrow is not re-announced
    third = run_pipeline({"usgs": deleted}, second.state, LATER)
    assert third.changeset == []


def test_within_tier_magnitude_revision_is_a_correction_not_a_trigger():
    first = run_pipeline({"usgs": fixture_bytes("usgs_mixed.json")}, {}, NOW)
    revised = usgs_variant("us6000tasa", mag=6.0)  # still PAGER yellow
    second = run_pipeline({"usgs": revised}, first.state, LATER)
    assert second.changeset == []
    assert second.changed is False
    disaster = second.state["disasters"][NZ_ID]
    assert disaster["corrections"][-1]["note"] == "magnitude revised M5.8 to M6.0"
    assert disaster["last_changed"] == NOW.isoformat()  # corrections amend forward


def test_new_reliefweb_report_on_known_disaster_breaks_silence():
    first = run_pipeline({"gdacs": fixture_bytes("gdacs_orange_red_green.json")}, {}, NOW)
    second = run_pipeline(
        {
            "gdacs": fixture_bytes("gdacs_orange_red_green.json"),
            "reliefweb": fixture_bytes("reliefweb_mixed.xml"),
        },
        first.state,
        LATER,
    )
    assert second.changed is True
    assert ("new_report", BAVI_ID) in kinds(second)
    assert second.state["disasters"][BAVI_ID]["last_changed"] == LATER.isoformat()


def test_stale_feed_warns_even_on_a_quiet_morning():
    much_later = datetime(2026, 7, 9, 12, tzinfo=timezone.utc)
    first = run_pipeline({"usgs": fixture_bytes("usgs_mixed.json")}, {}, NOW)
    second = run_pipeline({"usgs": fixture_bytes("usgs_mixed.json")}, first.state, much_later)
    assert second.changed is False
    assert any(w.startswith("usgs feed stale") for w in second.warnings)


def test_fresh_feed_produces_no_warning():
    early = datetime(2026, 7, 8, 5, tzinfo=timezone.utc)  # newest gdacs record ~03:05
    result = run_pipeline({"gdacs": fixture_bytes("gdacs_orange_red_green.json")}, {}, early)
    assert not any("gdacs" in w for w in result.warnings)


def test_unavailable_feed_warns_without_crashing():
    result = run_pipeline({"gdacs": None}, {}, NOW)
    assert result.changed is False
    assert result.warnings == ["gdacs feed unavailable this run"]
