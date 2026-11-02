---
name: 01-world-bible
description: World Bible with enforced v0.11.1 contracts, repair routing and release evidence.
---
# World Bible

## Instructions

**Creator control.** Use the creator's approved scope. Ask before introducing a gameplay mechanic or mandatory story structure; an unattended run must omit unapproved additions. Adventure clocks, countdowns, forced deadlines, timed escalation and substitute pressure tracks are excluded from this build. Never add them during generation, audit or repair, or penalize exploration/rest with a timer. Estimated session length, historical dates and ordinary rules durations are not adventure timers.

Build a place whose history creates decisions at the table. Use the approved premise, audience, content boundaries and entity plan. Aim for 800–1,200 words across the world output; spend most of them on present tensions, useful secrets and decisions rather than a chronology. Give the setting one distinctive material, one social custom and one practical dependency. Show how each affects food, travel, authority or shelter. Tie at least two hooks to named people and immediate stakes; explain what those people offer and what they risk.

Write the background as causes and consequences. Three specific events are more useful than a dozen eras. Separate common belief, local knowledge and the concealed truth so the GM knows who can say what. Every faction should have a reason to keep doing its work even when the party stays away. Describe the current situation and the consequences of specific actions. Passage of time alone must not worsen it, close routes or punish the party for exploring or resting. Let investigation reveal a truth that changes what a sensible solution looks like.

Favor details that can be acted on. A surviving ledger may identify a buyer; an altered burial practice can reveal who feared the river; an unpaid ferryman can refuse passage. Put sensory description in short, concrete images. Use two or three senses and reserve explanations for the GM. Keep arrival/read-aloud passages to 40–90 words, describing observable facts rather than telling players what they feel.

Failure modes: Wallpaper history fills pages but changes nothing; Universal secrecy makes every local evasive; Single-hook dependence assumes one conversation; Unmotivated opposition has no response to character decisions; Borrowed identity substitutes a familiar published setting for an original one. Resolve these through choices, access and consequences rather than extra exposition.

Bad: “This ancient village has a mysterious past and the residents are worried.”
Good: “Every house keeps a brass basin by its door. The bailiff owns the ferry and demands water for its bearings as payment for passage. Three families dispute that demand and ask the party to inspect his accounts.” The custom reveals an existing disagreement and a choice the party can influence.

Preserve the clue backups and the premise's strongest twist. Let world details support those structures. Use the supplied craft references only for high-level organization when the creator has actually supplied them; otherwise work from this original guidance and leave reference selection open.

State what is true. Only say what something is NOT when players would reasonably assume it. Keep production_notes outside customer-facing prose.

## Inputs: exact selectors

- `brief`: `premise`, `themes`, `content_boundaries`, `rules_basis`, `tone`, `visual_direction`

Only the declared creator spec fields and named prerequisite keys in `skill.json` are supplied. Missing inputs fail explicitly. Oversized context is not silently truncated.

## Output contract

Return the exact shape in `output.schema.json`. The schema is executable and authoritative; do not rename its top-level fields. Local validation is mandatory for every provider; native JSON-schema output is used only when explicitly configured. Bad JSON/schema replies receive bounded correction attempts with the actual rejected reply and error. Valid raw responses are saved before modification.

Owns: `world`. Execution: `ai` / `world`.

## Verification and failure behavior

A successful call is not publication approval. Post-skill checks feed the repair controller; unrepairable/schema failures retain the checkpoint and raw evidence. Audit and repair pointers address canonical state (for example `/npcs/npcs/0/speech_style`), not a PDF page. Protected human values, IDs and unrelated fields may not be overwritten. Upstream changes invalidate affected output and audit hashes.

See `docs/REVIEW_RESPONSE.md` and `docs/ENFORCEMENT_MATRIX.md` for code-vs-prompt boundaries and regression tests. Quality, originality, play balance, art rights and visual proof are not guaranteed by field presence or a pass label.
