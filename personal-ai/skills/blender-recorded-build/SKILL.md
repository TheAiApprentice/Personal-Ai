---
name: blender-recorded-build
description: How a Blender build runs when the whole build is also a teaching video - assets, buildings, characters, scenes. One Blender window kept open for the whole build, every pass a recorded round (ask, first result, tweak, second result) written in rounds/plan.md, the owner's feedback as new rounds, a privacy text scan on every recording, GPU only under a grant, and the recording keeps going until the owner approves the asset. Use whenever you start, resume, change or re-record a Blender build, or the owner gives feedback on one.
---

# Blender recorded build

Done twice the same way: a game-asset build (24 rounds) and a character walk-up (23 rounds). Both run on one
shared recorder script that opens Blender, runs a round plan and writes frames. Copy the layout; never invent a new
one.

> The recorder and the per-build helper scripts named below are not part of this repo. This page is the method:
> write or reuse your own recorder with the same round-file shape.

## The owner's rules for this work

- One Blender window, opened once and kept open for the whole build. Every first result and every tweak happens in
  that same window. Never close and reopen it between rounds.
- Record every pass. The teaching video is the whole build, from the start until the owner approves the asset.
  Feedback rounds are recorded too, and nothing is cut until he approves.
- Match the picked art or concept sheet as closely as you can: silhouette, prop density, details, light. Keep going
  until it really matches, and don't send progress updates or side-by-sides on the way.
- Scale: 1 unit = 1 m, a person is 1.8 m tall. Never make people bigger to make them read. Say "more visible", never
  "bigger". Follow the target engine's version and the asset brief.
- The GPU is only yours under a current gpu-time grant, and the Blender window's EEVEE viewport counts as GPU use.
  When the owner says pause, everything stops, CPU work included.
- Big output (recordings, renders, staging) goes on a big drive, not the system drive.
- Edit files only with the editor tools. No shell heredocs, no `sed -i`, no `python -c` edits. Never `python -` with
  a heredoc: it waits on stdin and hangs.
- Stop only processes you started, by the PID you wrote down. Never by name or image, never by matching command text.

## Build folder layout (the same in both builds)

