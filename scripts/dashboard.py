"""Render the current state as the slice-1 Sitrep list in dashboard.html.

Deterministic output: no timestamps of its own, total sort order - an
unchanged run produces byte-identical HTML so git stays quiet on quiet
mornings.
"""

import html
from datetime import datetime

TIER_ORDER = {"red": 0, "orange": 1}

CAP = 12


def render_dashboard(state, changeset):
    new_ids = {entry["disaster_id"] for entry in changeset if entry["kind"] == "new"}
    disasters = sorted(state.get("disasters", {}).values(), key=_sort_key)
    shown, overflow = disasters[:CAP], disasters[CAP:]

    if shown:
        items = "\n".join(_row(d, d["disaster_id"] in new_ids) for d in shown)
        body = f'<ol class="sitrep">\n{items}\n</ol>'
        if overflow:
            body += f'\n<p class="overflow">… and {len(overflow)} more above threshold.</p>'
    else:
        body = '<p class="quiet">No Disasters above threshold.</p>'

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HADR Monitor — Sitrep</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 44rem; margin: 2rem auto; padding: 0 1rem; color: #1e2523; }}
  h1 {{ font-size: 1.4rem; }}
  ol.sitrep {{ list-style: none; padding: 0; }}
  ol.sitrep li {{ padding: 0.5rem 0; border-bottom: 1px solid #ddd; }}
  .tier {{ font-weight: 700; padding: 0.05rem 0.45rem; border-radius: 3px; color: #fff; font-size: 0.8rem; }}
  .tier.red {{ background: #b8432f; }}
  .tier.orange {{ background: #c27a24; }}
  .badge {{ font-size: 0.7rem; font-weight: 700; color: #3e7d4e; border: 1px solid #3e7d4e; padding: 0 0.3rem; border-radius: 3px; }}
  .meta {{ color: #555; font-size: 0.85rem; }}
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


def _row(disaster, is_new):
    tier = html.escape(disaster["severity"])
    name = html.escape(disaster["name"])
    country = html.escape(disaster["country"])
    hazard = html.escape(disaster["hazard_type"])
    changed = html.escape(disaster["last_changed"])
    url = html.escape(disaster["reports"][0]["url"], quote=True)
    badge = ' <span class="badge">NEW</span>' if is_new else ""
    title = f'<a href="{url}">{name}</a>' if url else name
    return (
        f'<li><span class="tier {tier.lower()}">{tier}</span> {title}{badge}<br>'
        f'<span class="meta">{country} · {hazard} · changed {changed}</span></li>'
    )
