# REQS.md - HADR Monitoring Agent

> Raw capture of the idea. Loose on purpose. The planning process
> (grill -> PRD -> shaping -> breadboard) refines this; it does not
> need to be complete or consistent yet.
>
> Lines marked **[DECIDE]** are mine to answer before Step A adds value.
> Everything else is the brief as I currently understand it.

## The idea

An agent that watches live disaster feeds, filters out the noise, works out
what actually matters, and hands me a short morning situation report so I do
not have to read three raw feeds myself every day.

The end state (from the course brief): a repository containing an agent that

- watches GDACS, USGS and ReliefWeb (just use the xml feed) (see `feeds/`)
- filters noise and assesses what remains: what happened, where, how bad, who is affected
- publishes a morning situation report to `dashboard.html` at 08:30 Singapore time
- runs on a schedule, unattended, and stays quiet when nothing has changed

## What the three feeds actually are (not interchangeable)

They sit at different stages of a disaster's life, they are a pipeline not
three copies of the same thing:

- **USGS** - physical sensor network. Earthquakes only. Fast (minutes). Says a
  quake happened; says nothing directly about humans. Events get revised and
  deleted after publication.
- **GDACS** - modelled impact estimator + aggregator over ~7 hazard types
  (quake/tsunami, cyclone, flood, volcano, drought, wildfire). Green/Orange/Red
  alert levels are model outputs that can escalate over time. Has an "episode"
  model (one event, many advisories).
- **ReliefWeb** - UN OCHA curated document library. Human-written sitreps,
  appeals, maps, hours-to-days later. Tells you about the *response*, not the
  detection. A firehose of near-duplicate reports of varying reliability.

## Constraints (from the course brief, treat as fixed)

- Output is `dashboard.html`, a morning sitrep, published 08:30 SGT.
- Runs unattended on a schedule (overnight loop).
- **Quiet when nothing has changed** - no daily "all clear" noise.
- Expected artefacts by end: `prd.html`, `system-view.html`,
  `implementation-notes.md`, `dashboard.html`, `goal.md`, at least one skill.
- Delivery cut into vertical slices; first slice is small and shippable.
- Timebox: three days (Plan / Autonomy / Trust).

## Things the design must handle (learned from the blindspot pass)

Not solutions yet - just problems I now know are real and must not be ignored:

- **Feeds mutate.** USGS revises magnitudes and deletes events; GDACS alerts
  escalate Green->Red; ReliefWeb reports get edited. Ingestion must upsert and
  diff, not just insert. Stateless "poll and summarise" will re-announce old
  events and miss revisions.
- **Cross-feed entity resolution is the core hard problem.** No shared event ID.
  Same disaster appears in multiple feeds (and multiple times within GDACS).
  GLIDE numbers are a partial join key. I must define what a single "disaster"
  entity is and how records merge.
- **Alert fatigue.** ~30 M4.5+ quakes/day, hundreds of GDACS Green events. The
  hard question is the threshold for surfacing something, not how to fetch data.
- **Silence is ambiguous.** "Quiet" could mean no disasters or a broken feed.
  Needs staleness / heartbeat monitoring or the agent fails silently during the
  exact event it exists for.
- **Magnitude is not impact.** Depth, time-of-day, population exposure matter.
  Prefer GDACS/PAGER impact estimates over raw magnitude.
- **ReliefWeb API access:** v2, and since 1 Nov 2025 the `appname` parameter
  must be pre-registered/approved, so just use the xml feed.

## Open decisions - [DECIDE]

- [Me personally ] **Reader.** Who reads the 08:30 sitrep and what do they do with it?
      (Me personally? A duty officer? A team channel?) This drives everything. 
- [natural hazard and humanitarian crises broadly] **Scope of hazards.** Just GDACS's ~7 natural hazards, or humanitarian
      crises broadly (conflict, displacement, epidemics - which these 3 feeds
      largely miss)? Design the data model for the wider scope even if v1 is narrow?
- [up to you, whatever is worth to be concerned about, i dont understand] **Surfacing threshold.** What earns a place in the sitrep? (e.g. GDACS
      Orange+, USGS PAGER yellow+, any ReliefWeb disaster record?) What is the
      re-alert policy when an event escalates or is revised?
- [Global] **Geographic focus.** Global, or a region of interest (e.g. Asia-Pacific)?
- [Headline only] **Sitrep shape.** How long, what sections, ranked how? Deep or headline-only?
- [] **"Something changed" definition.** What counts as a change worth breaking
      the silence for (new event / escalation / new report / revised impact)?
- [ ] **LLM vs deterministic code split.** My instinct: parsing, dedup and
      thresholding are code; the LLM does triage, cross-source synthesis and
      summarising the ReliefWeb pile. Confirm.
- [ ] **State store.** Where does "what I've already seen" live between runs?
- [ ] **Backtest.** Do I want to replay a past month to check catch-vs-miss
      before trusting it? (EM-DAT as reference catalogue.)

## Out of scope (initial instinct - [DECIDE] to confirm)

- Real-time / sub-hourly alerting (this is a once-a-morning digest).
- Feeds beyond the three named ones, for v1.
- Acting on disasters (tasking, dispatch) - this observes and reports only.
- A queryable UI beyond the static `dashboard.html`.
