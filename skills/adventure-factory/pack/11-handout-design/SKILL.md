---
name: 11-handout-design
description: Player Handouts with enforced v0.11.1 contracts, repair routing and release evidence.
---
# Player Handouts

## Instructions

**Creator control.** Use the creator's approved scope. Ask before introducing a gameplay mechanic or mandatory story structure; an unattended run must omit unapproved additions. Adventure clocks, countdowns, forced deadlines, timed escalation and substitute pressure tracks are excluded from this build. Never add them during generation, audit or repair, or penalize exploration/rest with a timer. Estimated session length, historical dates and ordinary rules durations are not adventure timers.

Create artifacts that characters can actually receive: a letter, notice, damaged ledger, sketch key or practical instruction sheet. Aim for 120–250 words per handout so it fits a legible single-page PDF; use 40–100 for a terse notice or clue scrap. Keep the title short. The author, age, condition and visual style should support the artifact's purpose rather than turn every page into identical aged parchment.

Write in the author's voice and for the author's original audience. A payroll list uses amounts and dates; a private letter assumes shared history; a repair notice gives a sequence and a warning. Reveal information through those purposes. Preserve the exact names, mechanism, sequence and clues in the canonical material. A character may be mistaken, but the GM-facing purpose should identify the intended misunderstanding and where it can be corrected.

Include enough context to interpret the clue without requiring a particular player's real-world expertise. A damaged passage can conceal optional flavor while the actionable clue remains legible. The same essential fact must still have a backup source in the clue network. A puzzle handout must show all necessary symbols or describe them precisely; decorative omissions should never remove the solution. Preserve player_safe as an honest audience choice and place all explanatory GM notes in purpose or production_notes, outside the printed artifact content.

Design for the actual page. Use short paragraphs, a modest heading, and a clear hierarchy between date, recipient, body and signature. Letter style suits personal correspondence; parchment style suits a notice or archival fragment. The export uses readable typeset text rather than simulated illegible handwriting. A list of figures should be grouped into compact lines. Shorten bloated prose while preserving every actionable detail before it reaches the one-page renderer.

Failure modes: GM explanation in a player's letter; Contradicting canonical facts; Decorative illegibility; Missing puzzle information; Identical author voices.

Bad: “This handout tells the players that the mayor secretly locked the gate and they should investigate the mill.”
Good: “Millkeeper—keep the relief wheel chained until the disputed ownership entry is corrected. Leave its key with my clerk, not the storehouse guard. The upper gauge marks the safe waterline. I will settle the flour account when you return the signed ledger. —Reeve Saren.” The recipient, instruction and debt reveal pressure without narrating a quest.

Return the artifact's exact text alongside its GM purpose and clue references. Those are distinct audiences even though they share one source record.

State what is true. Only say what something is NOT when players would reasonably assume it. Keep production_notes outside customer-facing prose.

## Inputs: exact selectors

- `brief`: `tone`
- `story`: `entity_registry`
- `clues`: `clue_web`
- `npcs`: `npcs.*.id`, `npcs.*.name`, `npcs.*.speech_style`
- `items`: `items.*.id`, `items.*.name`

Only the declared creator spec fields and named prerequisite keys in `skill.json` are supplied. Missing inputs fail explicitly. Oversized context is not silently truncated.

## Output contract

Return the exact shape in `output.schema.json`. The schema is executable and authoritative; do not rename its top-level fields. Local validation is mandatory for every provider; native JSON-schema output is used only when explicitly configured. Bad JSON/schema replies receive bounded correction attempts with the actual rejected reply and error. Valid raw responses are saved before modification.

Owns: `handouts`. Execution: `ai` / `handouts`.

## Verification and failure behavior

A successful call is not publication approval. Post-skill checks feed the repair controller; unrepairable/schema failures retain the checkpoint and raw evidence. Audit and repair pointers address canonical state (for example `/npcs/npcs/0/speech_style`), not a PDF page. Protected human values, IDs and unrelated fields may not be overwritten. Upstream changes invalidate affected output and audit hashes.

See `docs/REVIEW_RESPONSE.md` and `docs/ENFORCEMENT_MATRIX.md` for code-vs-prompt boundaries and regression tests. Quality, originality, play balance, art rights and visual proof are not guaranteed by field presence or a pass label.
