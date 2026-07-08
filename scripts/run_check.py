"""Fetch GDACS, run the pipeline, write state + dashboard, signal changed.

Signal convention: `changed=true|false` is appended to $GITHUB_OUTPUT (when
set) and printed to stdout. The exit code means success/failure only - a
fetch or parse error exits nonzero so a broken run can never be mistaken
for a quiet morning.
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from dashboard import render_dashboard
from pipeline import run_pipeline

GDACS_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/EVENTS4APP"
USER_AGENT = "hadr-monitor (github.com/felix-ong/hadr-project)"

ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = ROOT / "state" / "disasters.json"
DASHBOARD_PATH = ROOT / "dashboard.html"


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def main():
    prior_state = {}
    if STATE_PATH.exists():
        prior_state = json.loads(STATE_PATH.read_text(encoding="utf-8"))

    payloads = {"gdacs": fetch(GDACS_URL)}
    result = run_pipeline(payloads, prior_state, datetime.now(timezone.utc))

    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    state_json = json.dumps(result.state, indent=1, ensure_ascii=False, sort_keys=True)
    STATE_PATH.write_text(state_json + "\n", encoding="utf-8", newline="\n")
    DASHBOARD_PATH.write_text(
        render_dashboard(result.state, result.changeset), encoding="utf-8", newline="\n"
    )

    signal = f"changed={'true' if result.changed else 'false'}"
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as fh:
            fh.write(signal + "\n")
    print(signal)
    return 0


if __name__ == "__main__":
    sys.exit(main())
