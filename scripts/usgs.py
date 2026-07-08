"""Parse a raw USGS earthquake-feed payload into Report dicts (CONTEXT.md)."""

import json
from datetime import datetime, timezone


def parse_usgs(raw):
    """Parse USGS GeoJSON bytes/str into a list of Report dicts.

    Raises ValueError when the payload is not a USGS FeatureCollection.
    """
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict) or "features" not in data:
        raise ValueError("not a USGS FeatureCollection: missing 'features'")

    reports = []
    for feature in data["features"]:
        props = feature.get("properties") or {}
        eventid = feature.get("id")
        if not eventid:
            continue
        coordinates = (feature.get("geometry") or {}).get("coordinates") or []
        reports.append(
            {
                "feed": "usgs",
                "eventtype": "EQ",
                "eventid": str(eventid),
                "glide": "",
                "name": props.get("title", ""),
                "hazard_type": "earthquake",
                "magnitude": props.get("mag"),
                "pager_alert": (props.get("alert") or "").strip(),
                "status": props.get("status", ""),
                "country": props.get("place", ""),
                "iso3": "",
                "coordinates": coordinates[:2],
                "event_time": _iso(props.get("time")),
                "datemodified": _iso(props.get("updated")),
                "url": props.get("url", ""),
            }
        )
    return reports


def _iso(epoch_ms):
    if epoch_ms is None:
        return ""
    return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).isoformat()
