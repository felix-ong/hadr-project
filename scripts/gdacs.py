"""Parse a raw GDACS event-list payload into Report dicts (see CONTEXT.md)."""

import json

from hazards import hazard_type


def parse_gdacs(raw):
    """Parse GDACS GeoJSON bytes/str into a list of Report dicts.

    Raises ValueError when the payload is not a GDACS FeatureCollection.
    """
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict) or "features" not in data:
        raise ValueError("not a GDACS FeatureCollection: missing 'features'")

    reports = []
    for feature in data["features"]:
        props = feature.get("properties") or {}
        # GDACS booleans are strings: "true" / "false"
        if props.get("istemporary") == "true" or props.get("iscurrent") == "false":
            continue
        eventid = props.get("eventid")
        eventtype = props.get("eventtype")
        if eventid in (None, "") or not eventtype:
            continue
        geometry = feature.get("geometry") or {}
        urls = props.get("url") or {}
        reports.append(
            {
                "feed": "gdacs",
                "eventtype": eventtype,
                "eventid": str(eventid),
                "episodeid": str(props.get("episodeid", "")),
                "glide": props.get("glide", ""),
                "name": props.get("name", ""),
                "hazard_type": hazard_type(eventtype),
                "alertlevel": (props.get("alertlevel") or "").strip(),
                "episodealertlevel": (props.get("episodealertlevel") or "").strip(),
                "country": props.get("country", ""),
                "iso3": props.get("iso3", ""),
                "coordinates": geometry.get("coordinates", []),
                "event_time": props.get("fromdate", ""),
                "fromdate": props.get("fromdate", ""),
                "datemodified": props.get("datemodified", ""),
                "url": urls.get("report", ""),
            }
        )
    return reports
