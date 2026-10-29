# Personal AI: skills and tools

**The skills and the tested code behind a personal AI that runs on one home PC, with an AI coding agent (Claude Code) as its working brain until it moves to its own self-hosted model.**

Everything here is real and in daily use. It was cleaned of private data before it went up, and a privacy scan checks the whole folder.

- **28 skills**, each with a `SKILL.md` and a machine-readable `manifest.json`, in [`skills/`](skills/)
- **5 tools with 280 tests (19 of them run on Windows only)**, in [`tools/`](tools/): a guard hook, a memory system, a health check, a GPU-time mailbox and a privacy scan
- **Standard library Python plus pytest.** No accounts, no keys, no network needed to run the tests

---

## Why it exists

An AI agent that works on a real PC every day needs more than a good model. It needs to remember what was decided,
follow the same steps every time, never do something dangerous because a prompt said not to, and share the machine
with other work without getting in the way. This repo is those parts:

| Problem | What solves it here |
|---|---|
| The agent forgets everything between sessions | **Memory** (`tools/memory/`): layered memory in SQLite, an append-only chat archive, and a recall step before every job |
| Written rules get ignored | **Guard hook** (`tools/guard/`): rules enforced in code before a command runs, with 201 tests |
| Jobs get done a different way each time | **Skills** (`skills/`): anything done twice becomes a skill with a manifest that says what it may touch |
| Two systems share the GPUs | **GPU-time mailbox** (`tools/gpu_mailbox/`): signed, append-only request, grant and release |
| Something breaks and nobody notices | **Health check** (`tools/health/`): one command, OK or BROKEN per part |
| Private data leaks into public files | **Privacy scan** (`tools/privacy_scan.py`): fails on paths, names, ids, keys and more |

## What's in here

```
skills/                 28 skills, one folder each (SKILL.md + manifest.json + any scripts)
tools/
  guard/                PreToolUse guard hook and its 201 tests
  memory/               memory store, recall and the decision log
  health/               the health check
  gpu_mailbox/          the GPU-time mailbox and its 34 tests
  privacy_scan.py       the privacy scan and its 39 tests
```

Each folder has its own README with how it works and how to run it.

## Highlights

- **The guard hook refuses dangerous commands before they run.** Killing programs by name, hard deletes, shell heredocs
  that write files, reading a protected secrets file, and Python reading its script from standard input. Each rule exists
  because it went wrong once on a real machine. 201 tests cover them.
- **Every skill has a manifest.** It lists what the skill may touch (files, network, code, messages, money), which steps need
  the owner's approval, how it is tested, and where it came from. A checker fails any skill without one.
- **The GPU mailbox can't be talked around.** Every message is a signed file that is never rewritten. A grant has an end
  time, a forged or stale message is ignored, and release is checked.

## Check it yourself

Python 3.11 or newer, and pytest. Windows is the main target.

    python tools/privacy_scan.py .
    python -m pytest -q -p no:cacheprovider tools
    python tools/health/check.py

Expected: the scan passes with 0 findings, pytest reports **280 passed on Windows; on Mac and Linux it reports 261 passed and 19 skipped (Windows-only path tests)** (201 guard, 39 privacy scan, 34 GPU mailbox, 3 memory, 3 health check), and the health check
ends in `ALL OK`. Every default path points inside this folder.
Runtime data (the memory database, the mailbox) goes under `data/`, which is in `.gitignore` and never shipped.

## What's not here

- **No data.** No memory database, no chat logs, no keys. The code creates empty ones on first use.
- **16 imported skills** from other people's kits are left out, because they are not mostly our own work.
  [`skills/README.md`](skills/README.md) lists them and why.
- **Some helper scripts** that a few skills call (a price watcher, a miner checker, a ledger) are not included.
  Those skills say so at the top and describe what the helper does.

## How it was built

Built with Claude Code as the agent and the owner setting every rule and approving every result. Big jobs run as a small
"factory": a spec writer, a builder, parallel read-only reviewers (correctness, safety, match), at most two fix rounds,
then an approver. The [`factory`](skills/factory/SKILL.md) skill describes it.

## License

MIT, see [LICENSE](LICENSE).
