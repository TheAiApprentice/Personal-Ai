---
name: 00-project-intake
description: Project Intake with enforced v0.11.1 contracts, repair routing and release evidence.
---
# Project Intake

## Instructions

**Creator control.** Use the creator's approved scope. Ask before introducing a gameplay mechanic or mandatory story structure; an unattended run must omit unapproved additions. Adventure clocks, countdowns, forced deadlines, timed escalation and substitute pressure tracks are excluded from this build. Never add them during generation, audit or repair, or penalize exploration/rest with a timer. Estimated session length, historical dates and ordinary rules durations are not adventure timers.

Translate the creator's request into an explicit brief without generating the adventure itself. Preserve the selected rules_profile; do not relabel a 5e request as system-neutral to evade checks. Scope estimated session length, tone, boundaries, target deliverables and map needs. Set minimum_clue_routes explicitly. A duration is an estimate to reconcile with chapter times, not an unsupported sales claim. Credits, permissions, attribution verification and disclosure approval belong to creator-supplied release metadata: never invent them.

State what is true. Only say what something is NOT when players would reasonably assume it. Keep production_notes outside customer-facing prose.

Preserve creator.rules_specific and creator.combat_intensity exactly. Treat market_pulse as cited observations and hypotheses, not sales forecasts; preserve the creator's explicit concept. Plan within entity_counts. Unverified signals stay unverified.

## Inputs: exact selectors

No AI input context; this is a deterministic host step.

Only the declared creator spec fields and named prerequisite keys in `skill.json` are supplied. Missing inputs fail explicitly. Oversized context is not silently truncated.

## Output contract

Return the exact shape in `output.schema.json`. The schema is executable and authoritative; do not rename its top-level fields. Local validation is mandatory for every provider; native JSON-schema output is used only when explicitly configured. Bad JSON/schema replies receive bounded correction attempts with the actual rejected reply and error. Valid raw responses are saved before modification.

Owns: `brief`. Execution: `ai` / `intake`.

## Verification and failure behavior

A successful call is not publication approval. Post-skill checks feed the repair controller; unrepairable/schema failures retain the checkpoint and raw evidence. Audit and repair pointers address canonical state (for example `/npcs/npcs/0/speech_style`), not a PDF page. Protected human values, IDs and unrelated fields may not be overwritten. Upstream changes invalidate affected output and audit hashes.

See `docs/REVIEW_RESPONSE.md` and `docs/ENFORCEMENT_MATRIX.md` for code-vs-prompt boundaries and regression tests. Quality, originality, play balance, art rights and visual proof are not guaranteed by field presence or a pass label.
