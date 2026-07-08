# Questions

Running log for the grilling session that turns `REQS.md` into `CONTEXT.md`
and `docs/adr/*.md`. All questions planned before the session starts are
listed below, in the order we'll walk them (each one gates or informs the
ones after it). Questions that come up mid-session get appended under
"Discovered during the session" as they happen, not batched at the end.

Each entry keeps my recommendation and the final answer once decided, so the
reasoning survives even where I got overruled.

## Planned up front

1. **Surfacing threshold** — status: resolved
   What earns a place in the sitrep — a GDACS colour, a USGS magnitude/PAGER
   level, any ReliefWeb record? REQS.md left this "up to you."
   **Answer:** Impact-based, not raw magnitude/colour-name matching. GDACS
   Orange+ or Red; USGS PAGER `alert` present (yellow/orange/red) with a
   M6.0+ magnitude fallback for events PAGER hasn't scored yet; any new
   ReliefWeb disaster record (already human-curated, so no further filter).

2. **"Something changed" trigger** — status: resolved
   Does silence break only for a brand-new event above threshold, or also
   for an existing one escalating, being revised, or picking up a new
   ReliefWeb report?
   **Answer:** Threshold-crossing changes only. Re-trigger for: a new event
   crossing the Q1 threshold, an already-surfaced event escalating past a
   tier boundary (GDACS colour tier, PAGER tier), a deletion or major
   downgrade of a surfaced event, or a new ReliefWeb report on a known
   disaster. Small within-tier revisions do not retrigger.

3. **Scope in v1 vs. the data model** — status: resolved
   REQS.md says scope is "natural hazard and humanitarian crises broadly,"
   but all three feeds are natural-hazard only. What does v1 actually cover,
   and where does "design for the wider scope" show up concretely?
   **Answer:** v1 ingests natural hazards only (all three feeds carry
   nothing else). The core entity is modeled generically — named
   "Disaster," open hazard-type field — not hardcoded to the 7 GDACS
   hazard types, so a future conflict/epidemic source can slot in without a
   schema rewrite. No ingestion code for those sources exists yet.

4. **Cross-feed entity resolution** — status: resolved
   No shared event ID across GDACS/USGS/ReliefWeb. What makes two records
   the same underlying disaster — GLIDE first, then time+location+magnitude
   proximity as fallback? What's the cost of a false merge vs. a missed one?
   **Answer:** GLIDE-first, precision-biased. Merge on matching GLIDE.
   Without GLIDE, merge only if hazard type matches AND records are close
   in both space (~250km) and time (~24-48h). Ambiguous cases stay as
   separate, cross-referenced entries rather than merging — a wrong merge
   (conflating two distinct disasters) is worse than a duplicate line.
   → Warrants an ADR (hard to reverse once other logic depends on the
   Disaster identity; real trade-off between precision and recall).

5. **GDACS alert authority + re-alert policy** — status: resolved
   Events carry `alertlevel`, `alertscore`, `episodealertlevel`,
   `episodealertscore`. Which one is authoritative, and do we re-alert when
   an already-reported event's colour changes?
   **Answer:** `alertlevel` (event-level, rolled-up colour) is what's
   displayed as current severity. Escalation is detected by comparing
   `episodealertlevel` across successive `episodeid`s of the same event —
   a new episode is GDACS's own revision unit. The `*score` fields are
   secondary, used only to sort within a colour tier, never as the
   primary trigger.

6. **USGS revision/deletion handling** — status: resolved
   Magnitudes get revised and events get deleted after publication. What
   happens to a sitrep line already published when its source event
   changes underneath it?
   **Answer:** Amend forward, never rewrite history. Each dashboard
   regenerates from current state; a revised event shows updated numbers
   plus a short correction note, a deleted event gets an explicit
   retraction line. Archived past snapshots (Q11) are never rewritten —
   only the current report reflects the change.

7. **ReliefWeb access mode** — status: resolved
   API access needs a pre-approved `appname` that may not clear in time.
   Build against RSS now and swap the API in later, or wait on approval?
   **Answer:** RSS permanently — no `appname` request, no v2 API
   integration planned. One integration, not two. GLIDE is still
   extractable: the RSS `<description>` embeds a
   `<div class="tag glide">Glide: ...</div>` tag, just as HTML-escaped
   text rather than a clean field, so Q4's GLIDE-first merge rule still
   works — it needs an HTML-tag scrape, not a JSON field read.
   → Worth an ADR (a reasonable reader would expect the official
   structured API; the reason to permanently avoid it is non-obvious
   without this context).

