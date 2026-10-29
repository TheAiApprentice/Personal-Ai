---
name: money-ledger
description: Track money in vs money out (plus hours and tokens) per project, so every money idea has a scoreboard. Use when the owner mentions a cost, a subscription, a purchase, a sale or revenue, time spent on a project, or asks "are we making money", "what has X cost", "scoreboard".
---

# Money Ledger

Master brief, section 16: an internal ledger that "cannot be rewritten". All money belongs to the owner; this only
measures which projects pay.

> The ledger tool and its database are not part of this repo. This page is the routine.

Tool: `python tools/ledger/ledger.py`. Data: an append-only SQLite database. The database itself refuses edits and
deletes.

## Use

- Cost: `ledger.py add --project <memory project id> --kind cost --amount 20 --note "assistant plan, Oct"`
- Revenue: `ledger.py add --project <project> --kind revenue --amount 4.99 --note "store sale #1"`
- Time: `--kind hours --amount 1.5`. Model usage: `--kind tokens --amount 120000`.
- Scoreboard: `ledger.py report` (or `--project X`). Recent entries: `ledger.py list`.
- A mistake gets a correcting entry: `--amount -20 --corrects <id> --note why`. Never try to edit.

## Rules

- Only log numbers the owner gave or that are on a real receipt or statement. Never estimate a cost and log it as fact.
  If a number is a guess, say so in the note or don't log it.
- Use the memory project ids (`mem.py projects`) so the ledger and memory line up.
- The assistant can't spend money. The ledger records, it never pays.
- The morning brief prints the scoreboard every morning.
