"""Render the current state as the Sitrep in dashboard.html.

Deterministic output: no timestamps of its own, total sort order - an
unchanged run produces byte-identical HTML so git stays quiet on quiet
mornings. The narrative paragraph is the one LLM-written artefact and is
passed in as text (docs/adr/0003) - this module never invents content.
"""

import html
from datetime import datetime

TIER_ORDER = {"red": 0, "orange": 1, "yellow": 2, "reported": 3}

BADGES = {
    "new": "NEW",
    "escalation": "ESCALATED",
    "downgrade": "DOWNGRADED",
    "new_report": "UPDATED",
    "retraction": "RETRACTED",
}

CAP = 12


def render_dashboard(state, changeset, warnings=(), narrative=""):
    badge_by_id = {e["disaster_id"]: BADGES[e["kind"]] for e in changeset if e["kind"] in BADGES}
    disasters = sorted(state.get("disasters", {}).values(), key=_sort_key)
    shown, overflow = disasters[:CAP], disasters[CAP:]

    blocks = []
    if warnings:
        alerts = "\n".join(f"<p>&#9888; {html.escape(w)}</p>" for w in warnings)
        blocks.append(f'<div class="warnings">\n{alerts}\n</div>')
    if narrative.strip():
        blocks.append(f'<section class="narrative"><p>{html.escape(narrative.strip())}</p></section>')
    if shown:
        items = "\n".join(_row(d, badge_by_id.get(d["disaster_id"])) for d in shown)
        listing = f'<ol class="sitrep">\n{items}\n</ol>'
        if overflow:
            listing += f'\n<p class="overflow">… and {len(overflow)} more above threshold.</p>'
        blocks.append(listing)
    else:
        blocks.append('<p class="quiet">No Disasters above threshold.</p>')
    body = "\n".join(blocks)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HADR Monitor — Sitrep</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 44rem; margin: 2rem auto; padding: 0 1rem; color: #1e2523; }}
  h1 {{ font-size: 1.4rem; }}
  .warnings {{ border: 1px solid #b8432f; border-left-width: 4px; border-radius: 4px; padding: 0.25rem 1rem; color: #b8432f; }}
  .warnings p {{ margin: 0.4rem 0; }}
  .narrative {{ border-left: 4px solid #6b7280; padding: 0.25rem 1rem; margin: 1rem 0; }}
  ol.sitrep {{ list-style: none; padding: 0; }}
  ol.sitrep li {{ padding: 0.5rem 0; border-bottom: 1px solid #ddd; }}
  .tier {{ font-weight: 700; padding: 0.05rem 0.45rem; border-radius: 3px; color: #fff; font-size: 0.8rem; }}
  .tier.red {{ background: #b8432f; }}
  .tier.orange {{ background: #c27a24; }}
  .tier.yellow {{ background: #a08a00; }}
  .tier.reported {{ background: #6b7280; }}
  .badge {{ font-size: 0.7rem; font-weight: 700; color: #3e7d4e; border: 1px solid #3e7d4e; padding: 0 0.3rem; border-radius: 3px; }}
  .meta {{ color: #555; font-size: 0.85rem; }}
  .correction {{ color: #555; font-size: 0.85rem; font-style: italic; }}
</style>
</head>
<body>
<h1>HADR Monitor — Sitrep</h1>
{body}
</body>
</html>
"""


def _sort_key(disaster):
    tier = TIER_ORDER.get(disaster["severity"].casefold(), 99)
    recency = -datetime.fromisoformat(disaster["last_changed"]).timestamp()
    return (tier, recency, disaster["disaster_id"])


def _row(disaster, badge):
    tier = html.escape(disaster["severity"])
    name = html.escape(disaster["name"])
    country = html.escape(disaster["country"])
    hazard = html.escape(disaster["hazard_type"])
    changed = html.escape(disaster["last_changed"])
    url = html.escape(disaster["reports"][0]["url"], quote=True)
    title = f'<a href="{url}">{name}</a>' if url else name
    if disaster.get("status") == "retracted":
        title = f"<s>{title}</s>"
        badge = badge or "RETRACTED"
    badge_html = f' <span class="badge">{badge}</span>' if badge else ""
    count = len(disaster["reports"])
    reports = f"{count} report{'s' if count != 1 else ''}"
    note = ""
    corrections = disaster.get("corrections")
    if corrections:
        latest = corrections[-1]
        note = f'<br><span class="correction">correction: {html.escape(latest["note"])} ({html.escape(latest["at"])})</span>'
    return (
        f'<li><span class="tier {tier.lower()}">{tier}</span> {title}{badge_html}<br>'
        f'<span class="meta">{country} · {hazard} · {reports} · changed {changed}</span>{note}</li>'
    )
