# CLAUDE.md

<!-- Fill in at least three conventions below before your first prompt.
     An empty conventions file is also a decision — just not one you made. -->

## Language & tooling

Python for everything in `scripts/` — fetching, entity resolution,
thresholding, state diffing. See [docs/adr/0003-code-decides-llm-narrates.md](docs/adr/0003-code-decides-llm-narrates.md)
for why this is code and not a model call.

## Test command

`pytest`

## Conventions

- Domain vocabulary lives in `CONTEXT.md` — check it before introducing a
  new term for something it already names (e.g. "Disaster" vs. "Report").
- State ("what's already been seen") lives in `state/*.json`, committed to
  the repo by the scheduled workflow each run — see `docs/adr/`.
- `dashboard.html` is the one generated artefact committed to the repo
  (see `.gitignore`); it is overwritten in place each run, not archived —
  history lives in `git log -p dashboard.html`.
- The `/sitrep` skill only narrates a Disaster record that code has already
  decided is newsworthy; it never decides what appears or how it's ranked.

## Deviations policy

Anything built that departs from `REQS.md`, this file, or a `docs/adr/`
decision goes in `implementation-notes.md` under Deviations, with the
reason. An undocumented deviation is a bug.
