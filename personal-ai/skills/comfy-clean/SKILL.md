---
name: comfy-clean
description: Weekly (run daily) clear of an image tool's output folder into the Windows Recycle Bin, stopping at 90% of the bin's limit. Use when the owner asks about clearing, cleaning or emptying the image-generator output folder, or about the output-clean scheduled task.
---

# comfy-clean

The owner's order: "build a program that will clear the output folder once a week from now on." And: "everything in that
folder once a week can be deleted, or you can do it faster and send it to the bin; the bin empties itself once a day."
A check confirmed nothing else reads that folder (finished panels are copied into each episode). It refills about 70 GB
a week.

> The helper script `comfy_clean.py` is not part of this repo. This page describes what it does so it can be rebuilt.

## What it does

The script sends every file inside the output folder (recursively, then the empty subfolders) to the Recycle Bin.

- Never a permanent delete (SHFileOperationW with undo; a move that would be permanent fails).
- Only that exact folder: the real path must match, and links and junctions are refused or skipped.
- Skips files modified in the last 60 minutes (the tool may still be writing).
- Bin rule: reads the bin size and the system-drive bin limit (MaxCapacity, about 49.7 GB). It stops before bin size
  plus the next file passes 90% of the limit. The rest waits for the next run; the bin empties itself daily. Refuses if
  the bin is set to delete on removal.
- Dry run is the default. One log line per run (execute only) in a log file.

## Run

Plan only: `python comfy_clean.py --dry-run`
Do it: `python comfy_clean.py --execute`

## Schedule (the owner registers it himself; never register it for him)

Daily, so a backlog held back by the bin limit drains over the following days. A Windows scheduled task running the
script with `--execute` at 4:00 AM does it.
