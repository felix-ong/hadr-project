"""Fetch the feeds, run the pipeline, write state + dashboard, signal changed.

Signal convention: `changed=true|false` is appended to $GITHUB_OUTPUT (when
set) and printed to stdout. The exit code means success/failure only - a
fetch or parse error degrades to a named staleness warning so a broken feed
can never be mistaken for a quiet morning, and a crashed run never signals.

`--render-only` re-renders dashboard.html from the committed state, the
last run's changeset and state/sitrep.txt without touching the network -
the workflow uses it to embed the narrative after the /sitrep skill runs.
"""

import gzip
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from dashboard import render_dashboard
from pipeline import run_pipeline

FEED_URLS = {
    "gdacs": "https://www.gdacs.org/gdacsapi/api/events/geteventlist/EVENTS4APP",
    "usgs": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson",
    "reliefweb": "https://reliefweb.int/disasters/rss.xml",
}
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 hadr-monitor/1.0"
)

ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = ROOT / "state" / "disasters.json"
RUN_PATH = ROOT / "state" / "changeset.json"
NARRATIVE_PATH = ROOT / "state" / "sitrep.txt"
DASHBOARD_PATH = ROOT / "dashboard.html"


def fetch_or_none(feed, url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
            "Accept-Encoding": "gzip",
            "Accept-Language": "en",
        },
    )
    for attempt in (1, 2):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = response.read()
                encoding = (response.headers.get("Content-Encoding") or "").lower()
                if encoding == "gzip" or data[:2] == b"\x1f\x8b":
                    data = gzip.decompress(data)
                print(
                    f"fetched {feed}: {len(data)} bytes, "
                    f"content-type {response.headers.get('Content-Type', '?')}",
                    file=sys.stderr,
                )
                if not data:
                    raise OSError("empty response body")
                return data
        except OSError as exc:
            # diagnostics go to the run log; the pipeline turns the missing
            # payload into a named dashboard warning
            print(f"fetch {feed} attempt {attempt} failed: {exc!r}", file=sys.stderr)
            if attempt == 1:
                time.sleep(5)
    return None


def _read_json(path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, indent=1, ensure_ascii=False, sort_keys=True)
    path.write_text(text + "\n", encoding="utf-8", newline="\n")


def _narrative():
    if NARRATIVE_PATH.exists():
        return NARRATIVE_PATH.read_text(encoding="utf-8-sig")  # tolerate a BOM
    return ""


def _render(state, run_record):
    DASHBOARD_PATH.write_text(
        render_dashboard(state, run_record["changeset"], run_record["warnings"], _narrative()),
        encoding="utf-8",
        newline="\n",
    )


def main(argv):
    if "--render-only" in argv:
        state = _read_json(STATE_PATH, {"disasters": {}})
        run_record = _read_json(RUN_PATH, {"changed": False, "changeset": [], "warnings": []})
        _render(state, run_record)
        return 0

    prior_state = _read_json(STATE_PATH, {})
    payloads = {feed: fetch_or_none(feed, url) for feed, url in FEED_URLS.items()}
    result = run_pipeline(payloads, prior_state, datetime.now(timezone.utc))

    _write_json(STATE_PATH, result.state)
    run_record = {
        "changed": result.changed,
        "changeset": result.changeset,
        "warnings": result.warnings,
    }
    _write_json(RUN_PATH, run_record)
    _render(result.state, run_record)

    signal = f"changed={'true' if result.changed else 'false'}"
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as fh:
            fh.write(signal + "\n")
    print(signal)
    for warning in result.warnings:
        print(f"warning: {warning}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
