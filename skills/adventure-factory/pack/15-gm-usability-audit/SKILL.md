---
name: 15-gm-usability-audit
description: GM Usability Audit with enforced v0.11.1 contracts, repair routing and release evidence.
---
# GM Usability Audit

## Instructions

**Creator control.** Use the creator's approved scope. Ask before introducing a gameplay mechanic or mandatory story structure; an unattended run must omit unapproved additions. Adventure clocks, countdowns, forced deadlines, timed escalation and substitute pressure tracks are excluded from this build. Never add them during generation, audit or repair, or penalize exploration/rest with a timer. Estimated session length, historical dates and ordinary rules durations are not adventure timers.

Ask whether a GM unfamiliar with the project could run it without inventing required rules or missing story links. Check hooks, investigation destinations, clue availability/backups, readable room keys, encounter triggers, enemy rules, alternate resolutions, rewards and endings. Inspect prose for mechanics not included in inventories; deterministic checks cannot discover every invented noun. Check that every chapter opens with its box in `purpose` (Purpose, Learn, Ends, Leads to; see 03-story-architecture), that each line is filled, and that it matches the plot spine and the next chapter; a missing or mismatched box is a finding on that chapter. Check that a new GM could explain the plot from the spine page alone. Return verdict/findings with exact field paths and a quick_reference grounded in actual canonical entries. Do not introduce a new fourth critical clue into the quick reference unless it already exists.

## Inputs: exact selectors

- `story`: `chapters`, `advancement`, `endings`
- `clues`: `clue_web`, `critical_revelations`
- `npcs`: `npcs.*.name`, `npcs.*.speech_style`, `npcs.*.sample_lines`, `npcs.*.reactions`
- `locations`: `locations.*.id`, `locations.*.rooms`
- `encounters`: `encounters`
- `creatures`: `creatures.*.id`, `creatures.*.stat_block`
- `items`: `items`
- `maps`: `maps.*.location_ref`, `maps.*.rooms`
- `handouts`: `handouts`

Only the declared creator spec fields and named prerequisite keys in `skill.json` are supplied. Missing inputs fail explicitly. Oversized context is not silently truncated.

## Section passes (0.11.3)

`skill.json` `audit_sections` splits this audit into one pass per story chapter plus a cross-section pass. A chapter pass reads everything a GM runs in that chapter (chapter, clues, NPCs, level, encounters, creatures, items, map, handouts), plus read-only creature stat blocks, NPC voice fields and item `id`, `name`, `rarity` and `exact_rules_text` it uses from other chapters. The cross-section pass reads `story.advancement`, `story.endings`, `clues.critical_revelations` and the section index. Every pass returns the full schema; the merged `quick_reference` is the ordered union of all passes. Entities the host cannot place in a chapter get their own `__unsectioned__` pass. A pass whose fingerprint is unchanged is reused, never re-asked. See `docs/AUDIT_EFFICIENCY_CHANGELOG.md`.

## Output contract

Return the exact shape in `output.schema.json`. The schema is executable and authoritative; do not rename its top-level fields. Local validation is mandatory for every provider; native JSON-schema output is used only when explicitly configured. Bad JSON/schema replies receive bounded correction attempts with the actual rejected reply and error. Valid raw responses are saved before modification.

Owns: `gm_audit`. Execution: `ai` / `gm_auditor`.

## Verification and failure behavior

A successful call is not publication approval. Post-skill checks feed the repair controller; unrepairable/schema failures retain the checkpoint and raw evidence. Audit and repair pointers address canonical state (for example `/npcs/npcs/0/speech_style`), not a PDF page. Protected human values, IDs and unrelated fields may not be overwritten. Upstream changes invalidate affected output and audit hashes.

See `docs/REVIEW_RESPONSE.md` and `docs/ENFORCEMENT_MATRIX.md` for code-vs-prompt boundaries and regression tests. Quality, originality, play balance, art rights and visual proof are not guaranteed by field presence or a pass label.
