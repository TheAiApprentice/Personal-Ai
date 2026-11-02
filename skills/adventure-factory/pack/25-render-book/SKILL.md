---
name: 25-render-book
description: Render Book with enforced v0.11.1 contracts, repair routing and release evidence.
---
# Render Book

## Instructions

**Creator control.** Use the creator's approved scope. Ask before introducing a gameplay mechanic or mandatory story structure; an unattended run must omit unapproved additions. Adventure clocks, countdowns, forced deadlines, timed escalation and substitute pressure tracks are excluded from this build. Never add them during generation, audit or repair, or penalize exploration/rest with a timer. Estimated session length, historical dates and ordinary rules durations are not adventure timers.

Render repaired canonical content, real stat blocks, exact checks/hazards/items, factions, clues, endings and every available keyed map. Use flow-based paragraphs and measured callouts; no opaque boxes at fixed coordinates over prose. Generate contents entries from the actual emitted headings, number all pages and keep endings with aftermath when possible. Print the creator-supplied attribution and credits verbatim as text. A layout fixture must visibly say it is a demo and is therefore not a customer release. Extract all PDF text for automated checks, then require human visual proof; text extraction alone cannot prove layout correctness.

## Inputs: exact selectors

No AI input context; this is a deterministic host step.

Only the declared creator spec fields and named prerequisite keys in `skill.json` are supplied. Missing inputs fail explicitly. Oversized context is not silently truncated.

## Output contract

Return the exact shape in `output.schema.json`. The schema is executable and authoritative; do not rename its top-level fields. Local validation is mandatory for every provider; native JSON-schema output is used only when explicitly configured. Bad JSON/schema replies receive bounded correction attempts with the actual rejected reply and error. Valid raw responses are saved before modification.

Owns: `book_files`. Execution: `builtin` / `render_book`.

## Where art goes (0.11.2)

Generated art is placed only from valid `ART/manifest.json` slots: the file exists, its SHA-256 matches, and the model and provider are recorded. Commissioned and licensed-stock plans keep their supplied-cover path unchanged.

- **Cover:** the painting gets the title set over its `title_space` and becomes `COVER/Cover.png` and a full-bleed first page with no running head or folio.
- **Chapter openers:** full column width, up to half a page, directly under each chapter title.
- **Locations:** full column width under the location name, before its history.
- **NPCs:** portrait at the right of the dossier; the entry's text flows around it.
- **Creatures:** illustration at the right of the description and lore, in the space the one-entry-per-page layout leaves; the stat block runs full width beneath.
- **Items (optional):** small illustration at the right of the item entry.

A slot without valid art keeps the plain layout: no frame, placeholder or caption. Images are embedded as JPEG copies at no more than 300 dpi at their placed size, scaled to fit, never stretched; `QA/book-art.json` records each placement and its effective dpi. Book Fixer and release QA check every image in the actual PDF against a manifest slot, a keyed map or the recorded cover.

## Stat blocks (0.11.2)

A creature with a numeric `stat_block` is printed as a tinted box with heavy top and bottom rules in the book's own teal palette and standard fonts: name in small capitals, size/type (and alignment if the data has one) in italics, then armor class, hit points (with hit dice), speed (zero speeds omitted), the six ability scores with modifiers, saving throws, skills, senses, languages, challenge with the proficiency bonus from the standard CR table, traits, then Actions, Bonus Actions, Reactions and Legendary Actions headings. Only fields present in the canonical data print; empty sections are omitted and no number is invented. A combat-capable NPC gets one "Statistics" line pointing to its Bestiary entry rather than a second copy of the block. Creatures without a stat block keep the system-neutral profile lines. Reference cards are unchanged.

## Verification and failure behavior

A successful call is not publication approval. Post-skill checks feed the repair controller; unrepairable/schema failures retain the checkpoint and raw evidence. Audit and repair pointers address canonical state (for example `/npcs/npcs/0/speech_style`), not a PDF page. Protected human values, IDs and unrelated fields may not be overwritten. Upstream changes invalidate affected output and audit hashes.

See `docs/REVIEW_RESPONSE.md` and `docs/ENFORCEMENT_MATRIX.md` for code-vs-prompt boundaries and regression tests. Quality, originality, play balance, art rights and visual proof are not guaranteed by field presence or a pass label.
