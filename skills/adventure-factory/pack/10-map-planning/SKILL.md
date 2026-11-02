---
name: 10-map-planning
description: Map Planning with enforced v0.11.1 contracts, repair routing and release evidence.
---
# Map Planning

## Instructions

**Creator control.** Use the creator's approved scope. Ask before introducing a gameplay mechanic or mandatory story structure; an unattended run must omit unapproved additions. Adventure clocks, countdowns, forced deadlines, timed escalation and substitute pressure tracks are excluded from this build. Never add them during generation, audit or repair, or penalize exploration/rest with a timer. Estimated session length, historical dates and ordinary rules durations are not adventure timers.

Produce explicit room geometry and connectivity from canonical locations, not arbitrary decorative rectangles. Every map-required location, including the finale, needs a map with unique id, location_ref and seed. Preserve all keyed room IDs; keep x/y/w/h in bounds and connect every room through valid corridors. Give thematic props, terrain, hazards, secret flags and meaningful tactical features. Use actual location dimensions and logic. Player variants must not expose GM markers or secret rooms. PNG variants receive host-written location_id, map_id, variant and spec hash metadata; a map for another location cannot satisfy this one. Planning prompts are not finished artwork.

Plan each map from the text, not apart from it. Every keyed area in the location text has the same number on its map, and every number on a map is a keyed area in the text; none is added, dropped or renumbered. Each map gets a square grid, a scale (optional `scale_feet`, feet per square, default 5, matching room dimensions), doors and secret doors marked, a legend, and a player copy with the secrets removed. Before returning, pass this checklist and fix any "no": (1) text areas and map numbers match both ways; (2) grid and scale are stated; (3) every door and secret door sits on a wall between connected rooms; (4) legend lists every symbol used; (5) the player copy shows no secret door, secret room or GM marker; (6) every room connects to the rest; (7) the finale has its own map.

State what is true. Only say what something is NOT when players would reasonably assume it. Keep production_notes outside customer-facing prose.

One geometry feeds every variant. Put every gameplay-important ledge, walkway, control and hazard in tactical_features with an explicit point or square list, label and visibility. Coordinates are zero-indexed GLOBAL map-square positions; point coordinates are square centers and square pairs identify occupied cells. Document this convention in production_notes, not in the customer key. Supply axis-aligned corridor paths and door segments in global grid-line coordinates. A door occupies one boundary segment and includes its open/closed/locked state; hidden doors use secret=true. Player labels include only observable facts. Avoid putting a public feature inside a secret room.

## Inputs: exact selectors

- `brief`: `map_needs`
- `world`: `visual_style`
- `locations`: `locations.*.id`, `locations.*.name`, `locations.*.map_required`, and per room `locations.*.rooms.*.id`, `name`, `purpose`, `width`, `height`, `ceiling`, `lighting`, `doors`, `connections`, `contents`, `interactive_features`, `hidden_elements`, `treasure`, `hazards`, `encounter_refs`, `hazard_refs`
- `encounters`: `encounters.*.location_ref`, `encounters.*.battlefield`, `encounters.*.hazards`

Only the declared creator spec fields and named prerequisite keys in `skill.json` are supplied. Missing inputs fail explicitly. Oversized context is not silently truncated.

0.11.3 narrowed the room selector to geometry, connectivity, contents, features, secrets and hazards. Read-aloud text, room development, clue text, clue/creature/item reference lists and production notes are no longer sent (measured on a six-level, 96-room dungeon: 200,950 to 132,016 characters of location context). This is a single call for all maps, not a per-entity call.

## Output contract

Return the exact shape in `output.schema.json`. The schema is executable and authoritative; do not rename its top-level fields. Local validation is mandatory for every provider; native JSON-schema output is used only when explicitly configured. Bad JSON/schema replies receive bounded correction attempts with the actual rejected reply and error. Valid raw responses are saved before modification.

Owns: `maps`. Execution: `ai` / `maps`.

## Verification and failure behavior

A successful call is not publication approval. Post-skill checks feed the repair controller; unrepairable/schema failures retain the checkpoint and raw evidence. Audit and repair pointers address canonical state (for example `/npcs/npcs/0/speech_style`), not a PDF page. Protected human values, IDs and unrelated fields may not be overwritten. Upstream changes invalidate affected output and audit hashes.

See `docs/REVIEW_RESPONSE.md` and `docs/ENFORCEMENT_MATRIX.md` for code-vs-prompt boundaries and regression tests. Quality, originality, play balance, art rights and visual proof are not guaranteed by field presence or a pass label.
