"""Parse the ReliefWeb disasters RSS feed into Report dicts (CONTEXT.md).

Permanently RSS, not the v2 API - see docs/adr/0002. The GLIDE number is
scraped from the <div class="tag glide"> markup embedded in each item's
description.
"""

import re
import xml.etree.ElementTree as ET
from datetime import timezone
from email.utils import parsedate_to_datetime

from hazards import hazard_type

GLIDE_PATTERN = re.compile(r"Glide:\s*([A-Z0-9-]+)")
COUNTRY_PATTERN = re.compile(r"Affected countr(?:y|ies):\s*([^<]+)")


def parse_reliefweb(raw):
    """Parse ReliefWeb RSS bytes/str into a list of Report dicts.

    Raises ValueError when the payload is not parseable RSS.
    """
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8-sig")
    try:
        root = ET.fromstring(raw.lstrip())
    except ET.ParseError as exc:
        raise ValueError(f"not parseable ReliefWeb RSS: {exc}") from exc

    reports = []
    for item in root.iter("item"):
        link = (item.findtext("link") or "").strip()
        eventid = link.rstrip("/").rsplit("/", 1)[-1] if link else ""
        if not eventid:
            continue
        description = item.findtext("description") or ""
        glide_match = GLIDE_PATTERN.search(description)
        glide = glide_match.group(1) if glide_match else ""
        country_match = COUNTRY_PATTERN.search(description)
        country = country_match.group(1).strip() if country_match else ""
        # hazard code from the GLIDE prefix, else the link slug prefix
        code = (glide or eventid).split("-", 1)[0]
        reports.append(
            {
                "feed": "reliefweb",
                "eventtype": code.upper(),
                "eventid": eventid,
                "glide": glide,
                "name": (item.findtext("title") or "").strip(),
                "hazard_type": hazard_type(code),
                "country": country,
                "iso3": "",
                "coordinates": [],
                "event_time": _iso(item.findtext("pubDate")),
                "datemodified": _iso(item.findtext("pubDate")),
                "url": link,
            }
        )
    return reports


def _iso(pubdate):
    if not pubdate:
        return ""
    return parsedate_to_datetime(pubdate.strip()).astimezone(timezone.utc).isoformat()