| Path | What it is |
|---|---|
| `src/` | A shared library (the recorder imports `Ctx` and `reset_scene` from it), helpers, and one part module per round, `rNN_name.py`, each with generators `v1(ctx)` and `tweak(ctx)`. Each `yield "text"` is one visible step; `yield ("tick", "text")` marks a long job that the video shows sped up. |
| `rounds/<round>.json` | The round plan: `round`, `module`, `src`, `out_dir`, `save_blend`, `view`, `ui`, the chat text `ask`, `first_result`, `tweak`, `second_result`, and `steps` (open, run1 build v1, result1 orbit, run2 build tweak, result2 orbit or play, holds). Copy an existing one. |
| `rounds/plan.md` | Every round in words: module, ask, first result, tweak, second result. The owner's feedback is quoted word for word with the time. |
| `dev/` | Not recorded: purge (forget cached modules), rebuild rounds 1..n, run one module, a full recorded run from r01, checks and render helpers. |
| `recordings/<round>/` | Frames, `session.json` and `end.blend` per round. |
| `review/` | Compare images, contact sheets, check results, previews. |
| `export/` | The delivered pack (engine builds). |
| `gpu_pids.txt` | Every GPU process PID you start (the recorder writes Blender's here). |

## Steps

1. **Memory first.** Recall the job, read the seat's rules, and read the build's `RESUME.md` (if any) and
   `rounds/plan.md`. Never redo what is already decided or built.
2. **GPU grant.** Follow the **gpu-time** skill. Before opening Blender,
   `python tools/gpu_mailbox/gpu_time.py check-grant --allocation <AL> --need-minutes 30` must say GO.
3. **Staging.** Each build stages in its own folder, named by an environment variable the recorder reads. The staging
   folder holds a fresh Blender preferences folder, so no recent files or user paths are ever drawn.
4. **Open the one window** (only if it is not open already). The PID is written to `<staging>/blender.pid` and to
   `gpu_pids.txt`. Register it:
   `python tools/gpu_mailbox/gpu_time.py register-pid --allocation <AL> --pid <pid>`.
   If another helper already has the window open, use that window and don't start a second one.
5. **Write the round.** The part module (v1 = the first result, tweak = the narrator's tweak), the round file, and its
   section in `rounds/plan.md`. The ask and tweak are said the way the teacher would ask the AI, since they become
   the chat panel of the teaching video.
6. **Try it without recording.** Purge, rebuild rounds 1..n, or run the one module on the current scene. Scripts run
   inside the window get `ARGS`, `shot(path)` (screenshot) and `setup_ui()`. Fix until it runs clean and looks right.
7. **Record it.** The recorder prints `SESSION OK <round> frames N`. Then add the round to the full-run script and the
   module to the module list used by the rebuild script.
8. **Full re-run when an earlier round changed.** First copy the old recordings to `recordings_archive/before_<date>/`
   (the video keeps its history; nothing is deleted). Then run the full recorded run from r01, all in the same open
   window (about 20-40 minutes), in the background, and wait for it to finish.
9. **Check it.** Anything that moves goes through the **animation-qa** skill. A character goes through the
   **character-from-2d-art** likeness loop. A building: render the concept sheet's views and put them beside the
   concept art. Look at every image yourself, give an honest likeness score out of 10, and list the gaps worst first.
   Don't call it done below the bar.
9b. **Rendering on both cards.** Always use every card you were granted. Never split a range in halves. One frame
    pool, every renderer pulls from it: each frame is claimed atomically with `O_CREAT|O_EXCL` in `<out_dir>/claims/`
    and skipped if claimed or on disk; a stale claim from a crash is taken over after 5 minutes.
    - GPU check first (gpu-time: `check-grant`, inbox), and register every PID you start.
    - The display card renders from the open window. The other card needs its own throwaway user config (EEVEE
      ignores `CUDA_VISIBLE_DEVICES`): save a copy of the scene, then start Blender in background mode with the pool
      script, `BLENDER_USER_CONFIG` and `BLENDER_USER_SCRIPTS` pointing at that throwaway folder. Check with nvidia-smi
      that the card takes memory.
    - A background EEVEE process can crash (light-probe atlas): watch its log, restart it, and the pool picks up where
      it stopped. Count the frames (all of f0..f1 on disk) before encoding.
10. **Privacy scan on every recording.** Run an OCR pass over each recording folder (every 8th frame); it must report
    0 banned hits. Also search `session.json`, `plan.md`, the import notes and `RESUME.md` for the machine's user name
    and for user-profile paths: zero hits. The recorder refuses to draw or save a user path, but the scan is still run
    every time.
11. **Engine export (game assets only).** The proof runs headless and only at the end: run Blender in background mode
    with a check script on the exported `.fbx` (and `.glb`); it must print CHECK PASS, and a second check does the
    same for characters. Only then copy into the build's `export/`. Fill the import notes with everything the brief
    asks for. FBX settings that re-import correctly: bake_space_transform False, FBX_SCALE_ALL, -Z forward, Y up.
12. **The owner's feedback = a new round.** Quote his words in `plan.md`, save them to memory right away, name the
    round for the fix (e.g. `r20_carry`), and keep the same window. Previews for him go in a new `review/previewN/`.
    The main seat sends them; this seat never messages him.
13. **Write the state down.** Update `RESUME.md` (done, current export, known gaps, exact resume steps) and `plan.md`.
    Save a project memory with the counts and the honest score, and an experience memory for each lesson learned.
14. **Stop only at the very end.** Stop the recorder, or end the PID in `blender.pid` by its own PID. Then release the
    grant through the gpu-time skill. Report to the main seat: what changed, what was run, the checks and their
    numbers, what is still open.

## Blender lessons already paid for

- Timeline markers bound to cameras switch `scene.camera` back on every `frame_set`. Unbind them before preview or
  turnaround renders and bind them again after.
- Simple driver expressions have `abs` but not `max`. A `max(...)` driver silently goes invalid, so use `1-abs(f-c)`
  and let the shape key's 0..1 range clamp it.
- Lights inside lantern glass are fully shadowed, so set the lantern's `visible_shadow` False. An even EEVEE world
  volume mist browns every frame, so get depth from light and local volumes instead.
- Read an object's `matrix_world` only after the depsgraph updates, or use a local-matrix helper. About 14 rack
  swords once sat hidden at the origin because of this.
- Boxes built from slabs need outward winding, or backface culling hides them. Book covers need matte leather and no
  subsurf.
- Triangle budgets get tight. Trade triangles (fewer-sided lathes on static figures, lighter swords) before you raise a
  budget, and write down any budget you raise.
