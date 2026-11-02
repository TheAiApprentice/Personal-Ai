---
name: 03-story-architecture
description: Story Architecture with enforced v0.11.1 contracts, repair routing and release evidence.
---
# Story Architecture

## Instructions

**Creator control.** Use the creator's approved scope. Ask before introducing a gameplay mechanic or mandatory story structure; an unattended run must omit unapproved additions. Adventure clocks, countdowns, forced deadlines, timed escalation and substitute pressure tracks are excluded from this build. Never add them during generation, audit or repair, or penalize exploration/rest with a timer. Estimated session length, historical dates and ordinary rules durations are not adventure timers.

Build a playable sequence of choices, not a synopsis of a novel. Aim for three substantial chapters for a six-hour adventure; follow the actual requested duration for other briefs. Each chapter needs a purpose, a clear starting situation, a few scenes and a change that carries play forward. Give approximate chapter play lengths whose total matches the brief. These are session-planning estimates, never limits on player exploration or in-world deadlines. Describe an opening situation and let player choices determine what follows; exploration and rest do not advance an automatic threat.

**Plot spine first (before any chapter).** Write one page, 300–500 words, titled "What is really going on". It states the truth once, in plain words a first-time GM can repeat after one reading: what the central creature or threat is; why whatever holds it (seals, pillars, a bargain) holds it, with the exact count, builder and what breaks the hold; who wants it changed and why; what that plan achieves if the party never acts, written as an outcome and never as a schedule, countdown or timed escalation; and the two or three ways the adventure can end. Names, counts and conditions fixed here are never restated differently anywhere else; later skills and chapters say "see What is really going on" and point at it. The book's GM section opens with this page. Home: the required `story.plot_spine` string; the host prints it as the first page of the GM section, and Clue Network, Continuity Audit and GM Usability Audit receive it.

**Chapter box.** Each chapter's `purpose` is a short opening box of four labelled lines: "Purpose" (one sentence, true to the spine), "Learn" (what the party should learn), "Ends" (the two or three ways the chapter can end) and "Leads to" (the next chapter or ending by name). The box adds no read-aloud text and does not replace `opening`. Every chapter box must agree with the spine and with `endings`.

Create the entity registry before expansion. Include every planned NPC, location, faction, creature, item and encounter with a stable ID and an original name; stay within the creator's entity-count ceilings. Scene references must use these entries. Seed optional material where it can be skipped without erasing essential information. Write 40–90 words of observable arrival text for important scenes, then concise GM-only explanation of what matters and what changes.

Keep core discoveries automatic when characters examine the right evidence. Give every critical revelation an independent backup. Distinguish information from advantage: a check can secure help, preserve a resource or change an outcome while the clue remains available. Plan two or three consequential checks across different scenes. State the visible stake before rolling: a failed crossing may leave a character on a lower ledge, damage a rope or forfeit an offered reward. Use consequences of the action itself, not elapsed-time penalties or a replacement progress track.

Shape the middle around a decision that changes the interpretation of the opening. Give the finale a location, participants, an objective beyond killing, and routes for confrontation, negotiation or withdrawal. Define three endings through requirements and aftermath, including how earlier costs affect them. The selected combat intensity governs the number and pressure of fights; a low-combat investigation should remain interesting through exploration and conflicting interests.

Failure modes: Predetermined revelation tells the players the answer; Single-door plotting requires one NPC; Consequence-free failure erases meaningful costs; Ending buttons ignore prior choices; Scope creep invents unplanned actors at the climax. Address them in scenes and references rather than disclaimers.

Bad: “If the party fails the check, they spend ten minutes and try again.”
Good: “The pilot reveals the overflow route as soon as the party shows the gauge. A DC 14 repair keeps her skiff afloat; failure uses its only spare float, leaving two fewer evacuation seats in the finale.” Information continues while the roll changes the situation.

State what is true. Only say what something is NOT when players would reasonably assume it. Keep production_notes outside customer-facing prose.

## Inputs: exact selectors

- `brief`: `premise`, `level_band`, `play_time_hours`, `product_size`
- `world`: `summary`, `background`, `hooks`, `secrets`
- `factions`: `factions`

Only the declared creator spec fields and named prerequisite keys in `skill.json` are supplied. Missing inputs fail explicitly. Oversized context is not silently truncated.

## Output contract

Return the exact shape in `output.schema.json`. The schema is executable and authoritative; do not rename its top-level fields. Local validation is mandatory for every provider; native JSON-schema output is used only when explicitly configured. Bad JSON/schema replies receive bounded correction attempts with the actual rejected reply and error. Valid raw responses are saved before modification.

Owns: `story`. Execution: `ai` / `story`.

## Verification and failure behavior

A successful call is not publication approval. Post-skill checks feed the repair controller; unrepairable/schema failures retain the checkpoint and raw evidence. Audit and repair pointers address canonical state (for example `/npcs/npcs/0/speech_style`), not a PDF page. Protected human values, IDs and unrelated fields may not be overwritten. Upstream changes invalidate affected output and audit hashes.

See `docs/REVIEW_RESPONSE.md` and `docs/ENFORCEMENT_MATRIX.md` for code-vs-prompt boundaries and regression tests. Quality, originality, play balance, art rights and visual proof are not guaranteed by field presence or a pass label.
