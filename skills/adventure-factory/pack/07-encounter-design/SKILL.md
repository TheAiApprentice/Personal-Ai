---
name: 07-encounter-design
description: Encounter Design with enforced v0.11.1 contracts, repair routing and release evidence.
---
# Encounter Design

## Instructions

**Creator control.** Use the creator's approved scope. Ask before introducing a gameplay mechanic or mandatory story structure; an unattended run must omit unapproved additions. Adventure clocks, countdowns, forced deadlines, timed escalation and substitute pressure tracks are excluded from this build. Never add them during generation, audit or repair, or penalize exploration/rest with a timer. Estimated session length, historical dates and ordinary rules durations are not adventure timers.

Write exactly the registry encounter in this request. Aim for 450–750 useful words covering setup, objectives, participants, terrain, tactics, changes, alternatives, outcomes and rewards. The first encounter request also supplies the adventure's numbered random-event and rumor tables. Each table names its die size, gives complete roll coverage and marks rumor reliability for the GM. Later encounter requests return only their assigned encounter.

Give the scene a dramatic question and an objective other than consuming hit points. Explain what each side wants, why it acts now, and how it responds to withdrawal or negotiation. Combatants need creature references and exact counts. Use the creator's combat_intensity selection, and give weaker/stronger scaling that adjusts the same encounter rather than introducing a new unexplained monster. Describe tactics and reactions tied to character actions or observable conditions. Reinforcements respond to an actual alarm or request for help; environmental consequences follow the defined interaction.

Make terrain tactical. Identify cover, routes, exposed squares, elevation, machinery and exits in terms the map planner can place. Every mechanical interaction has a check or hazard entry with a clear trigger, method, numerical DC, effect, duration and countermeasure where appropriate. Quote those entries through references instead of rewriting inconsistent rules in prose. Use a short GM Quick Run sequence the GM can follow under pressure.

Keep core clues automatic. Separate finding the answer from paying to act on it. Across the adventure, include two or three meaningful checks with a stated cost to a resource, position, relationship or ending. In failure_cost identify the exact target, amount and effect. Tell players the stake before they roll. Avoid repeated retries that erase the cost, and let failure still lead to playable consequences.

Provide at least two plausible alternative approaches and explain their outcomes. Failure and retreat should leave a changed situation and a route forward, not restart the encounter. Put actual amounts and item references in rewards. When a mob matters, give it a clear objective, a named spokesperson and actionable ways to intervene. It responds to what the characters do, not an automatic fuse, round limit or escalating track.

Failure modes: Empty difficulty label; Damage-only purpose; Terrain invisible on the map; Cost-free repeated checks; Failure resets the scene.

Bad: “Failure delays the characters briefly. The crowd attacks.”
Good: “Nera locks the gate when the party attempts to seize her cart. A DC 13 Athletics check reaches the cart from the wet ledge. Failure tears one rescue rope and leaves the climber on the lower landing, where they can climb back. Presenting the gate ledger persuades Nera to unlock the gate and discuss ownership.”

State what is true. Only say what something is NOT when players would reasonably assume it. Keep production_notes outside customer-facing prose.

## Inputs: exact selectors

- `brief`: `rules_profile`, `level_band`, `party_size`
- `story`: `chapters`, `entity_registry`
- `npcs`: `npcs.*.id`, `npcs.*.name`, `npcs.*.combat_capable`, `npcs.*.creature_ref`
- `locations`: `locations.*.id`, `locations.*.name`, `locations.*.rooms`
- `clues`: `clue_web`

Only the declared creator spec fields and named prerequisite keys in `skill.json` are supplied. Missing inputs fail explicitly. Oversized context is not silently truncated.

## Output contract

Return the exact shape in `output.schema.json`. The schema is executable and authoritative; do not rename its top-level fields. Local validation is mandatory for every provider; native JSON-schema output is used only when explicitly configured. Bad JSON/schema replies receive bounded correction attempts with the actual rejected reply and error. Valid raw responses are saved before modification.

Owns: `encounters`. Execution: `ai` / `encounters`.

## Verification and failure behavior

A successful call is not publication approval. Post-skill checks feed the repair controller; unrepairable/schema failures retain the checkpoint and raw evidence. Audit and repair pointers address canonical state (for example `/npcs/npcs/0/speech_style`), not a PDF page. Protected human values, IDs and unrelated fields may not be overwritten. Upstream changes invalidate affected output and audit hashes.

See `docs/REVIEW_RESPONSE.md` and `docs/ENFORCEMENT_MATRIX.md` for code-vs-prompt boundaries and regression tests. Quality, originality, play balance, art rights and visual proof are not guaranteed by field presence or a pass label.
