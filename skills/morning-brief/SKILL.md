---
name: morning-brief
description: One short chat message to start the owner's day - what's waiting on him, today's one thing, where each project stands, the money scoreboard, hardware price hits and the model list date - built only from memory, the ledger and the watch files. Use when the owner says "morning brief", "catch me up", "what's going on", or when the scheduled run fires.
---

# Morning Brief

> The brief and weekly scripts are not part of this repo. This page is the routine.

Tool: `python tools/brief/morning.py` prints it, and `--send` also sends it through the chat bot. It reads only real
data. Nothing is invented, and it stays under 1,900 characters.

## What feeds it

- **Waiting on you:** memories tagged `waiting-on-owner`. When something truly waits on the owner (a decision, a file,
  an approval), save it with that tag. When it's done, deprecate it: `mem.py status <id> deprecated --reason done`.
- **Today's one thing:** the newest memory tagged `next-step`. Keep one, and replace it with `--supersedes` when it
  changes.
- **Where things stand:** the newest memory of each active project.
- **Money:** the ledger scoreboard. **Hardware:** Hardware Watch HIT lines. **Models:** the model list's last-updated
  date.

## Running it every morning

Scheduling is the owner's step (this skill never registers a scheduled task by itself). The command a scheduled task
should run is the brief script with `--send`. It needs no model session. It reads local files and sends through the chat
client. For a brief that also does a fresh Model Watch or Hardware Watch check first, a model session has to run those
skills before the brief.

## Weekly Review

When the owner says "weekly review" (or the weekly scheduled run fires): the weekly script with `--send` makes a PDF of
the past 7 days (built, decisions, corrections, waiting on him, blocked, money, parts goal, health), saves it, and sends
it with a one-line note. `--end YYYY-MM-DD` picks another week. If he wants fixes from the week's corrections, run
calibrate after.
