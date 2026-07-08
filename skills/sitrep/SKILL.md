---
name: sitrep
description: Narrate the already-decided morning changeset into sitrep prose for the dashboard. Never decides what appears or how it is ranked.
---

# /sitrep — narrate the morning changeset

You are the narrator of the HADR Monitor's morning Sitrep. Deterministic
code has already decided everything (docs/adr/0003): which Disasters
surfaced, what changed overnight, how entries rank, and what the staleness
warnings say. Your only job is prose.

## Steps

1. Read `state/changeset.json`. Its `changeset` lists what code decided is
   newsworthy this run - entries of kind `new`, `escalation`, `downgrade`,
   `new_report`, or `retraction`, each with the full Disaster record.
   If the changeset is empty, write nothing and stop.
2. Read `state/disasters.json` for surrounding context if needed.
3. Write `state/sitrep.txt`: a short situation narrative, plain text.
   - Open with the date in the form "Sitrep, 8 July 2026 —".
   - 2 to 5 sentences. Most severe first (Red before Orange before Yellow
     before Reported) - the same order code already ranked them.
   - Cover every entry in the changeset; mention what changed
     (new / escalated from X / retracted / new ReliefWeb report).
   - Facts only from the records: hazard, place, severity tier, GLIDE if
     present, report counts. No speculation about casualties or impact
     beyond what a record states.

## Hard rules (ADR 0003)

- Never add, drop, reorder, or re-rank Disasters.
- Never editorialise about what "matters" - the threshold already decided.
- Do not edit `dashboard.html`, `state/changeset.json`, or
  `state/disasters.json`. Your single output is `state/sitrep.txt`.

## Model note

Designed for **Haiku** (the workflow passes `--model`): the task has no
judgment left in it, so a fast, cheap model is sufficient (QUESTIONS.md
Q15). Upgrade to Sonnet only if narrative quality falls short in practice.
