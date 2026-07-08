---
status: accepted
---

# Code decides, the LLM narrates

Every decision that must give the same answer twice — what crosses the
surfacing threshold, what counts as a change, which Reports are the same
[Disaster](../../CONTEXT.md), which GDACS field is authoritative, how a
revision or retraction is handled, what counts as feed staleness — is
deterministic Python, not a model call. The headless `/sitrep` skill's only
job is turning an already-decided, already-merged Disaster record into
sitrep prose; it never decides what appears or how it's ranked.

We chose this because `.github/workflows/sitrep.yml.disabled` already
encodes the rule ("a deterministic script decides whether anything changed;
a headless model call runs only if it did"), and because every upstream
decision made while shaping this system turned out to have a testable,
deterministic answer — leaving the model a well-scoped job it's actually
good at (readable prose from structured facts) instead of one it would be
unreliable at (consistently applying a numeric threshold).

## Consequences

The `/sitrep` skill runs on Haiku by default — its job has no independent
judgment left in it, so a fast, cheap model is sufficient. Upgrade only if
narrative quality falls short in practice.
