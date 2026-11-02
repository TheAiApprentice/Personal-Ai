---
name: adventure-factory
description: Turn a creator's brief into a complete, playable tabletop adventure book (world, factions, story, clues, NPCs, locations, encounters, creatures, treasure, maps, handouts, art direction, audits, book, cards, store copy and a release package) through a fixed chain of 35 skills run by a master. Use when the owner wants to make a D&D-style adventure or campaign book.
---

# Adventure Factory

A skill pack for making a tabletop adventure book from a brief. The 36 skills (35 stages plus a master) are in [`pack/`](pack/);
[`pack/README.md`](pack/README.md) lists them in the order they run. Each stage has a `SKILL.md` (its instructions), a `skill.json`
(its inputs, outputs and limits) and an `output.schema.json` (the exact shape its output must have).

The pack is written for the Adventure Factory application, which runs the stages, validates every output against its schema and does the
code checks. That application is not in this repo; the skills here show the whole method and can be read or adapted on their own.

## How a run goes

The master skill ([`pack/adventure-factory-master/SKILL.md`](pack/adventure-factory-master/SKILL.md)) is the source of truth. In short:

1. **Creator control.** Use only the creator's approved scope. Ask before adding a game mechanic or a required story structure; an unattended
   run leaves unapproved additions out. Adventure clocks, countdowns, forced deadlines and timed escalation are not used.
2. **Preflight.** Check the creator's rules choice and the size of the job before any model call. Market Pulse (optional, opt-in) runs before intake.
3. **Write the adventure.** Intake, world, factions, story (with a required plot spine), clue network, then NPCs, locations and encounters one entry
   at a time, then creatures, treasure, maps, handouts and art direction. Stable IDs are kept throughout.
4. **Audit and repair.** Mechanics, continuity and GM-usability audits, editorial polish (applied once), marketing, Kickstarter and storefront copy,
   then the commercial and IP review. Blocking findings are fixed by small checked patches from the skill that owns the field, and re-audited.
5. **Build.** Assemble the canonical project, render maps, cards, handouts and the book, optional Foundry VTT export, Book Fixer on the real customer text,
   commercial export, manufacturing handoff and the creator's tweak workspace.
6. **Final QA and release.** Rescan all public copy and files. A source package can be delivered while the customer release stays blocked.
   The creator approves publication of the exact reviewed version.

## Honesty rules (from the master)

- Report exactly which stages ran, were cached, were skipped, failed or still need outside checks.
- No simulated model call, legal approval, copyright right, paid research, Foundry import or playtest is presented as real.
- Missing token counts are unknown, not zero. An audit run on the same model as the writer gets a visible warning.
