---
name: wipe
description: The assistant's delete tool. Whenever the owner says delete, remove, wipe, scrap, trash, nuke or "get rid of" a file or folder, send it to the Windows Recycle Bin with this skill's recycle.py so he can check it and restore or empty it himself. Also use it whenever you are about to delete anything at all. Never hard-delete, never rm -rf, Remove-Item or shutil.rmtree, never a wildcard.
---

# Wipe (the delete tool)

The owner's order when setting this up: "make it work for this system, it's the new delete tool, so if I say delete
something or whatever, use that: it puts it in the recycling bin and then I can check it and decide if it was a mistake
or remove it." It was adapted from an earlier delete skill; the Recycle Bin mover was rebuilt
as `recycle.py`.

So "delete" always means: into the Recycle Bin, recoverable. Emptying the bin is the owner's job, never ours.

## Steps (same turn, no confirmation question when his words name the thing)

1. **Find the literal paths.** List the folder and name each file or folder exactly. Never a wildcard, never "everything
   matching". If his words could mean more than one thing, list the candidates with full paths and ask him which. That is
   the only question.
2. **Save his words** to an order file (his exact message), e.g. in the scratchpad.
3. **Dry run** (it reads only):
   `python skills/wipe/scripts/recycle.py --path "<abs path>" [--path ...] --order-file <f>`
   It prints a PLAN line per path, or REFUSED with every reason. Nothing moves.
4. **Move:** the same command with `--execute`. It proves every path is gone from disk and listed in the Recycle Bin,
   writes a result JSON in `data/wipes/`, and prints `RECYCLE CLEAN`. Anything else is not done.
5. **Report** plainly: what went to the Recycle Bin (names and sizes), that he can restore it from there or empty the bin
   when he's sure, and anything refused and why.

## What it refuses (moves nothing)

- wildcards, relative paths, paths that don't exist, a path listed twice or inside another;
- links and junctions, and folders that contain one;
- drive roots, Windows, Program Files, ProgramData, the user-profile root and its top folders (Desktop, Documents,
  Downloads...);
- anything under a folder named in `WIPE_PROTECTED` (a list of folders separated by the OS path separator; set it to keep
  other systems' folders off limits);
- the repo root and its top-level folders and files (only things inside them), the `data/` memory folder, and
  secrets/config files (`api.env`, `.env`, `config.json`...);
- a move the Recycle Bin would turn into a permanent delete: bin set to delete on removal, or the item bigger than the
  bin's space (90% limit).

If it refuses, tell him exactly why. Never work around a refusal (no hand delete, no other tool).

## Never

- `rm -rf`, `Remove-Item`, `del`, `shutil.rmtree`, `os.remove` on anything of his, or emptying the Recycle Bin. Permanent
  deletes are his to do.
- A wildcard or a pattern: one `rm -rf .../the-*` once destroyed four finished videos that were not the target. Literal
  names only.
- Moving files by hand "to be safe" or renaming them to park them. The bin is the only place.

Rules distilled from earlier lessons: `references/rules.md`.
