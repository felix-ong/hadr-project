---
status: accepted
---

# GLIDE-first, precision-biased cross-feed entity resolution

GDACS, USGS and ReliefWeb share no common event ID, and GLIDE numbers only
cover some records. We merge two feed Reports into one [Disaster](../../CONTEXT.md)
when their GLIDE numbers match, or — absent a GLIDE — when hazard type
matches and the records are close in both space (~250km) and time
(~24-48h). Ambiguous cases stay as separate, cross-referenced entries
rather than being merged.

We picked this over a looser fallback because in a HADR context, wrongly
conflating two distinct disasters is worse than showing a duplicate line
for the same one: a false merge misleads on scale and location, a
duplicate is just noise.

## Considered options

- **Aggressive merge** — looser space/time windows, fewer duplicates, more
  false merges. Rejected: the failure mode is worse than the noise it saves.
- **GLIDE-only** — simplest, safest, but USGS and fresh GDACS events rarely
  have a GLIDE yet, so most same-day cross-feed matches wouldn't merge.
- **No auto-merge in v1** — defer entity resolution entirely. Rejected:
  REQS.md calls this the core hard problem; deferring it defers the point
  of the exercise.

## Consequences

Same-disaster records without a GLIDE and outside the space/time window
won't merge automatically — expect occasional duplicate sitrep entries
until a GLIDE number catches up (typically once ReliefWeb picks the story
up).
