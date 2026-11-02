---
name: 13-mechanics-balance
description: Mechanics Balance with enforced v0.11.1 contracts, repair routing and release evidence.
---
# Mechanics Balance

## Instructions

**Creator control.** Use the creator's approved scope. Ask before introducing a gameplay mechanic or mandatory story structure; an unattended run must omit unapproved additions. Adventure clocks, countdowns, forced deadlines, timed escalation and substitute pressure tracks are excluded from this build. Never add them during generation, audit or repair, or penalize exploration/rest with a timer. Estimated session length, historical dates and ordinary rules durations are not adventure timers.

Audit exact runnable rules, action economy, CR profile ranges, rest assumptions, rewards, hazards, DCs, damage, items, variants and scaling. Inspect prose for unregistered mechanical entities as well as explicit reference lists. A creature with moderate HP, a missing hazard/check field, a vague item or an unstattted combat NPC is blocking. A numeric profile is a sanity screen, not an official CR calculation or playtest. Return verdict plus findings in the output schema. Each finding must identify a canonical-state JSON Pointer, its owning skill, the problem and a required fix. Do not replace the book yourself and do not certify balance based on empty fields.

## Inputs: exact selectors

- `brief`: `rules_profile`, `level_band`, `party_size`
- `story`: `advancement`
- `encounters`: `encounters`, `random_encounters`
- `creatures`: `creatures`
- `items`: `items`

Only the declared creator spec fields and named prerequisite keys in `skill.json` are supplied. Missing inputs fail explicitly. Oversized context is not silently truncated.

## Section passes (0.11.3)

`skill.json` `audit_sections` splits this audit into one pass per story chapter plus a cross-section pass. A chapter pass reads the encounters, creatures and items placed in that chapter, plus read-only `id`, `name`, `size`, `type` and `stat_block` of creatures, and the rules fields of items, that its encounters use from other chapters. The cross-section pass reads `brief`, `story.advancement`, `encounters.random_encounters` and the section index. Entities the host cannot place in a chapter get their own `__unsectioned__` pass. Sectioned lists keep their canonical array index as object keys, so finding pointers stay exact. The merged result has the same schema; a fail in any pass is a fail. A pass whose fingerprint (exact request input, skill, auditor identity, schema) is unchanged is reused, never re-asked. See `docs/AUDIT_EFFICIENCY_CHANGELOG.md`.

## Output contract

Return the exact shape in `output.schema.json`. The schema is executable and authoritative; do not rename its top-level fields. Local validation is mandatory for every provider; native JSON-schema output is used only when explicitly configured. Bad JSON/schema replies receive bounded correction attempts with the actual rejected reply and error. Valid raw responses are saved before modification.

Owns: `mechanics_audit`. Execution: `ai` / `mechanics_audit`.

## Verification and failure behavior

A successful call is not publication approval. Post-skill checks feed the repair controller; unrepairable/schema failures retain the checkpoint and raw evidence. Audit and repair pointers address canonical state (for example `/npcs/npcs/0/speech_style`), not a PDF page. Protected human values, IDs and unrelated fields may not be overwritten. Upstream changes invalidate affected output and audit hashes.

See `docs/REVIEW_RESPONSE.md` and `docs/ENFORCEMENT_MATRIX.md` for code-vs-prompt boundaries and regression tests. Quality, originality, play balance, art rights and visual proof are not guaranteed by field presence or a pass label.
