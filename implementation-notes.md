# Implementation notes

Kept by the agent, reviewed by you. One entry per working block.

## Decisions

**2026-07-08 — Slice 1 (GDACS → changed-signal, #3)**

- **Changed-signal convention:** `run_check.py` appends `changed=true|false`
  to `$GITHUB_OUTPUT` (when set) and prints the same to stdout. The exit
  code means success/failure only — signalling "changed" via exit codes
  would conflate a changed morning with a crashed run, the exact ambiguity
  REQS.md warns about. The future workflow branches on
  `steps.check.outputs.changed`.
- **Only Orange+ Disasters are stored in state.** Hundreds of daily Green
  events would bloat a committed JSON file for nothing; a later
  Green→Orange transition correctly surfaces as NEW, consistent with
  CONTEXT.md's Escalation definition ("tier increase since last
  *surfaced*").
- **No generated-at timestamps in state or dashboard.** An unchanged run
  rewrites byte-identical files, so `git diff` stays quiet on quiet
  mornings (verified by hash comparison across consecutive live runs).
- **Runtime is stdlib-only** (`urllib.request`, `json`, `html`); the only
  dev dependency is pytest. One GET of a public JSON endpoint doesn't
  justify `requests` plus an install step in the scheduled workflow.

**2026-07-08 — Slice 2 (three feeds, one Disaster, #4)**

- **Severity tiers unified as Red > Orange > Yellow > Reported.** GDACS
  colours map directly; USGS PAGER yellow/orange/red map directly; a
  ReliefWeb record with no impact score ranks "Reported" (curated but
  unscored). An M6.0+ quake PAGER hasn't scored yet surfaces as Yellow —
  a documented placeholder tier, not feed data.
- **A PAGER verdict outranks raw magnitude.** The M6.0 fallback applies
  only when PAGER hasn't scored the event; a PAGER-green M6+ stays below
  threshold ("magnitude is not impact", REQS.md).
- **Proximity merging is cross-feed only.** A feed's own eventid identity
  outranks space/time proximity: two USGS quakes near each other are two
  events (aftershocks), not one — same-feed near-duplicates stay separate,
  per ADR 0001's precision bias. GLIDE matches merge regardless of feed.
- **Feed processing order is gdacs → usgs → reliefweb** (detection before
  curation), so entity resolution is deterministic: detections anchor
  Disasters, later feeds attach evidence to them.
- **USGS window is `all_day`; `status: deleted` events are skipped** —
  explicit retraction handling is slice 3.
- **State was regenerated once** on this branch (pre-publication) to pick
  up the richer stored-Report shape and hazard-code names; slice-1 state
  had never been served from anywhere.

## Open questions

## Deviations

<!-- Anything built that departs from the PRD or CLAUDE.md is recorded here,
     with the reason. An undocumented deviation is a bug. -->
