---
name: 08-creature-bestiary
description: Creature Bestiary with enforced v0.11.1 contracts, repair routing and release evidence.
---
# Creature Bestiary

## Instructions

**Creator control.** Use the creator's approved scope. Ask before introducing a gameplay mechanic or mandatory story structure; an unattended run must omit unapproved additions. Adventure clocks, countdowns, forced deadlines, timed escalation and substitute pressure tracks are excluded from this build. Never add them during generation, audit or repair, or penalize exploration/rest with a timer. Estimated session length, historical dates and ordinary rules durations are not adventure timers.

Define every creature in the registry or encounters, including combat-capable NPCs, finale manifestations and threats that may be fought OR bargained with. In a 5e profile produce the complete numeric stat_block in the schema: AC, HP and matching hit dice, CR, all ability scores, movement modes, saving throws, actions and effects. Use the creator-supplied mechanics_profile, not an invented official CR table. Each attack/save action must have exact bonus/DC, reach/range, damage and effect as applicable. Use stat_block null only for an explicitly system-neutral brief. Vague offense/defense prose is never a rules replacement. Provide distinct lore, behavior, tactics, weaknesses and illustration direction.

State what is true. Only say what something is NOT when players would reasonably assume it. Keep production_notes outside customer-facing prose.

Every creature requires a size and creature type (for example Medium construct), including system-neutral profiles. Use the selected combat intensity and the encounter combatant counts. Put attack range and reach in the exact rules fields, with complete targets and effects.

## Inputs: exact selectors

- `brief`: `rules_profile`, `level_band`, `party_size`
- `world`: `visual_style`
- `story`: `entity_registry`
- `encounters`: `encounters.*.id`, `encounters.*.participants`, `encounters.*.creature_refs`, `encounters.*.tactics`, `encounters.*.rules_mentions`

Only the declared creator spec fields and named prerequisite keys in `skill.json` are supplied. Missing inputs fail explicitly. Oversized context is not silently truncated.

## Output contract

Return the exact shape in `output.schema.json`. The schema is executable and authoritative; do not rename its top-level fields. Local validation is mandatory for every provider; native JSON-schema output is used only when explicitly configured. Bad JSON/schema replies receive bounded correction attempts with the actual rejected reply and error. Valid raw responses are saved before modification.

Owns: `creatures`. Execution: `ai` / `bestiary`.

## Verification and failure behavior

A successful call is not publication approval. Post-skill checks feed the repair controller; unrepairable/schema failures retain the checkpoint and raw evidence. Audit and repair pointers address canonical state (for example `/npcs/npcs/0/speech_style`), not a PDF page. Protected human values, IDs and unrelated fields may not be overwritten. Upstream changes invalidate affected output and audit hashes.

See `docs/REVIEW_RESPONSE.md` and `docs/ENFORCEMENT_MATRIX.md` for code-vs-prompt boundaries and regression tests. Quality, originality, play balance, art rights and visual proof are not guaranteed by field presence or a pass label.
