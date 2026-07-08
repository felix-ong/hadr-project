"""Shared open-ended hazard-type vocabulary (see CONTEXT.md: not a closed
enum of GDACS's 7 types - unknown codes fall through as lowercase strings).

Codes are shared by GDACS event types and GLIDE number prefixes.
"""

HAZARD_TYPES = {
    "EQ": "earthquake",
    "TC": "tropical cyclone",
    "FL": "flood",
    "VO": "volcano",
    "DR": "drought",
    "WF": "wildfire",
    "TS": "tsunami",
    "EP": "epidemic",
    "ST": "storm",
    "LS": "landslide",
    "CW": "cold wave",
    "HT": "heat wave",
    "FF": "flash flood",
    "FR": "fire",
    "VW": "violent wind",
    "SS": "storm surge",
}


def hazard_type(code):
    code = (code or "").strip().upper()
    return HAZARD_TYPES.get(code, code.lower())
