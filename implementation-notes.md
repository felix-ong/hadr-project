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

**2026-07-08 — Slice 3 (change lifecycle, staleness, 08:30 loop, #5)**

- **Escalation detection is a generic tier-boundary detector** on the
  unified severity (works for GDACS colours and PAGER alike). For GDACS,
  tier changes arrive via new Episodes in practice, and the episode fields
  are preserved on every stored Report for audit — but the trigger itself
  compares tiers, not raw episode fields. Slight generalisation of
  QUESTIONS.md Q5's wording; same observable behaviour.
- **Malformed/unfetchable feeds now degrade to named warnings** instead of
  crashing the run (changed from slice 1, where a bad payload raised). A
  broken feed can never be mistaken for a quiet morning, and never affects
  the changed signal. Exit code still means success/failure only.
- **Corrections live on the Disaster** (`corrections`, capped at 5) and
  never break silence by themselves; the dashboard always shows the latest
  note. Only USGS magnitude revisions generate them in v1.
- **A revision that drops every Report below threshold keeps the last
  surfaced tier** rather than deleting the Disaster (Q6: amend forward).
- **The narrative round-trip**: `run_check.py` writes
  `state/changeset.json` (the decided changeset + warnings) each run; the
  `/sitrep` skill reads it and writes `state/sitrep.txt`;
  `run_check.py --render-only` re-renders the dashboard with the prose
  embedded. On quiet mornings the previous narrative stays visible — the
  most recent Sitrep remains the current one.
- **Skill installation in CI**: Claude Code discovers skills under
  `.claude/skills/`, but the course artefact location is `skills/`; the
  workflow copies `skills/sitrep` into `.claude/skills/` before the
  narration step. Single source of truth stays in `skills/`.
- **@claude-on-failure caveat**: the failure issue is created with the
  Actions token, which cannot trigger the `claude.yml` workflow — the
  issue asks a human to comment `@claude investigate` to summon it.
- **Live observation on day one**: ReliefWeb's newest disaster record was
  11 days old at build time, so the staleness warning fired immediately —
  the 48h cadence for a curated feed may prove too tight; revisit after a
  week of live runs rather than tuning it now.

**2026-07-08 — Post-slice-3 hardening (feeds on CI runners)**

- **GDACS rejected the honest User-Agent from runner IPs** (empty/error
  responses); a browser-compatible UA string fixed it outright.
- **ReliefWeb's CDN filters by IP**: a subset of GitHub Actions runner IPs
  get the real RSS, the rest get an empty 200 `text/html` - identical
  behaviour for urllib and curl on the same runner, different runners
  differ. No header or TLS-stack change fixes an IP blocklist, so the
  design outcome is the honest one: those runs show the named
  "reliefweb feed unavailable" warning. Coverage self-heals because state
  is cumulative and the disasters feed moves on a ~48h cadence - a record
  only needs one clean-IP run to be ingested. Revisit ADR 0002 (API with
  an approved appname) only if live coverage proves materially gappy.
- **Fetching is layered** (urllib → curl fallback → one retry round) with
  diagnostics in the run log; an empty body counts as a failed fetch.
- **claude-code-action validates workflow content against the default
  branch**: on a non-main branch whose sitrep.yml differs, the narration
  step is skipped by design ("workflow validation failed") and the step
  still succeeds. Narration is therefore only testable on main.
- **claude-code-review.yml shipped broken from the template**: agent mode
  (custom `prompt`) grants no tools, and the job had `pull-requests: read`
  - reviews ran, were denied their first action, posted nothing, and
  reported success. Fixed with `pull-requests: write` + an
  `--allowedTools` grant for the diff/comment commands.

## Open questions

## Deviations

<!-- Anything built that departs from the PRD or CLAUDE.md is recorded here,
     with the reason. An undocumented deviation is a bug. -->
