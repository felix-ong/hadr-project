---
status: accepted
---

# ReliefWeb: RSS permanently, not the v2 API

ReliefWeb's v2 API requires a pre-approved `appname`, requested via a form
with no stated turnaround; the RSS feed needs no approval. We build against
RSS permanently rather than treating it as a stopgap until API approval
clears — one ReliefWeb integration to maintain, not two, and no dependency
on an external approval process with an unknown timeline.

GLIDE numbers are still extractable from RSS: the `<description>` field
embeds a `<div class="tag glide">Glide: ...</div>` tag as HTML-escaped text,
so [entity resolution](0001-glide-first-entity-resolution.md) isn't
affected — it needs an HTML-tag scrape instead of a clean JSON field.

## Consequences

RSS lacks the API's structured filtering and pagination, and is described
in `feeds/reliefweb.md` as "a firehose of near-duplicate reports of varying
reliability" — expect more raw duplication on the ReliefWeb side than the
API would have provided.
