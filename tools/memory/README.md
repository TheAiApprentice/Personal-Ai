# Memory

Long-term memory for an AI agent. One SQLite file, shaped like a planned PostgreSQL + pgvector schema so it can move
later with a straight copy.

## How it works

- **Layers.** `user` (preferences and personal context), `project` (goals, decisions, status), `experience` (what worked,
  what failed, why) and `knowledge` (general facts and lessons). Plus `archive`, the raw chat log, which is append-only and
  never edited.
- **Status.** A memory is `trusted`, `uncertain`, `deprecated` or `quarantined`. A newer memory can supersede an older one,
  so old decisions are kept but marked replaced.
- **Seats.** A memory can belong to a seat (a stable agent role), so whatever model sits in that seat later inherits it.
- **Intent chain.** Each project has an intent and an optional parent, so `intent <project>` prints the chain from the task
  up to the top goal. It's the anti-scope-creep check.
- **Full-text search** with SQLite FTS5.

## Files

| File | What it does |
|---|---|
| `mem.py` | The store: `add`, `search`, `brief`, `intent`, `rules`, `export` and more |
| `recall.py` | Run before any job: prints matching skills, saved memories, and the owner's own past messages |
| `decisions.py` | The decision log: every decision the owner made, newest first, with who decided and when |
| `test_decisions.py` | Tests for the decision log |

## Use it

    python tools/memory/mem.py add --layer project --text "We ship the weekly report on Fridays."
    python tools/memory/recall.py "make the weekly report like the last one"
    python tools/memory/decisions.py report
    python tools/memory/mem.py brief

The database is `data/memory.db`, created on first use. Set `AI_MEMORY_DB` to use a different file.
No database is shipped with this repo.

## Tests

    python -m pytest -q -p no:cacheprovider tools/memory

Expected: `3 passed`, on a throwaway database in a temp folder.
