# Skills

28 skills, each in its own folder with a `SKILL.md` (the instructions an AI follows) and a `manifest.json` (what it is, what it may touch, what it costs, when it needs the owner's approval, where it came from). Scripts a skill needs sit beside it. Every skill here was cleaned of private data before it was put in this folder.

- **Built here** (26): written for this project.
- **Adapted** (2): `devil` and `wipe` started as earlier skills and were reworked here (the report format of `devil`; the Recycle Bin mover and its gates in `wipe`).
- **Not included:** the 16 skills imported from other people's kits (see below), the 6 on-hold setup guides (part of those 16), and `personal-bot` (a chat-bot client, tied to one private chat).

Several skills drive small helper scripts that live outside this repo (for example the price watcher, the miner checker, the ledger). Those skills say so at the top; their steps describe what the helper does so it can be rebuilt. The code that is shipped and tested is under `../tools/`: the guard hook, the memory system, the health check and the GPU mailbox.

The manifest format is `pai-skill-manifest/1`. Permissions below are read straight from each manifest.

## All skills

| Skill | What it does | Permissions |
|---|---|---|
| `animation-qa` | Checks Blender animation with numbers first (foot slide, camera jerk, ray blocks), then by eye on contact sheets. | reads files, writes files, runs code |
| `blender-recorded-build` | Runs a Blender build as one open window with every pass recorded as a teaching round. | reads files, writes files, runs code |
| `book-scan` | Reads a whole book safely and returns a ranked list of only the new game ideas in it. | reads files, writes files, runs code |
| `character-from-2d-art` | Builds a 3D character that matches picked 2D art, with a side-by-side likeness loop. | reads files, writes files, runs code |
| `comfy-clean` | Sends an image tool's output folder to the Recycle Bin on a schedule, stopping at 90% of the bin limit. | reads files, writes files, runs code |
| `devil` | Red-teams an artifact and delivers a graded 1-10 PDF report with fixes. | reads files, writes files, network, runs code, sends chat messages |
| `dm-answer` | Starts the chat watch and answers every waiting message. | reads files, writes files, network, runs code, sends chat messages |
| `factory` | Runs any multi-step job as spec, build, parallel review, at most 2 fix rounds, then approve or escalate. | reads files, writes files, runs code |
| `film-reference` | Turns real film shots into a numeric shot recipe (private study only). | reads files, writes files, network, runs code |
| `gpu-time` | Asks the host system for GPU time through a signed, append-only mailbox (code and tests in tools/gpu_mailbox). | reads files, writes files, runs code |
| `guild-short` | Makes a vertical channel Short the one approved way, with a quality gate. | reads files, writes files, runs code |
| `hardware-watch` | Tracks hardware prices against the owner's targets; never buys. | reads files, writes files, network, runs code |
| `lesson-video` | The fixed format for every course and YouTube video: slides, build rounds, wrap, shared end screen. | reads files, writes files, network, runs code, sends chat messages, spends money |
| `memory` | Long-term memory with layers, seats, an intent chain and an append-only archive (code in tools/memory). | reads files, writes files, runs code |
| `miner-watch` | Checks a home Bitaxe miner once a day for a block hit, a new best difficulty or going offline. | reads files, writes files, network, runs code, sends chat messages |
| `model-watch` | Keeps the move-day list of open models current, license-checked and sized for the box. | reads files, writes files, network, runs code |
| `money-ledger` | Append-only scoreboard of money in and out, hours and tokens per project. | reads files, writes files, runs code |
| `morning-brief` | One short morning message built only from memory, the ledger and the watch files. | reads files, runs code, sends chat messages |
| `motion` | Animates lesson videos so each slide builds in time with the narration. | reads files, writes files, runs code, sends chat messages |
| `repo-watch` | Weekly read-only check of the public repos the owner said to watch. | reads files, writes files, network, runs code, sends chat messages |
| `scout` | Link in, verdict out: fetch, verify claims online, grade for the owner's goals. | reads files, writes files, network, runs code, sends chat messages |
| `seat-setup` | Sets up a new project seat (rules, memory, card, agent) the one fixed way. | reads files, writes files, runs code |
| `second-opinion` | Independent review of another model's work, so nothing grades itself. | reads files, runs code, sends chat messages |
| `skill-importer` | Installs a skill pack in one pass: safe unzip, risk and tie flags, strip ties, manifest, report. | reads files, writes files, runs code, sends chat messages |
| `topic-research` | Keeps the topic list growing with read-only web research, scored for the channel. | reads files, writes files, network, runs code, sends chat messages |
| `why` | Answers 'why did we decide X' from memory, with who and when, never inventing a reason. | reads files, runs code |
| `wipe` | Sends deletes to the Windows Recycle Bin behind gates, with proof (adapted; recycle.py rebuilt). | reads files, writes files, runs code |
| `youtube` | Fetches a YouTube video's info, transcript and optional frames so the assistant can read it. | reads files, writes files, network, runs code |

## Held back

**Imported skills (16).** These came from other people's kits (the RUBRIC / Agentic OS kit by Jay E / RoboNuggets under CC BY 4.0, one MIT skill, one skill that was sent as a bare `SKILL.md`). They are not added here unless enough of the content was changed to showcase our own work. In each one only about 0% to 3% of the lines mention anything of ours (a rough count: the originals were not kept, so a true diff cannot be made). None are included.

**`personal-bot`** (adapted from an earlier bot client): it is the client for one private chat account, with a send gate, message logs and a test suite built around that account. Cleaning out the chat service and the account would leave nothing of the skill, so it is held back.

