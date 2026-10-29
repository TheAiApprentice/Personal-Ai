---
name: model-watch
description: Keep the move-day model download list current. Check for new open models and AI tools, compare them to the current picks (quality, license, fits on 96 or 128 GB, works on AMD ROCm), and update the model registry with reasons. Use when the owner says "model watch", "any new models", "update the download list", or about once a week.
---

# Model Watch

The owner's standing task: keep the best open models and tools tracked so the download list is ready the day the box is
built.

> The registry tool and its data file are not part of this repo. This page is the routine.

Tool: `python tools/models/registry.py` (`list`, `plan`, `add --file`, `set <id> key=value`, `script`). Data: one JSON
registry file. A human-readable copy is kept as a PDF.

## Steps

1. `registry.py list` to see the current picks, and note the `updated` date.
2. Search what's new since then, using a subagent for breadth. Check Hugging Face, release blogs and leaderboards
   (Artificial Analysis, LMArena, Open ASR, the TTS and image/video arenas), plus runtime releases (vLLM, llama.cpp,
   ROCm). Verify everything online, never from memory.
3. For each candidate, record: HF repo id, size, license (flag non-commercial or revenue caps), whether it fits on 96 GB
   (3090s) or 128 GB (R9700s), and ROCm status.
4. Update the registry:
   - a new pick, or a candidate for "watch": `registry.py add --file entry.json`
   - an old pick that's beaten: `registry.py set <id> status=retired notes="replaced by X: reason"` (retired entries
     stay, so the history is kept)
5. `registry.py plan` to check the day-1 total still fits the 4 TB drive.
6. Tell the owner in 3-6 lines what changed and why. Rebuild the PDF only if the day-1 list changed.
7. Save one memory line under the model-stack project.

## Rules

- License beats benchmark. A non-commercial model never goes on the day-1 list, because the goal is making money.
- "Unverified" stays marked until someone checks it.
- Downloading anything is a move-day job; this skill only plans.
