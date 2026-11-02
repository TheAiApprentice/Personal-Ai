---
name: 04-clue-network
description: Clue Network with enforced v0.11.1 contracts, repair routing and release evidence.
---
# Clue Network

## Instructions

**Creator control.** Use the creator's approved scope. Ask before introducing a gameplay mechanic or mandatory story structure; an unattended run must omit unapproved additions. Adventure clocks, countdowns, forced deadlines, timed escalation and substitute pressure tracks are excluded from this build. Never add them during generation, audit or repair, or penalize exploration/rest with a timer. Estimated session length, historical dates and ordinary rules durations are not adventure timers.

Define actual clues, not labels in a quick reference. Each clue needs a stable ID, discoverable evidence, what it reveals, defined discovery and destination refs, explicit check/DC or automatic discovery, failure recovery, and a backup route at a DIFFERENT valid source. Every critical_revelation lists existing clue IDs and a achievable min_clues. Meet the brief's independent-source requirement; three clues behind the same NPC are not three routes. Trace every clue to the plot spine (see 03-story-architecture): each non-false clue's `reveals` supports a spine fact (what the creature is, why the hold works, who wants it changed, how it can end), and every spine fact has at least one critical_revelation. A clue may not state a count, builder or condition that differs from the spine. Include false leads that can be disproven. Never refer to an undescribed ledger or document.

State what is true. Only say what something is NOT when players would reasonably assume it. Keep production_notes outside customer-facing prose.

## Inputs: exact selectors

- `brief`: `minimum_clue_routes`
- `world`: `secrets`
- `story`: `entity_registry`, `chapters`, `endings`

Only the declared creator spec fields and named prerequisite keys in `skill.json` are supplied. Missing inputs fail explicitly. Oversized context is not silently truncated.

## Output contract

Return the exact shape in `output.schema.json`. The schema is executable and authoritative; do not rename its top-level fields. Local validation is mandatory for every provider; native JSON-schema output is used only when explicitly configured. Bad JSON/schema replies receive bounded correction attempts with the actual rejected reply and error. Valid raw responses are saved before modification.

Owns: `clues`. Execution: `ai` / `clues`.

## Verification and failure behavior

A successful call is not publication approval. Post-skill checks feed the repair controller; unrepairable/schema failures retain the checkpoint and raw evidence. Audit and repair pointers address canonical state (for example `/npcs/npcs/0/speech_style`), not a PDF page. Protected human values, IDs and unrelated fields may not be overwritten. Upstream changes invalidate affected output and audit hashes.

See `docs/REVIEW_RESPONSE.md` and `docs/ENFORCEMENT_MATRIX.md` for code-vs-prompt boundaries and regression tests. Quality, originality, play balance, art rights and visual proof are not guaranteed by field presence or a pass label.
