---
name: 17b-audit-repair
description: Apply targeted owner repairs and editorial patches, then re-audit before rendering.
---
# Audit-Repair Controller

## Instructions

**Creator control.** Use the creator's approved scope. Ask before introducing a gameplay mechanic or mandatory story structure; an unattended run must omit unapproved additions. Adventure clocks, countdowns, forced deadlines, timed escalation and substitute pressure tracks are excluded from this build. Never add them during generation, audit or repair, or penalize exploration/rest with a timer. Estimated session length, historical dates and ordinary rules durations are not adventure timers.
Run `adventure_factory.repairs.repair_cycle`. Do not ask a general-purpose model to rewrite the full book.
Use each blocking finding's JSON Pointer to resolve its owning skill. Re-ask only that skill for exact-field patches with `before` and `value`. Validate the patch response against a per-field schema. Validate the entire owner output after applying it to a temporary copy. Commit only if IDs, unrelated domains and human locks remain unchanged.
Apply Editorial Polish patches to unlocked draft text, record before/after values, and re-check all five audits against the resulting content hash. Audits are sectioned (0.11.3): a re-check re-audits every section pass whose fingerprinted input changed, the cross-section pass when its index changed, and any pass whose own finding points at a changed path; it reuses only passes whose fingerprint proves unchanged input, and records which in `repair_control.audit_passes`. A failing verdict blocks even if findings is empty. Non-repairable errors, human-locked conflicts and remaining issues block release. Stop after at most three repair cycles; do not silently drop findings, weaken policy or relabel failures as warnings.
Plot-spine contradictions from the continuity audit are repaired in the chapter that disagrees, never by changing the spine to match it, unless the creator changes the spine. Re-check only the sections the patch changed.
On resume, rerun stale audits before using their findings. Save after each successful owner repair and audit, not just after the whole batch. Fixture-provider replies are not evidence of writing quality.

## Incremental audits (0.11.3, host behaviour)

`repair_cycle` calls `audit_sections.run_audit` for every re-check. Reused passes keep their original raw response and hash; failing passes are reused too, so an unchanged blocking finding never self-clears by being asked again. `repair_control.audit_passes` lists, per round and audit, the passes re-audited and the passes reused. `QA/audit-sections.json` holds the latest status of every pass and `SOURCE/audit-section-history.jsonl` every check. See `docs/AUDIT_EFFICIENCY_CHANGELOG.md`.

