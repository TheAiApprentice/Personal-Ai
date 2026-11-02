---
name: 06-location-development
description: Location Development with enforced v0.11.1 contracts, repair routing and release evidence.
---
# Location Development

## Instructions

**Creator control.** Use the creator's approved scope. Ask before introducing a gameplay mechanic or mandatory story structure; an unattended run must omit unapproved additions. Adventure clocks, countdowns, forced deadlines, timed escalation and substitute pressure tracks are excluded from this build. Never add them during generation, audit or repair, or penalize exploration/rest with a timer. Estimated session length, historical dates and ordinary rules durations are not adventure timers.

Develop exactly the requested registry location as somewhere a GM can run immediately. Aim for 300–500 words of site-level material and 180–300 useful words per important keyed room. Keep arrival and room read-aloud passages to 40–90 words. Lead with observable features: entrances, light, sound, surfaces and occupants. Place history, hidden mechanisms and explanatory lore in separate GM fields. Describe what a character can interact with and the observable result.

Assign each room a practical original purpose and a current use. Explain why it connects to neighboring rooms. Preserve the room IDs used by the story, clues and encounters. Give dimensions and heights in consistent units, lighting, doors or passages, and the route to the next area. A room's furniture should follow its purpose: a counting desk, drying rack, sluice chain or cooking hearth. Describe the same geometry the map will show; coordinates needed for combat belong in structured tactical features rather than decorative prose alone.

Layer discovery. Say what is obvious on entry, what deliberate examination reveals, and what a risky interaction changes. Essential clues are found automatically through a stated action and retain a backup source elsewhere. Optional checks may secure treasure, reduce exposure or preserve an advantage. For each hazard specify its warning, trigger and countermeasure through the encounter record; use that record consistently instead of introducing a second unexplained effect.

Give treasure a location and an amount or item reference. Give occupants a reason to remain, react or leave. Loud combat or damage to machinery may change the site as a direct consequence of that action. Describe the physical effect and any response from occupants of adjacent rooms. Do not schedule deterioration during exploration, rest or absence. Design room entries for quick lookup: distinctive first impression, interactable details, consequences, exits.

Failure modes: Feature soup lists scenery with no use; Impossible adjacency contradicts the map; Hidden-clue bottleneck stalls play; Repeated atmosphere makes rooms blend together; Treasure without placement forces the GM to invent it.

Bad: “The chamber is ancient and damp. There are several objects here.”
Good: “Water drips through the tally desk into an empty copper pan. Three old waterline marks on its rim record earlier floods. Raising the desk exposes the gate release diagram automatically; dragging it to the west doorway gives cover but jams that exit.” Each visible detail supports action.

Put production limitations and renderer instructions only in production_notes. The customer-facing room text should describe the world and explain play.

State what is true. Only say what something is NOT when players would reasonably assume it. Keep production_notes outside customer-facing prose.

## Inputs: exact selectors

- `brief`: `map_needs`
- `world`: `background`, `visual_style`
- `story`: `entity_registry`, `chapters`
- `npcs`: `npcs.*.id`, `npcs.*.name`, `npcs.*.occupation`, `npcs.*.secret`
- `clues`: `clue_web`

Only the declared creator spec fields and named prerequisite keys in `skill.json` are supplied. Missing inputs fail explicitly. Oversized context is not silently truncated.

## Output contract

Return the exact shape in `output.schema.json`. The schema is executable and authoritative; do not rename its top-level fields. Local validation is mandatory for every provider; native JSON-schema output is used only when explicitly configured. Bad JSON/schema replies receive bounded correction attempts with the actual rejected reply and error. Valid raw responses are saved before modification.

Owns: `locations`. Execution: `ai` / `locations`.

## Verification and failure behavior

A successful call is not publication approval. Post-skill checks feed the repair controller; unrepairable/schema failures retain the checkpoint and raw evidence. Audit and repair pointers address canonical state (for example `/npcs/npcs/0/speech_style`), not a PDF page. Protected human values, IDs and unrelated fields may not be overwritten. Upstream changes invalidate affected output and audit hashes.

See `docs/REVIEW_RESPONSE.md` and `docs/ENFORCEMENT_MATRIX.md` for code-vs-prompt boundaries and regression tests. Quality, originality, play balance, art rights and visual proof are not guaranteed by field presence or a pass label.
