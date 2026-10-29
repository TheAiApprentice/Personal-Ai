---
name: memory
description: The assistant's long-term memory (tools/memory/mem.py, a SQLite database created on first use). Load the brief at the start of every session, save what matters from the owner's chats on your own, log every message in and out, and answer "what do you remember about X" / "forget that". Use whenever the owner says remember, forget, what do you know, or when a durable fact, decision, preference or lesson comes up.
---

# Memory

One continuous identity that outlives whichever model is in the seat. Built to the master brief: layered memory, a
gatekeeper for permanent writes, statuses with provenance, an append-only raw archive. Today it is SQLite; the tables
are shaped like the future PostgreSQL schema, and `export` writes portable JSONL for the move.

All commands: `python tools/memory/mem.py ...` from the repo root. The database is created fresh by the code on first
use (default `data/memory.db`, override with `AI_MEMORY_DB`); no rows are ever shipped. Text goes in with
`--text '...'` or, for anything with quotes/backticks, `--text-file`.

## Every session

1. Start: `mem.py brief`. Read it before answering the owner. It holds who he is, the active projects with their
   intent chains, and recent lessons.
2. Each chat message is logged into the raw archive automatically by the chat client (`mem.py log ...` is for chat that
   did not go through it).
3. Before answering about something you may have discussed before: `mem.py search "<words>"` (add `--project <id>` to
   narrow), or `python tools/memory/recall.py "<words>"` for skills, memories and the owner's past messages together.

## Saving (the owner chose: save on your own, he does not review)

Save a fact once it is durable, not chatter:

- `user`: preferences, how he works, boundaries, goals.
  `mem.py add --layer user --tags <topic> --source chat:<msgid> --text '...'`
- `project`: decisions, status, results, blockers. Use `--project <id>`, and create the project first with an intent
  and a parent so the chain reaches the top goal:
  `mem.py project add <id> --name '...' --intent '...' --parent make-money`
  Anything the owner decides (picks, yes/no, on hold, skipped, paused) also gets `--tags decision`, so the Decision Log
  finds it.
- `experience`: what worked or failed and why (tool quirks, fixes, lessons).
- `knowledge`: general facts useful to every user or agent.

When something changes, save the new fact with `--supersedes <old id>`. The old one is deprecated, never silently
edited. If you are unsure of a fact, use `--status uncertain`. Agents other than the main session `propose`; the main
session is the gatekeeper and `commit`s.

Don't type the current time into a memory. Every save is stamped with the real time automatically, and `list`/`search`
show it as `[Oct 1 7:20 PM]`. If the text has a typed clock time, `add` warns and prints the real save time; check it or
drop it.

## The owner's controls

- "What do you remember about X": `mem.py search "X"` and answer plainly.
- "What did I decide about X": `python tools/memory/decisions.py X` (newest first, with dates; `--history` shows
  replaced ones, `--html out.html` makes the whole log a page).
- "Forget that": `mem.py status <id> deprecated --reason "<his words>"`. It disappears from search and the brief, and
  the history stays.
- "Erase it completely": `mem.py purge <id> --owner-request "<his words>"`. Only on his explicit ask.
- A bad idea that spread (a "mind virus"): `status <id> quarantined`, then search for copies and quarantine those too.

## Seats and intent

- Seats are stable agent roles (for example `assistant@main`, later `teacher@main`). Memories saved with `--seat` belong to
  the role, so a future model in that seat inherits them.
- **Each project is its own seat.** Before working on a project, run `mem.py rules <project>@main` and follow only
  those rules. Nothing carries over between seats. A new rule the owner gives for a project:
  `mem.py add --seat <project>@main --project <project> --layer project --tags rule --text '...'`. A new project gets
  its own seat with `seat add`.
- `mem.py intent <project>` prints the chain from the task up to the top goal. Check long work against it (the
  Refocus check): is this still serving the top goal?

## Never

- Never store tokens, passwords or keys, or anything from a protected secrets file.
- The archive and audit tables are append-only by design; do not try to edit them.
