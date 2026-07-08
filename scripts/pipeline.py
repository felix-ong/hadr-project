"""The pipeline seam: raw feed payloads + prior state in, Disasters state +
changeset + changed signal out.

Every decision here is deterministic per docs/adr/0003 - the /sitrep skill
only ever narrates what this module has already decided.
"""

import copy
from typing import NamedTuple

import gdacs

PARSERS = {"gdacs": gdacs.parse_gdacs}

SURFACING_TIERS = {"orange", "red"}

SCHEMA_VERSION = 1


class PipelineResult(NamedTuple):
    state: dict
    changeset: list
    changed: bool


def run_pipeline(payloads, prior_state, now):
    """Pure function - no network or file I/O; `now` must be tz-aware UTC."""
    disasters = copy.deepcopy((prior_state or {}).get("disasters") or {})
    changeset = []
    for feed, raw in payloads.items():
        for report in PARSERS[feed](raw):
            if report["alertlevel"].casefold() not in SURFACING_TIERS:
                continue
            disaster_id = f"{report['feed']}-{report['eventtype']}-{report['eventid']}"
            existing = disasters.get(disaster_id)
            if existing is None:
                disaster = _disaster_from_report(disaster_id, report, now)
                disasters[disaster_id] = disaster
                changeset.append(
                    {
                        "kind": "new",
                        "disaster_id": disaster_id,
                        "disaster": copy.deepcopy(disaster),
                    }
                )
            else:
                _refresh(existing, report)
    state = {"schema_version": SCHEMA_VERSION, "disasters": disasters}
    return PipelineResult(state, changeset, bool(changeset))


def _disaster_from_report(disaster_id, report, now):
    return {
        "disaster_id": disaster_id,
        "hazard_type": report["hazard_type"],
        "name": report["name"],
        "severity": report["alertlevel"],
        "country": report["country"],
        "iso3": report["iso3"],
        "glide": report["glide"],
        "coordinates": report["coordinates"],
        "status": "active",
        "first_seen": now.isoformat(),
        "last_changed": now.isoformat(),
        "reports": [_stored_report(report)],
    }


def _refresh(disaster, report):
    # Within-tier data refresh: update the stored Report, leave last_changed
    # alone and emit nothing. Escalations and Corrections are slice 3.
    disaster["severity"] = report["alertlevel"]
    disaster["glide"] = report["glide"]
    for i, stored in enumerate(disaster["reports"]):
        if stored["feed"] == report["feed"] and stored["eventid"] == report["eventid"]:
            disaster["reports"][i] = _stored_report(report)
            return
    disaster["reports"].append(_stored_report(report))


def _stored_report(report):
    return {
        "feed": report["feed"],
        "eventtype": report["eventtype"],
        "eventid": report["eventid"],
        "episodeid": report["episodeid"],
        "alertlevel": report["alertlevel"],
        "episodealertlevel": report["episodealertlevel"],
        "fromdate": report["fromdate"],
        "datemodified": report["datemodified"],
        "url": report["url"],
    }