8. **Feed staleness / heartbeat** — status: resolved
   "Quiet" must mean "nothing happened," not "a feed died silently." What
   counts as stale per feed, and what does the sitrep say when one is down?
   **Answer:** Per-feed threshold matched to that feed's normal cadence
   (USGS ~1h, GDACS ~6h, ReliefWeb ~48h). A stale feed always produces a
   named warning on the dashboard ("USGS feed stale, last updated 3h
   ago") — staleness can never be silently absorbed into a quiet morning.

9. **LLM vs. deterministic code split** — status: resolved
   REQS.md's instinct: parsing/dedup/thresholding are code, the LLM does
   triage, cross-source synthesis, and summarising the ReliefWeb pile.
   Confirming the boundary before it's load-bearing.
   **Answer:** Confirmed and narrowed. Code owns every decision already
   made in this session — surfacing, change-trigger, entity match, alert
   authority, revision handling, staleness. The LLM's only job is
   narrative synthesis: turning an already-decided, already-merged
   Disaster record into sitrep prose. It never decides what appears or
   how it's ranked.
   → Worth an ADR (this is the load-bearing architectural boundary for
   the whole system).

10. **State store** — status: resolved
    Where does "what I've already seen" live between scheduled runs?
    **Answer:** Committed to the repo — a JSON file (e.g.
    `state/disasters.json`), read and written by the scheduled workflow
    and committed back each run. Zero infra; git history doubles as an
    audit trail of every merge/escalation/correction.

11. **Dashboard hosting + history** — status: resolved
    Where does `dashboard.html` get served from, and is each morning's
    report archived or overwritten in place?
    **Answer:** GitHub Pages, serving `dashboard.html` from the repo
    root, overwritten in place each run — one stable bookmarkable URL
    always shows today's report. No separate dated archive; past reports
    are recoverable via `git log -p dashboard.html` since the state
    store (Q10) already versions everything in git.

12. **Sitrep shape, precisely** — status: resolved
    REQS.md says "headline only." How many items, what per-item shape,
    ranked by what?
    **Answer:** A capped list (~10-15 items) of one-line-plus-clause
    entries (e.g. "M7.1 earthquake, Venezuela — GDACS Red, escalated
    from Orange overnight, 2 ReliefWeb reports"). Ranked by severity tier
    first, then recency of change within tier. NEW/ESCALATED entries are
    visually tagged and distinguished from corrections. Anything past
    the cap is summarised as a count, never silently dropped.

13. **Backtest approach** — status: resolved
    Replay a past window against EM-DAT (or similar) to check catch-vs-miss
    before trusting the threshold — worth doing before Day 2, or defer?
    **Answer:** No backtest. Trust the impact-based threshold (Q1) as
    designed and rely on live observation over the 3-day exercise instead
    of retrospective validation against EM-DAT.

14. **Language & tooling** — status: resolved
    `CLAUDE.md`'s "Language & tooling" is blank; `.gitignore` hedges for
    both Python and Node debris. What runs `scripts/` (fetching, entity
    resolution, thresholding, state diffing)?
    **Answer:** Python. Strong stdlib/ecosystem for HTTP/JSON/XML
    (requests, feedparser), a good fit for the entity-resolution math
    (distance/time proximity, GLIDE parsing), easy to test with pytest.

## Discovered during the session

15. **Headless sitrep model + budget** — status: resolved
    Split out from the original Q14 once `.github/workflows/sitrep.yml.disabled`
    made clear the LLM step is a headless `claude -p` run of a `/sitrep`
    skill (per the Team seat), not a raw billed API call. Which model does
    the skill declare per `skills/README.md`'s "note on which model each
    step should use," and is a once-a-day headless run (plus manual
    testing runs during dev) something to think about budget-wise at all?
    **Answer:** Haiku by default — the synthesis task is bounded and
    involves no independent judgment (Q9), so a fast/cheap model suffices
    and keeps Day 2 iteration cheap. Upgrade to Sonnet only if synthesis
    quality falls short in practice. No separate budget ceiling — one run
    a day is negligible on a Team seat.
