# Tools

The tested code of the Personal AI. Standard library Python; the tests need pytest. Every default path points inside
this repo, and runtime data goes under `data/` (never shipped).

| Tool | What it does | Tests |
|---|---|---|
| [`guard/`](guard/) | PreToolUse hook that refuses banned commands from an AI coding agent before they run | 201 |
| [`memory/`](memory/) | Layered memory in SQLite, recall before every job, and the decision log | 3 |
| [`health/`](health/) | One command that checks every part of the repo and prints OK or BROKEN per part | 3 |
| [`gpu_mailbox/`](gpu_mailbox/) | Signed, append-only mailbox for asking a host system for GPU time | 34 |
| [`privacy_scan.py`](privacy_scan.py) | Walks a folder and fails if anything private could be inside it | 39 |

Run everything:

    python -m pytest -q -p no:cacheprovider tools

Expected: `280 passed`.
