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

## Open questions

## Deviations

<!-- Anything built that departs from the PRD or CLAUDE.md is recorded here,
     with the reason. An undocumented deviation is a bug. -->
