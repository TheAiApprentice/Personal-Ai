---
name: 14-continuity-audit
description: Continuity Audit with enforced v0.11.1 contracts, repair routing and release evidence.
---
# Continuity Audit

## Instructions

**Creator control.** Use the creator's approved scope. Ask before introducing a gameplay mechanic or mandatory story structure; an unattended run must omit unapproved additions. Adventure clocks, countdowns, forced deadlines, timed escalation and substitute pressure tracks are excluded from this build. Never add them during generation, audit or repair, or penalize exploration/rest with a timer. Estimated session length, historical dates and ordinary rules durations are not adventure timers.

Trace canonical names, IDs, relationships, timing, deaths, knowledge, faction activity, clues, keyed rooms, map geometry and endings. Flag missing factions, unexplained documents, impossible chronology, stale names and incomplete destinations. Each blocking finding must point at the exact faulty field and owning skill. Compare each chapter against the plot spine (see 03-story-architecture) and flag every disagreement as a blocking finding pointing at the chapter field and its owning skill: pillar or seal count, who built them, what holds or wakes the creature, who wants it changed and why, and the endings. Also flag a chapter box (`purpose`) that disagrees with the spine. The chapter pass receives the spine read-only. Check section by section; never re-check a section that passed and is unchanged. State fail even when a serious unresolved issue cannot be automatically repaired. The host reapplies audits after changes and counts both fail verdicts and blocking findings.

## Inputs: exact selectors

- `world`: `background`, `secrets`
- `factions`: `factions`
- `story`: `chapters`, `entity_registry`, `endings`
- `clues`: `clue_web`, `critical_revelations`
- `npcs`: `npcs.*.id`, `npcs.*.name`, `npcs.*.history`, `npcs.*.secret`, `npcs.*.relationships`
- `locations`: `locations.*.id`, `locations.*.rooms`
- `encounters`: `encounters.*.id`, `encounters.*.location_ref`, `encounters.*.consequences`
- `maps`: `maps.*.location_ref`, `maps.*.rooms`
- `handouts`: `handouts`

Only the declared creator spec fields and named prerequisite keys in `skill.json` are supplied. Missing inputs fail explicitly. Oversized context is not silently truncated.

## Section passes (0.11.3)

`skill.json` `audit_sections` splits this audit into one pass per story chapter plus a cross-section pass. A chapter pass reads that chapter and the clues, NPCs, level, encounters, map and handouts placed in it, plus read-only `id`, `name`, `secret` and `relationships` of NPCs and the route fields (`clue`, `reveals`, `found_at_refs`, `points_to_refs`, `backup_refs`) of clues it mentions from other chapters. The cross-section pass reads `world`, `factions`, `story.entity_registry`, `story.endings`, `clues.critical_revelations` and the section index: one row per entity with its canonical path, section, ID, name, every `*_ref`/`*_refs` field and, for clues, `reveals`. It owns continuity between chapters. Entities the host cannot place in a chapter get their own `__unsectioned__` pass. Sectioned lists keep their canonical array index as object keys, so finding pointers stay exact. A pass whose fingerprint is unchanged is reused, never re-asked; the cross-section pass is re-audited when an index row changes. See `docs/AUDIT_EFFICIENCY_CHANGELOG.md`.

## Output contract

Return the exact shape in `output.schema.json`. The schema is executable and authoritative; do not rename its top-level fields. Local validation is mandatory for every provider; native JSON-schema output is used only when explicitly configured. Bad JSON/schema replies receive bounded correction attempts with the actual rejected reply and error. Valid raw responses are saved before modification.

Owns: `continuity_audit`. Execution: `ai` / `continuity`.

## Verification and failure behavior

A successful call is not publication approval. Post-skill checks feed the repair controller; unrepairable/schema failures retain the checkpoint and raw evidence. Audit and repair pointers address canonical state (for example `/npcs/npcs/0/speech_style`), not a PDF page. Protected human values, IDs and unrelated fields may not be overwritten. Upstream changes invalidate affected output and audit hashes.

See `docs/REVIEW_RESPONSE.md` and `docs/ENFORCEMENT_MATRIX.md` for code-vs-prompt boundaries and regression tests. Quality, originality, play balance, art rights and visual proof are not guaranteed by field presence or a pass label.
