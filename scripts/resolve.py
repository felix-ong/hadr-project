"""GLIDE-first, precision-biased entity resolution (docs/adr/0001).

A Report merges into an existing Disaster when:
1. the Disaster already holds that exact Report (same feed + eventid), or
2. GLIDE numbers match, or
3. no GLIDE: hazard type matches AND the Report is within ~250km and
   ~48h of one of the Disaster's Reports - and the Disaster has no Report
   from the same feed yet (a feed's own event identity outranks proximity).

A Report proximate to more than one Disaster is ambiguous: it stays a
separate, cross-referenced entry rather than merging - a false merge
misleads on scale and location, a duplicate is just noise.
"""

from datetime import datetime, timezone
from math import asin, cos, radians, sin, sqrt

MAX_DISTANCE_KM = 250
MAX_HOURS_APART = 48

EARTH_RADIUS_KM = 6371


def find_match(disasters, report):
    """Return (matched_disaster_id or None, ambiguous_disaster_ids)."""
    for disaster_id, disaster in disasters.items():
        for stored in disaster["reports"]:
            if stored["feed"] == report["feed"] and stored["eventid"] == report["eventid"]:
                return disaster_id, []

    if report["glide"]:
        for disaster_id, disaster in disasters.items():
            if disaster.get("glide") == report["glide"]:
                return disaster_id, []

    candidates = [
        disaster_id
        for disaster_id, disaster in disasters.items()
        if disaster["hazard_type"] == report["hazard_type"]
        and not any(stored["feed"] == report["feed"] for stored in disaster["reports"])
        and _proximate(disaster, report)
    ]
    if len(candidates) == 1:
        return candidates[0], []
    if candidates:
        return None, sorted(candidates)
    return None, []


def _proximate(disaster, report):
    if len(report.get("coordinates") or []) < 2 or not report.get("event_time"):
        return False
    for stored in disaster["reports"]:
        if len(stored.get("coordinates") or []) < 2 or not stored.get("event_time"):
            continue
        if (
            _km_between(stored["coordinates"], report["coordinates"]) <= MAX_DISTANCE_KM
            and _hours_apart(stored["event_time"], report["event_time"]) <= MAX_HOURS_APART
        ):
            return True
    return False


def _km_between(a, b):
    lon1, lat1, lon2, lat2 = map(radians, [a[0], a[1], b[0], b[1]])
    h = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(h))


def _hours_apart(iso_a, iso_b):
    delta = parse_timestamp(iso_a) - parse_timestamp(iso_b)
    return abs(delta.total_seconds()) / 3600


def parse_timestamp(iso):
    parsed = datetime.fromisoformat(iso)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed
