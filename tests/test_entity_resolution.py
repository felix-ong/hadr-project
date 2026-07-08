"""Slice-2 DoD scenarios: three feeds, one Disaster (issue #4).

Still driven only through the pipeline seam - fixture payloads plus prior
state in, assertions on state/changeset/changed out.
"""

from datetime import datetime, timezone
from pathlib import Path

from dashboard import render_dashboard
from pipeline import run_pipeline

FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 7, 8, tzinfo=timezone.utc)

BAVI_ID = "gdacs-TC-1001279"  # Red TC, GLIDE TC-2026-000099-GUM
MOLUCCA_ID = "gdacs-EQ-1550684"  # Orange EQ at (126.36, 1.40)


def payloads(**names):
    return {
        feed: (FIXTURES / name).read_bytes() for feed, name in names.items()
    }


def run(**names):
    return run_pipeline(payloads(**names), {}, NOW)


ALL_THREE = dict(
    gdacs="gdacs_orange_red_green.json",
    usgs="usgs_mixed.json",
    reliefweb="reliefweb_mixed.xml",
)


def test_glide_match_merges_across_feeds():
    result = run(**ALL_THREE)
    bavi = result.state["disasters"][BAVI_ID]
    assert {r["feed"] for r in bavi["reports"]} == {"gdacs", "reliefweb"}
    # the ReliefWeb Report merged in - it must not appear as its own Disaster
    assert "reliefweb-tc-2026-000099-gum" not in result.state["disasters"]
    assert bavi["severity"] == "Red"


def test_proximity_match_merges_without_glide():
    result = run(**ALL_THREE)
    molucca = result.state["disasters"][MOLUCCA_ID]
    assert {r["feed"] for r in molucca["reports"]} == {"gdacs", "usgs"}
    assert "usgs-EQ-us6000talg" not in result.state["disasters"]
    assert molucca["severity"] == "Orange"  # GDACS Orange outranks the USGS Yellow


def test_merged_disaster_announced_once():
    result = run(**ALL_THREE)
    announced = [e["disaster_id"] for e in result.changeset]
    assert announced.count(BAVI_ID) == 1
    assert announced.count(MOLUCCA_ID) == 1


def test_usgs_pager_yellow_surfaces():
    result = run(usgs="usgs_mixed.json")
    nz = result.state["disasters"]["usgs-EQ-us6000tasa"]
    assert nz["severity"] == "Yellow"


def test_usgs_m6_unscored_fallback_surfaces():
    result = run(usgs="usgs_mixed.json")
    assert "usgs-EQ-us6000talg" in result.state["disasters"]


def test_usgs_pager_green_outranks_magnitude():
    result = run(usgs="usgs_mixed.json")
    # fixture has an M6.1 already scored green and an unscored M5.0
    assert set(result.state["disasters"]) == {
        "usgs-EQ-us6000talg",
        "usgs-EQ-us6000tasa",
    }


def test_reliefweb_record_surfaces_as_reported():
    result = run(reliefweb="reliefweb_mixed.xml")
    georgia = result.state["disasters"]["reliefweb-fl-2026-000106-geo"]
    assert georgia["severity"] == "Reported"
    assert georgia["glide"] == "FL-2026-000106-GEO"
    assert georgia["hazard_type"] == "flood"
    assert georgia["country"] == "Georgia"


def test_ambiguous_proximity_stays_separate():
    result = run(gdacs="gdacs_two_eq.json", usgs="usgs_ambiguous.json")
    disasters = result.state["disasters"]
    # both GDACS quakes and the between-them USGS quake stay distinct
    assert set(disasters) == {
        "gdacs-EQ-8880001",
        "gdacs-EQ-8880002",
        "usgs-EQ-usambig01",
    }
    assert disasters["usgs-EQ-usambig01"]["related"] == [
        "gdacs-EQ-8880001",
        "gdacs-EQ-8880002",
    ]


def test_three_feeds_idempotent():
    first = run(**ALL_THREE)
    later = datetime(2026, 7, 8, 6, tzinfo=timezone.utc)
    second = run_pipeline(payloads(**ALL_THREE), first.state, later)
    assert second.changed is False
    assert second.changeset == []
    assert second.state == first.state


def test_dashboard_shows_report_count():
    result = run(**ALL_THREE)
    page = render_dashboard(result.state, result.changeset)
    assert "2 reports" in page
