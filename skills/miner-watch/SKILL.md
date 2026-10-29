---
name: miner-watch
description: Watch the owner's small home Bitcoin "lottery" miner (a Bitaxe running AxeOS on the local network) for a block hit, a new best difficulty or the miner going offline, and report in plain words. Use when the owner says "miner", "bitaxe", "lottery miner" or "update on the miner", and once a day in sessions.
---

# Miner Watch

The owner's order: "look once a day, or anytime I ask for an update on it". "That" is the miner hitting a block: a
share with difficulty at or above Bitcoin's network difficulty.

> The tool `miner.py` is not part of this repo. This page is the routine. The miner's address is read from the
> `MINER_URL` setting, never written into a file here.

Tool: `miner.py`. Read only: it only does GET on the miner and never changes its settings. It never prints or stores the
wallet address, WiFi name or MAC. The last reading is kept in a small state file.

## Steps

1. Run `python tools/miner/miner.py check`. Exit code 0 ok, 2 HIT, 3 OFFLINE.
2. On a HIT line, tell the owner right away, before anything else.
3. On a NEW BEST line, message the owner too (old -> new value). He likes watching his highest go up, even though it does
   not change the odds. The state file keeps every new best with its date (`best_history`).
4. On an OFFLINE line, message the owner that the miner did not answer.
5. When the owner asks for an update, send him the result in plain words: hashrate, best difficulty, how many times
   short, and any NEW BEST.
6. Run it at every session start and once a day while running. The morning brief also carries a one-line miner section.

## No scheduled task

The owner's choice: "just make it something you do, if you crash who cares, you will just look when I start you up."
There is no scheduled task for this; the session start step runs it.
