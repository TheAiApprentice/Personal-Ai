---
name: 25b-book-fixer
description: Book Fixer / Customer Proof for Adventure Factory v0.11.
---
# Book Fixer / Customer Proof

## Instructions

**Creator control.** Use the creator's approved scope. Ask before introducing a gameplay mechanic or mandatory story structure; an unattended run must omit unapproved additions. Adventure clocks, countdowns, forced deadlines, timed escalation and substitute pressure tracks are excluded from this build. Never add them during generation, audit or repair, or penalize exploration/rest with a timer. Estimated session length, historical dates and ordinary rules durations are not adventure timers.

Inspect actual customer PDF text and associated human-facing files after rendering. Enforce P0 isolation, approved-disclosure matching, defined check/hazard/encounter references, English field labels and size/type output. Run the repeat scan on the customer text: a description or fact written twice is a warning finding (`repeated_text`) naming the canonical entry and the repeats; Editorial Polish patches each repeat to "see NPC: name, page X" or "see section X" in the canonical source, and the fixer never edits prose itself. Deterministic repairs use the canonical customer projection and rerender the source; never white-out errors in a PDF or guess missing mechanics. Preserve canonical human locks, review metadata and the hash-bound release gate. Produce before/after artifact hashes, the fixes applied, blocking findings and low-occupancy warnings. End with a buyer-notice checklist requiring human visual review; a automated pass is not a claim of completed human proofreading.

## Host contract

This built-in stage is executed by the application, not by a model pretending to have performed it. See skill.json and output.schema.json. Retain actual evidence; creator decisions are never fabricated.
