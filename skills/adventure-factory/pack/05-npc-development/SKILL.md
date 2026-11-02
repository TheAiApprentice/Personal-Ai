---
name: 05-npc-development
description: NPC Development with enforced v0.11.1 contracts, repair routing and release evidence.
---
# NPC Development

## Instructions

**Creator control.** Use the creator's approved scope. Ask before introducing a gameplay mechanic or mandatory story structure; an unattended run must omit unapproved additions. Adventure clocks, countdowns, forced deadlines, timed escalation and substitute pressure tracks are excluded from this build. Never add them during generation, audit or repair, or penalize exploration/rest with a timer. Estimated session length, historical dates and ordinary rules durations are not adventure timers.

Develop exactly the registry character in this request. Preserve their identity and relationships while giving them a distinctive way to act. Aim for 450–650 words in the full source dossier, with a useful first impression of 25–50 words. The GM should be able to portray this person after reading their role, voice, current want and two lines of dialogue. Avoid repeating the signatures of previously written characters supplied with the request.

This entry is the one canonical description of the NPC: appearance, voice, want and secret are written here and nowhere else. Scenes, locations, encounters and handouts refer to the NPC as "see NPC: name, page X" instead of describing them again.

Start from occupation, loyalties and pressure. Choose one memorable physical detail that follows from lived experience: an ink-black thumbnail, carefully mended cuffs, or a polished hinge on an artificial jaw. Match clothing and habits to anatomy, circumstances and resources. Write a specific formative event and a recent choice that explain the current goal. State the secret as a fact already true, not an action the NPC might perform. Separate what they know, what they suspect, and what they confidently misunderstand.

Make voice audible through sentence length, preferred images and conversational strategy. One character asks questions to buy time; another bargains in quantities; a third answers slowly while searching for a lost memory. Write at least two dialogue lines that could not plausibly be exchanged with another cast member. A construct with failing recall might interrupt itself at a particular name; a clerk may reach for dates when frightened. Let voice reveal a motive rather than become an accent caricature.

Give specific leverage and a moral boundary. Friendly conversation, intimidation, bribery, deception, violence, rescue and betrayal should produce different, believable reactions. Choose exactly four reaction keys most relevant to the adventure for print_reactions; preserve the whole reaction set in the source. A failed approach can change the price or available assistance while essential information retains its backup route. The NPC's if-ignored entry describes their current independent activity and attitude toward the party. It must not schedule deterioration or punish the party's absence.

Failure modes: Same voice in different coats; Secret without consequences; Biographical padding; Universal cooperation; Species-inconsistent appearance. Revise the underlying choice or behavior instead of swapping adjectives.

Bad: “She is nervous but capable and will help if the party earns her trust.”
Good: “Odo counts the remaining ferry pegs while visitors speak. ‘Names first. Promises take no space in a boat.’ Showing him a working float wins two seats; threatening him makes him refuse use of his boat.” The action, line and reaction arise from his duty.

State what is true. Only say what something is NOT when players would reasonably assume it. Keep production_notes outside customer-facing prose.

## Inputs: exact selectors

- `brief`: `tone`, `level_band`
- `world`: `summary`, `visual_style`
- `factions`: `factions`
- `story`: `entity_registry`
- `clues`: `clue_web`, `critical_revelations`

Only the declared creator spec fields and named prerequisite keys in `skill.json` are supplied. Missing inputs fail explicitly. Oversized context is not silently truncated.

## Output contract

Return the exact shape in `output.schema.json`. The schema is executable and authoritative; do not rename its top-level fields. Local validation is mandatory for every provider; native JSON-schema output is used only when explicitly configured. Bad JSON/schema replies receive bounded correction attempts with the actual rejected reply and error. Valid raw responses are saved before modification.

Owns: `npcs`. Execution: `ai` / `npcs`.

## Verification and failure behavior

A successful call is not publication approval. Post-skill checks feed the repair controller; unrepairable/schema failures retain the checkpoint and raw evidence. Audit and repair pointers address canonical state (for example `/npcs/npcs/0/speech_style`), not a PDF page. Protected human values, IDs and unrelated fields may not be overwritten. Upstream changes invalidate affected output and audit hashes.

See `docs/REVIEW_RESPONSE.md` and `docs/ENFORCEMENT_MATRIX.md` for code-vs-prompt boundaries and regression tests. Quality, originality, play balance, art rights and visual proof are not guaranteed by field presence or a pass label.
