---
name: 09-item-treasure-design
description: Item & Treasure Design with enforced v0.11.1 contracts, repair routing and release evidence.
---
# Item & Treasure Design

## Instructions

**Creator control.** Use the creator's approved scope. Ask before introducing a gameplay mechanic or mandatory story structure; an unattended run must omit unapproved additions. Adventure clocks, countdowns, forced deadlines, timed escalation and substitute pressure tracks are excluded from this build. Never add them during generation, audit or repair, or penalize exploration/rest with a timer. Estimated session length, historical dates and ordinary rules durations are not adventure timers.

Create original, useful treasure with stable IDs, contextual discovery and a purpose in play. Each item needs appearance, history, rarity, explicit attunement status, and exact_rules_text plus structured activation, target, numeric range_ft, duration, uses, recharge and limitations. Avoid effects such as brief warning or moderate benefit without rules. Book and cards use the same record. Ensure encounter/room item refs resolve and give treasure/advancement guidance consistent with the brief.

State what is true. Only say what something is NOT when players would reasonably assume it. Keep production_notes outside customer-facing prose.

## Inputs: exact selectors

- `brief`: `rules_profile`, `level_band`
- `story`: `entity_registry`, `advancement`
- `locations`: `locations.*.id`, `locations.*.name`, `locations.*.treasure`, and per room `locations.*.rooms.*.id`, `name`, `contents`, `hidden_elements`, `treasure`, `item_refs`, `encounter_refs`
- `encounters`: `encounters.*.item_refs`, `encounters.*.rewards`, `encounters.*.rules_mentions`

Only the declared creator spec fields and named prerequisite keys in `skill.json` are supplied. Missing inputs fail explicitly. Oversized context is not silently truncated.

0.11.3 narrowed the room selector from whole rooms to the fields that place and describe treasure. Read-aloud text, room development, purpose, doors, lighting and clue text are no longer sent (measured on a six-level, 96-room dungeon: 200,558 to 45,177 characters of location context). This is a single call for all items, not a per-entity call.

## Output contract

Return the exact shape in `output.schema.json`. The schema is executable and authoritative; do not rename its top-level fields. Local validation is mandatory for every provider; native JSON-schema output is used only when explicitly configured. Bad JSON/schema replies receive bounded correction attempts with the actual rejected reply and error. Valid raw responses are saved before modification.

Owns: `items`. Execution: `ai` / `items`.

## Verification and failure behavior

A successful call is not publication approval. Post-skill checks feed the repair controller; unrepairable/schema failures retain the checkpoint and raw evidence. Audit and repair pointers address canonical state (for example `/npcs/npcs/0/speech_style`), not a PDF page. Protected human values, IDs and unrelated fields may not be overwritten. Upstream changes invalidate affected output and audit hashes.

See `docs/REVIEW_RESPONSE.md` and `docs/ENFORCEMENT_MATRIX.md` for code-vs-prompt boundaries and regression tests. Quality, originality, play balance, art rights and visual proof are not guaranteed by field presence or a pass label.
