"""The pipeline seam: raw feed payloads + prior state in, Disasters state +
changeset + changed signal + staleness warnings out.

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

# Expected cadence per feed (QUESTIONS.md Q8); a feed whose newest record
# is older than this always produces a named warning - staleness can never
# be silently absorbed into a quiet morning.
STALENESS_HOURS = {"usgs": 1, "gdacs": 6, "reliefweb": 48}

SCHEMA_VERSION = 1


class PipelineResult(NamedTuple):
    state: dict
    changeset: list
    changed: bool
    warnings: list


def run_pipeline(payloads, prior_state, now):
    """Pure function - no network or file I/O; `now` must be tz-aware UTC.

    A payload of None marks a feed that could not be fetched this run;
    unparseable payloads degrade to a warning the same way. Neither ever
    affects the changed signal.
    """
    unknown = set(payloads) - set(FEED_ORDER)
    if unknown:
        raise ValueError(f"unknown feeds: {sorted(unknown)}")

    disasters = copy.deepcopy((prior_state or {}).get("disasters") or {})
    changeset, warnings = [], []
    created = set()
    for feed in FEED_ORDER:
        if feed not in payloads:
            continue
        raw = payloads[feed]
        if raw is None:
            warnings.append(f"{feed} feed unavailable this run")
            continue
        try:
            reports = PARSERS[feed](raw)
        except ValueError:
            warnings.append(f"{feed} feed unparseable this run")
            continue
        if not reports:
            warnings.append(f"{feed} feed returned no records this run")
            continue
        stale = _staleness(feed, reports, now)
        if stale:
            warnings.append(stale)
        for report in reports:
            changeset.extend(_ingest(disasters, report, now, created))
    state = {"schema_version": SCHEMA_VERSION, "disasters": disasters}
    return PipelineResult(state, changeset, bool(changeset), warnings)


def _staleness(feed, reports, now):
    timestamps = [
        stamp
        for stamp in (r.get("datemodified") or r.get("event_time") for r in reports)
        if stamp
    ]
    if not timestamps:
        return f"{feed} feed records carry no timestamps this run"
    newest = max(resolve.parse_timestamp(stamp) for stamp in timestamps)
    limit = STALENESS_HOURS[feed]
    if (now - newest).total_seconds() / 3600 > limit:
        return f"{feed} feed stale: newest record {newest.isoformat()} is past the {limit}h threshold"
    return None


def _ingest(disasters, report, now, created):
    """Route one Report; returns the changeset entries it produced."""
    if report["feed"] == "usgs" and report.get("status") == "deleted":
        matched_id, _ = resolve.find_match(disasters, report)
        if matched_id and disasters[matched_id]["status"] != "retracted":
            disaster = disasters[matched_id]
            _replace_or_append(disaster, report)
            disaster["status"] = "retracted"
            disaster["last_changed"] = now.isoformat()
            return [_entry("retraction", disaster)]
        return []  # deletion of something never surfaced is a non-event

    if _surfacing_tier(report) is None:
        return []

    matched_id, ambiguous = resolve.find_match(disasters, report)
    if matched_id is None:
        disaster_id = _disaster_key(report)
        disaster = _disaster_from_report(disaster_id, report, now)
        if ambiguous:
            disaster["related"] = ambiguous
        disasters[disaster_id] = disaster
        created.add(disaster_id)
        return [_entry("new", disaster)]
    return _attach(disasters[matched_id], report, now, brand_new=matched_id in created)


def _attach(disaster, report, now, brand_new):
    """Merge a Report into a known Disaster; classify what changed.

    Tier boundary crossings (Escalation/downgrade) and a new ReliefWeb
    report break the silence; a within-tier magnitude revision becomes a
    Correction that amends forward without retriggering (QUESTIONS.md Q2/Q6);
    anything else is a silent evidence refresh.
    """
    old_severity = disaster["severity"]
    existing = next(
        (
            stored
            for stored in disaster["reports"]
            if stored["feed"] == report["feed"] and stored["eventid"] == report["eventid"]
        ),
        None,
    )
    correction = None
    if existing is not None and not brand_new and report["feed"] == "usgs":
        old_mag, new_mag = existing.get("magnitude"), report.get("magnitude")
        if old_mag is not None and new_mag is not None and old_mag != new_mag:
            correction = f"magnitude revised M{old_mag} to M{new_mag}"

    _replace_or_append(disaster, report)
    if report["glide"] and not disaster["glide"]:
        disaster["glide"] = report["glide"]
    if report["country"] and not disaster["country"]:
        disaster["country"] = report["country"]
    # a revision can drop every Report below threshold; the Disaster keeps
    # its last surfaced tier rather than vanishing silently (Q6: amend forward)
    disaster["severity"] = _severity(disaster["reports"]) or old_severity

    if brand_new:
        return []
    old_rank = TIER_RANK[old_severity]
    new_rank = TIER_RANK[disaster["severity"]]
    if new_rank < old_rank:
        disaster["last_changed"] = now.isoformat()
        return [_entry("escalation", disaster)]
    if new_rank > old_rank:
        disaster["last_changed"] = now.isoformat()
        return [_entry("downgrade", disaster)]
    if existing is None and report["feed"] == "reliefweb":
        disaster["last_changed"] = now.isoformat()
        return [_entry("new_report", disaster)]
    if correction:
        notes = disaster.setdefault("corrections", [])
        notes.append({"at": now.isoformat(), "note": correction})
        disaster["corrections"] = notes[-5:]
    return []


def _replace_or_append(disaster, report):
    for i, stored in enumerate(disaster["reports"]):
        if stored["feed"] == report["feed"] and stored["eventid"] == report["eventid"]:
            disaster["reports"][i] = copy.deepcopy(report)
            return
    disaster["reports"].append(copy.deepcopy(report))


def _entry(kind, disaster):
    return {
        "kind": kind,
        "disaster_id": disaster["disaster_id"],
        "disaster": copy.deepcopy(disaster),
    }


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


def _severity(reports):
    tiers = [tier for tier in map(_surfacing_tier, reports) if tier is not None]
    return min(tiers, key=TIER_RANK.__getitem__) if tiers else None
