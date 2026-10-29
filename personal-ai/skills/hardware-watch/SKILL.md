---
name: hardware-watch
description: Track prices for the future self-hosted AI box (GPUs, a Threadripper CPU, a workstation board, ECC RAM, PSUs, drives) against the owner's target prices and flag when a target is hit. Read-only, never buys. Use when the owner says "hardware watch", "check GPU prices", "set a target for X", or about once a week.
---

# Hardware Watch

> The tool `watch.py` and its data files are not part of this repo. This page is the routine.

Tool: `python tools/hardware/watch.py` (`list`, `record`, `target`, `report`). Parts and targets live in one JSON file.
Every price seen goes into an append-only JSONL file. The first prices were copied from the master brief's snapshot and
are labelled as such.

## Steps

1. `watch.py list` to see the parts and targets.
2. Check current prices online for each part, using a subagent for breadth: the owner's local store first, then the big
   retailers. For a used-market GPU, also check refurbished and used listings from real sellers.
3. Record each real price seen:
   `watch.py record --part <part> --price 1549.99 --store "<store>" --url <url> --in-stock yes`
4. `watch.py report`. Lines starting with HIT mean a target was reached. Tell the owner about any HIT right away.
   Otherwise send a 2-4 line summary only if something moved.
5. Targets are the owner's to set: `watch.py target --part ecc-128gb --price 2000`. Suggest targets, but never set one
   he hasn't agreed to.

## Rules

- Never buy, add to cart, sign in to a store or enter payment details.
- Record only prices actually seen on a page, with the URL. No guesses.
- Watch for the brief's purchase gate: buy one GPU and test the software stack before buying four.
