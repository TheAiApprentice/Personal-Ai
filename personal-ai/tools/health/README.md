# Health check

One command that tests every part of this repo and prints OK or BROKEN per part, so a break is found the day it happens.

## Checks

| Check | What it tests |
|---|---|
| guard hook | the guard refuses a banned command and lets a safe one through |
| junk chars | no hidden control characters in code, docs or manifests |
| pointers | every path the README files point to still exists |
| memory | a fresh memory database is created by the code and the brief loads (in a temp folder) |
| skills | every `skills/<name>/` has a `SKILL.md` and a valid `manifest.json` |
| skill index | `skills/README.md` lists every skill |
| memory dupes | near-duplicate memories (skipped when there is no database) |
| tests | every pytest suite in the repo |

Each line prints OK, WARN, SKIP, KNOWN or BROKEN. A KNOWN failure has its reason written down in the code.

## Use it

    python tools/health/check.py            all checks, exit 1 if anything is broken
    python tools/health/check.py --fast     skip the slow test suites
    python tools/health/check.py --json     machine-readable result

Expected on a fresh copy: `ALL OK (10 ok, 0 to tidy, 0 known, 1 skipped)`. The skipped one is memory dupes, because no
database is shipped. Everything is read from inside this repo.

## Tests

    python -m pytest -q -p no:cacheprovider tools/health

Expected: `3 passed`.
