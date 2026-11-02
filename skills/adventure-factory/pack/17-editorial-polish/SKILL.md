---
name: 17-editorial-polish
description: Editorial Polish with enforced v0.11.1 contracts, repair routing and release evidence.
---
# Editorial Polish

## Instructions

**Creator control.** Use the creator's approved scope. Ask before introducing a gameplay mechanic or mandatory story structure; an unattended run must omit unapproved additions. Adventure clocks, countdowns, forced deadlines, timed escalation and substitute pressure tracks are excluded from this build. Never add them during generation, audit or repair, or penalize exploration/rest with a timer. Estimated session length, historical dates and ordinary rules durations are not adventure timers.

Propose precise text improvements to weak, repetitive or unclear draft prose without rewriting unrelated content. Return verdict, findings and patches. Each patch uses op replace, exact canonical path, the exact current before string, replacement value string and a reason. Only individual narrative text fields may change here: no IDs, object replacements, numerical rules, audits, metadata or approval fields. Human-locked text is immutable. The host applies accepted unlocked patches, logs before/after, validates owner schemas and reruns all audits; prose must actually reach the rendered book rather than remain in a suggestion report.

Repeat scan (before render; the host also flags exact repeated sentences as `repeated_text` warnings, with the canonical entry and the repeat paths): find any fact or character description written in more than one place. Keep it in the canonical entry (the NPC or location entry, or the plot spine) and patch every other occurrence to "see NPC: name, page X" or "see section X". Do not touch read-aloud text. Never patch the canonical entry itself for a repeat.

Stop rule: return no patches unless clarity, consistency or readability is broken. Round 0 is the single application pass. Later passes may offer non-blocking suggestions; stylistic preferences alone never require another repair. Prioritize negation_warnings by stating useful truths rather than arguing with imagined objections. Send substantive gameplay defects to the responsible audit instead of editing statistics.

## Inputs: exact selectors

- `story`: `chapters`, `endings`
- `npcs`: `npcs`
- `locations`: `locations`
- `encounters`: `encounters`

Only the declared creator spec fields and named prerequisite keys in `skill.json` are supplied. Missing inputs fail explicitly. Oversized context is not silently truncated.

## Section passes (0.11.3)

`skill.json` `audit_sections` splits the polish into one pass per story chapter plus a cross-section pass. A chapter pass reads the chapter, NPCs, level and encounters placed in it, and receives only the negation warnings whose paths fall in that pass. The cross-section pass reads `story.endings`, the section index and the remaining warnings. Patches from all passes are merged, one proposal per field. Round-zero application, owner boundaries, stable IDs, before-values and locks are unchanged. A pass whose fingerprint is unchanged is reused, never re-asked. See `docs/AUDIT_EFFICIENCY_CHANGELOG.md`.

## Output contract

Return the exact shape in `output.schema.json`. The schema is executable and authoritative; do not rename its top-level fields. Local validation is mandatory for every provider; native JSON-schema output is used only when explicitly configured. Bad JSON/schema replies receive bounded correction attempts with the actual rejected reply and error. Valid raw responses are saved before modification.

Owns: `polish`. Execution: `ai` / `polish`.

## Verification and failure behavior

A successful call is not publication approval. Post-skill checks feed the repair controller; unrepairable/schema failures retain the checkpoint and raw evidence. Audit and repair pointers address canonical state (for example `/npcs/npcs/0/speech_style`), not a PDF page. Protected human values, IDs and unrelated fields may not be overwritten. Upstream changes invalidate affected output and audit hashes.

See `docs/REVIEW_RESPONSE.md` and `docs/ENFORCEMENT_MATRIX.md` for code-vs-prompt boundaries and regression tests. Quality, originality, play balance, art rights and visual proof are not guaranteed by field presence or a pass label.
