---
name: 18-marketing-copy
description: Marketing Copy with enforced v0.11.1 contracts, repair routing and release evidence.
---
# Marketing Copy

## Instructions

**Creator control.** Use the creator's approved scope. Ask before introducing a gameplay mechanic or mandatory story structure; an unattended run must omit unapproved additions. Adventure clocks, countdowns, forced deadlines, timed escalation and substitute pressure tracks are excluded from this build. Never add them during generation, audit or repair, or penalize exploration/rest with a timer. Estimated session length, historical dates and ordinary rules durations are not adventure timers.

Draft a truthful pitch, audience, tags and feature copy grounded in the completed content plan. Declare each deliverable promise in deliverable_claims. Do not invent map counts, page counts, original art, print readiness, production prices or completion status. The host compares claims against the actual rendered inventory later. This is creator-side copy, not customer book text. A canned  is never usable as a real-model sales showcase.

State what is true. Only say what something is NOT when players would reasonably assume it. Keep production_notes outside customer-facing prose.

State the selected combat intensity honestly. For low, use "low-combat investigation" where it describes the actual premise. Compatibility wording follows the creator's house policy: "compatible with fifth edition" with reviewed SRD attribution, rather than publisher brand names. Prices and deliverable claims require evidence. Production notes, estimates and unresolved release reviews stay in creator fields.

## Inputs: exact selectors

- `brief`: `tone`, `level_band`, `play_time_hours`
- `world`: `summary`, `themes`
- `story`: `endings`
- `maps`: `maps.*.id`
- `handouts`: `handouts.*.id`
- `items`: `items.*.id`

Only the declared creator spec fields and named prerequisite keys in `skill.json` are supplied. Missing inputs fail explicitly. Oversized context is not silently truncated.

## Output contract

Return the exact shape in `output.schema.json`. The schema is executable and authoritative; do not rename its top-level fields. Local validation is mandatory for every provider; native JSON-schema output is used only when explicitly configured. Bad JSON/schema replies receive bounded correction attempts with the actual rejected reply and error. Valid raw responses are saved before modification.

Owns: `marketing`. Execution: `ai` / `marketing`.

## Verification and failure behavior

A successful call is not publication approval. Post-skill checks feed the repair controller; unrepairable/schema failures retain the checkpoint and raw evidence. Audit and repair pointers address canonical state (for example `/npcs/npcs/0/speech_style`), not a PDF page. Protected human values, IDs and unrelated fields may not be overwritten. Upstream changes invalidate affected output and audit hashes.

See `docs/REVIEW_RESPONSE.md` and `docs/ENFORCEMENT_MATRIX.md` for code-vs-prompt boundaries and regression tests. Quality, originality, play balance, art rights and visual proof are not guaranteed by field presence or a pass label.
