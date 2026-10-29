---
name: seat-setup
description: Set up a new seat (project) for the assistant the one fixed way - memory seat and project, seat card, agent file, map row, skill index and health check. Use whenever the owner says "new seat", "make X its own seat", "this is under a new seat called X", or a project needs its own rules and memory.
---

# Seat setup

A seat is a project with its own address (`<id>@main`), rules, memory, seat card and agent. Nothing carries over between
seats. The owner decides that a seat exists; this skill only builds it. Use his words for what the seat does. **Never
write rules he didn't give.** A new seat starts with only his words and the hard lines every helper must carry.

`<id>` is short kebab-case (`news`, `ai-services`). `<Name>` is what the owner called it.

> The board, the skill index and the root rules file named below are not part of this repo; the memory tool and the
> health check are (`tools/memory/mem.py`, `tools/health/check.py`).

## Steps

1. **Check first.** `python tools/memory/mem.py seat list` and `python tools/memory/mem.py projects`. If the seat or
   project already exists, stop and fix only what's missing. Run `python tools/memory/recall.py "<Name> seat"` and
   collect every order the owner gave about it.
2. **Memory seat and project.**
   - `python tools/memory/mem.py seat add <id>@main --role "<Name> seat" --description "<his words>. Its own rules only."`
   - `python tools/memory/mem.py project add <id> --name "<Name>" --intent "<what it is for, in his words>" --parent <parent>`
     Parent is `make-money` for money projects, otherwise the assistant's own project. Ask him if it isn't clear.
3. **Rules.** Save each rule the owner gave for this seat:
   `python tools/memory/mem.py add --layer user --tags rule --seat <id>@main --project <id> --text "<his rule>"`.
   No rules from him yet means none are saved. Don't add any of your own.
4. **Seat card.** Write `projects/<id>/CLAUDE.md` from `templates/seat-card.md`. Fill every `{...}` and write nothing
   else into it.
5. **Agent.** Write the agent file for the seat from `templates/agent.md`. Its description says when the main seat hands
   work to it.
6. **Map row.** Add a `Seat: <Name>` row to the Map table in the root rules file, next to the other seats.
7. **Board item** (optional): only if the owner gave the seat a job that's still open.
8. **Check.** Rebuild the skill index, then run `python tools/health/check.py --fast`. Fix any failure before
   reporting. Then `python tools/memory/mem.py rules <id>@main` should show only his rules.
9. **Report** to the owner in plain words: the seat's name and address, what it does, which rules it has, and that it's
   ready.

## Rules

- Edit files with the Edit and Write tools, never shell heredocs.
- Keep the hard lines in the templates word for word. They're the owner's rules for every helper.
- One seat per run. A seat for a game or a business follows the same steps.
