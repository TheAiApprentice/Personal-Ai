---
name: 16-commercial-ip-review
description: Commercial & IP Review with enforced v0.11.1 contracts, repair routing and release evidence.
---
# Commercial & IP Review

## Instructions

**Creator control.** Use the creator's approved scope. Ask before introducing a gameplay mechanic or mandatory story structure; an unattended run must omit unapproved additions. Adventure clocks, countdowns, forced deadlines, timed escalation and substitute pressure tracks are excluded from this build. Never add them during generation, audit or repair, or penalize exploration/rest with a timer. Estimated session length, historical dates and ordinary rules durations are not adventure timers.

Review the original material and creator-supplied release metadata for unresolved brand/setting names, placeholders, inconsistent compatibility claims, missing exact attribution, credits, AI-use disclosure and rights evidence. Return only verdict/findings; never manufacture release_metadata or legal approval. Metadata issues use a /runtime_spec/release/... pointer and owner_skill human. The expanded term list is a screening list, not an exhaustive SRD exclusion index or legal determination. The creator must verify the selected rules license and current storefront requirements. Code blocks empty/TBD metadata and image records without hashes/evidence/reviewer, but does not authenticate ownership or certify compliance.

Review the FINAL marketing, Kickstarter, storefront, handouts, map labels and art prompts as well as manuscript. Apply the explicit trademark house policy; a match is a release-review finding, not a legal conclusion. Preserve the exact separately reviewed license attribution and AI disclosure. Return owner-specific paths for corrections.

## Inputs: exact selectors

- `brief`: `rules_basis`, `compatibility_label`, `license_basis`
- `world`: `summary`, `background`
- `factions`: `factions.*.name`
- `story`: `chapters`
- `npcs`: `npcs.*.name`, `npcs.*.history`
- `creatures`: `creatures.*.name`, `creatures.*.lore`
- `items`: `items.*.name`, `items.*.history`

Only the declared creator spec fields and named prerequisite keys in `skill.json` are supplied. Missing inputs fail explicitly. Oversized context is not silently truncated.

## Section passes (0.11.3)

`skill.json` `audit_sections` splits this review into one pass per story chapter plus a cross-section pass. A chapter pass reads that chapter's text and the NPC, creature and item names and lore, maps and handouts placed in it. The cross-section pass reads the rules basis, compatibility and license labels, world summary and background, faction names, marketing, Kickstarter, storefront, art direction and the section index. Because it reads the creator `release` metadata, a metadata change re-audits every pass of this review. Entities the host cannot place in a chapter get their own `__unsectioned__` pass. A pass whose fingerprint is unchanged is reused, never re-asked. See `docs/AUDIT_EFFICIENCY_CHANGELOG.md`.

## Output contract

Return the exact shape in `output.schema.json`. The schema is executable and authoritative; do not rename its top-level fields. Local validation is mandatory for every provider; native JSON-schema output is used only when explicitly configured. Bad JSON/schema replies receive bounded correction attempts with the actual rejected reply and error. Valid raw responses are saved before modification.

Owns: `commercial_audit`. Execution: `ai` / `commercial_audit`.

## Verification and failure behavior

A successful call is not publication approval. Post-skill checks feed the repair controller; unrepairable/schema failures retain the checkpoint and raw evidence. Audit and repair pointers address canonical state (for example `/npcs/npcs/0/speech_style`), not a PDF page. Protected human values, IDs and unrelated fields may not be overwritten. Upstream changes invalidate affected output and audit hashes.

See `docs/REVIEW_RESPONSE.md` and `docs/ENFORCEMENT_MATRIX.md` for code-vs-prompt boundaries and regression tests. Quality, originality, play balance, art rights and visual proof are not guaranteed by field presence or a pass label.
