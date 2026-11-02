# Adventure Factory skill pack (0.11.3)

35 production skills plus one master. Each production skill has `SKILL.md`, `skill.json` and `output.schema.json`.
They are written to be run by the Adventure Factory application, which feeds each skill its declared inputs, checks its output
against `output.schema.json` and runs the code checks the skills mention. The application code is not part of this repo, so the
skills here show the method; on their own they do not enforce the checks. Mentions of `docs/...`, module names and project files
such as `QA/audit-sections.json` refer to that application.

Execution order is read from `adventure-factory-master/skill.json`, not inferred by sorting directory names. Commercial review keeps its stable ID but runs after storefront output.

1. **pre-market-pulse** — Market Pulse (builtin; output `market_pulse`)
2. **00-project-intake** — Project Intake (ai; output `brief`)
3. **01-world-bible** — World Bible (ai; output `world`)
4. **02-faction-design** — Faction Design (ai; output `factions`)
5. **03-story-architecture** — Story Architecture (ai; output `story`)
6. **04-clue-network** — Clue Network (ai; output `clues`)
7. **05-npc-development** — NPC Development (ai; output `npcs`)
8. **06-location-development** — Location Development (ai; output `locations`)
9. **07-encounter-design** — Encounter Design (ai; output `encounters`)
10. **08-creature-bestiary** — Creature Bestiary (ai; output `creatures`)
11. **09-item-treasure-design** — Item & Treasure Design (ai; output `items`)
12. **10-map-planning** — Map Planning (ai; output `maps`)
13. **11-handout-design** — Player Handouts (ai; output `handouts`)
14. **12-art-direction** — Art Direction (ai; output `art_direction`)
15. **13-mechanics-balance** — Mechanics Balance (ai; output `mechanics_audit`)
16. **14-continuity-audit** — Continuity Audit (ai; output `continuity_audit`)
17. **15-gm-usability-audit** — GM Usability Audit (ai; output `gm_audit`)
18. **17-editorial-polish** — Editorial Polish (ai; output `polish`)
19. **18-marketing-copy** — Marketing Copy (ai; output `marketing`)
20. **19-kickstarter-package** — Kickstarter Package (ai; output `kickstarter`)
21. **20-storefront-package** — Storefront Package (ai; output `storefront`)
22. **16-commercial-ip-review** — Commercial & IP Review (ai; output `commercial_audit`)
23. **17b-audit-repair** — Audit-Repair Controller (builtin; output `repair_control`)
24. **21-assemble-canonical-project** — Assemble Canonical Project (builtin; output `project`)
25. **22-render-maps** — Render Maps (builtin; output `map_files`)
26. **23-render-cards** — Render Cards (builtin; output `card_files`)
27. **24-render-handouts** — Render Handouts (builtin; output `handout_files`)
28. **24b-foundry-export** — Foundry VTT Export (builtin; output `foundry_files`)
29. **25-render-book** — Render Book (builtin; output `book_files`)
30. **25b-book-fixer** — Book Fixer / Customer Proof (builtin; output `book_proof`)
31. **26-commercial-export** — Commercial Asset Export (builtin; output `commercial_files`)
32. **27-manufacturing-handoff** — Manufacturing Handoff (builtin; output `manufacturing_files`)
33. **28-tweak-workspace** — Creator Tweak Workspace (builtin; output `tweak_files`)
34. **29-final-qa** — Final QA (builtin; output `qa`)
35. **30-package-release** — Package Release (builtin; output `release_zip`)

**adventure-factory-master** dispatches the chain, including optional Market Pulse, per-entity generation, Book Fixer and Foundry export. Disabled optional stages report skipped/unavailable instead of pretending their work occurred.

"ai" skills are model-written stages; "builtin" skills are done by the application's own code, and their `SKILL.md` says what that code must do.
Only the `Instructions` section of an ai skill is sent to the model as task guidance; its contracts and selected context go with it.
