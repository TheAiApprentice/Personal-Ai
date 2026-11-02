---
name: 29-final-qa
description: Final QA with enforced v0.11.1 contracts, repair routing and release evidence.
---
# Final QA

## Instructions

**Creator control.** Use the creator's approved scope. Ask before introducing a gameplay mechanic or mandatory story structure; an unattended run must omit unapproved additions. Adventure clocks, countdowns, forced deadlines, timed escalation and substitute pressure tracks are excluded from this build. Never add them during generation, audit or repair, or penalize exploration/rest with a timer. Estimated session length, historical dates and ordinary rules durations are not adventure timers.

Run code checks, not another opinion-only prompt: validate skill schemas and canonical projection, all NPC narrative-template comparisons, numeric mechanics/profile rules, explicit check/hazard arrays, registered references and clue routes; verify per-location PNG metadata; extract PDF/HTML/text and scan visible markup and internal text; inspect actual inventories and claims; reject placeholder metadata and missing image rights records. Read every required audit verdict and current content hash, including editorial outcomes. Reject stale render/asset hashes, missing raw-response provenance, all fixture runs and stale/missing human approval. Fail closed on unreadable/encrypted PDFs. No AI verdict overrides deterministic findings. Human proofing and legal/rights review remain necessary.

## Inputs: exact selectors

No AI input context; this is a deterministic host step.

Only the declared creator spec fields and named prerequisite keys in `skill.json` are supplied. Missing inputs fail explicitly. Oversized context is not silently truncated.

## Output contract

Return the exact shape in `output.schema.json`. The schema is executable and authoritative; do not rename its top-level fields. Local validation is mandatory for every provider; native JSON-schema output is used only when explicitly configured. Bad JSON/schema replies receive bounded correction attempts with the actual rejected reply and error. Valid raw responses are saved before modification.

Owns: `qa`. Execution: `builtin` / `final_qa`.

## Verification and failure behavior

A successful call is not publication approval. Post-skill checks feed the repair controller; unrepairable/schema failures retain the checkpoint and raw evidence. Audit and repair pointers address canonical state (for example `/npcs/npcs/0/speech_style`), not a PDF page. Protected human values, IDs and unrelated fields may not be overwritten. Upstream changes invalidate affected output and audit hashes.

See `docs/REVIEW_RESPONSE.md` and `docs/ENFORCEMENT_MATRIX.md` for code-vs-prompt boundaries and regression tests. Quality, originality, play balance, art rights and visual proof are not guaranteed by field presence or a pass label.
