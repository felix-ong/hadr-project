"""The pipeline seam: raw feed payloads + prior state in, Disasters state +
changeset + changed signal out.

Every decision here is deterministic per docs/adr/0003 - the /sitrep skill
only ever narrates what this module has already decided.
"""

import copy
from typing import NamedTuple

import gdacs
import reliefweb
import resolve
import usgs

PARSERS = {
    "gdacs": gdacs.parse_gdacs,
    "usgs": usgs.parse_usgs,
    "reliefweb": reliefweb.parse_reliefweb,
}

# Feeds are processed in pipeline order (detection before curation) so
# entity resolution is deterministic: detections anchor Disasters, later
# feeds attach to them.
FEED_ORDER = ("gdacs", "usgs", "reliefweb")

TIER_RANK = {"Red": 0, "Orange": 1, "Yellow": 2, "Reported": 3}

SCHEMA_VERSION = 1


class PipelineResult(NamedTuple):
    state: dict
    changeset: list
    changed: bool


def run_pipeline(payloads, prior_state, now):
    """Pure function - no network or file I/O; `now` must be tz-aware UTC."""
    unknown = set(payloads) - set(FEED_ORDER)
    if unknown:
        raise ValueError(f"unknown feeds: {sorted(unknown)}")

    disasters = copy.deepcopy((prior_state or {}).get("disasters") or {})
    changeset = []
    for feed in FEED_ORDER:
        if feed not in payloads:
            continue
        for report in PARSERS[feed](payloads[feed]):
            if _surfacing_tier(report) is None:
                continue
            matched_id, ambiguous = resolve.find_match(disasters, report)
            if matched_id:
                _attach(disasters[matched_id], report)
            else:
                disaster_id = _disaster_key(report)
                disaster = _disaster_from_report(disaster_id, report, now)
                if ambiguous:
                    disaster["related"] = ambiguous
                disasters[disaster_id] = disaster
                changeset.append(
                    {
                        "kind": "new",
                        "disaster_id": disaster_id,
                        "disaster": copy.deepcopy(disaster),
                    }
                )
    state = {"schema_version": SCHEMA_VERSION, "disasters": disasters}
    return PipelineResult(state, changeset, bool(changeset))


def _surfacing_tier(report):
    """The surfacing threshold (PRD #2). Returns a tier or None (below).

    Works on fresh and stored Reports alike so severity can always be
    recomputed from a Disaster's evidence.
    """
    feed = report["feed"]
    if feed == "gdacs":
        level = report["alertlevel"].strip().casefold()
        return level.capitalize() if level in {"orange", "red"} else None
    if feed == "usgs":
        alert = report["pager_alert"].strip().casefold()
        if alert:
            # PAGER has scored it: its impact estimate outranks raw magnitude,
            # so a PAGER-green M6+ stays below threshold.
            return alert.capitalize() if alert in {"yellow", "orange", "red"} else None
        magnitude = report["magnitude"]
        if magnitude is not None and magnitude >= 6.0:
            return "Yellow"  # M6.0+ not yet PAGER-scored, see implementation-notes
        return None
    if feed == "reliefweb":
        return "Reported"
    return None


def _disaster_key(report):
    if report["feed"] == "reliefweb":
        return f"reliefweb-{report['eventid']}"  # slug already encodes the hazard
    return f"{report['feed']}-{report['eventtype']}-{report['eventid']}"


def _disaster_from_report(disaster_id, report, now):
    return {
        "disaster_id": disaster_id,
        "hazard_type": report["hazard_type"],
        "name": report["name"],
        "severity": _surfacing_tier(report),
        "country": report["country"],
        "iso3": report["iso3"],
        "glide": report["glide"],
        "coordinates": report["coordinates"],
        "status": "active",
        "first_seen": now.isoformat(),
        "last_changed": now.isoformat(),
        "reports": [copy.deepcopy(report)],
    }


def _attach(disaster, report):
    # Merge or within-tier refresh: update the evidence, leave last_changed
    # alone and emit nothing. Escalations and Corrections are slice 3.
    for i, stored in enumerate(disaster["reports"]):
        if stored["feed"] == report["feed"] and stored["eventid"] == report["eventid"]:
            disaster["reports"][i] = copy.deepcopy(report)
            break
    else:
        disaster["reports"].append(copy.deepcopy(report))
    if report["glide"] and not disaster["glide"]:
        disaster["glide"] = report["glide"]
    if report["country"] and not disaster["country"]:
        disaster["country"] = report["country"]
    disaster["severity"] = _severity(disaster["reports"])


def _severity(reports):
    tiers = [tier for tier in map(_surfacing_tier, reports) if tier is not None]
    return min(tiers, key=TIER_RANK.__getitem__)
