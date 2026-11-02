---
name: 19-kickstarter-package
description: Kickstarter Package with enforced v0.11.1 contracts, repair routing and release evidence.
---
# Kickstarter Package

## Instructions

**Creator control.** Use the creator's approved scope. Ask before introducing a gameplay mechanic or mandatory story structure; an unattended run must omit unapproved additions. Adventure clocks, countdowns, forced deadlines, timed escalation and substitute pressure tracks are excluded from this build. Never add them during generation, audit or repair, or penalize exploration/rest with a timer. Estimated session length, historical dates and ordinary rules durations are not adventure timers.

Prepare creator-side campaign copy, reward/stretch concepts, FAQ, risks and image needs using the canonical pitch and declared deliverables. State unconfirmed manufacturing, costs and schedules as things to decide, not promises. Keep deliverable_claims explicit and avoid claims for unrendered art or unsupported page counts. Do not substitute generic policy knowledge for a creator's current platform review. Nothing in this skill publishes a campaign or certifies acceptance.

State what is true. Only say what something is NOT when players would reasonably assume it. Keep production_notes outside customer-facing prose.

State the selected combat intensity honestly. For low, use "low-combat investigation" where it describes the actual premise. Compatibility wording follows the creator's house policy: "compatible with fifth edition" with reviewed SRD attribution, rather than publisher brand names. Prices and deliverable claims require evidence. Production notes, estimates and unresolved release reviews stay in creator fields.

## Inputs: exact selectors

- `brief`: `level_band`, `play_time_hours`
- `marketing`: `elevator_pitch`, `short_description`, `feature_bullets`, `deliverable_claims`
- `art_direction`: `cover_spec`

Only the declared creator spec fields and named prerequisite keys in `skill.json` are supplied. Missing inputs fail explicitly. Oversized context is not silently truncated.

## Output contract

Return the exact shape in `output.schema.json`. The schema is executable and authoritative; do not rename its top-level fields. Local validation is mandatory for every provider; native JSON-schema output is used only when explicitly configured. Bad JSON/schema replies receive bounded correction attempts with the actual rejected reply and error. Valid raw responses are saved before modification.

Owns: `kickstarter`. Execution: `ai` / `kickstarter`.

## Verification and failure behavior

A successful call is not publication approval. Post-skill checks feed the repair controller; unrepairable/schema failures retain the checkpoint and raw evidence. Audit and repair pointers address canonical state (for example `/npcs/npcs/0/speech_style`), not a PDF page. Protected human values, IDs and unrelated fields may not be overwritten. Upstream changes invalidate affected output and audit hashes.

See `docs/REVIEW_RESPONSE.md` and `docs/ENFORCEMENT_MATRIX.md` for code-vs-prompt boundaries and regression tests. Quality, originality, play balance, art rights and visual proof are not guaranteed by field presence or a pass label.
