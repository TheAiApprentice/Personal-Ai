---
name: gpu-time
description: Ask the host system that owns the GPUs for GPU time and talk with it about that time - request, wait, get "you're clear" with how long you have, a 5-minute warning, "Orders from the GPU owner to start a job", release. Use it whenever you (the agent) want to run anything on the GPUs (a model, training, image or audio generation, a benchmark), whenever the owner asks you to use or book the GPUs, and after any restart to find out whether you hold GPU time. This skill is the one channel both ways: your requests go out through it and every reply from the host side comes back through it.
---

# GPU time

You may use a GPU only while you hold a current grant for it. The GPUs belong to a host system
(the GPU owner). While the host is busy with its own work no GPU is free and nothing is granted;
if the host needs a GPU while you hold it, your grant is preempted (stop and release; your
registered processes are ended 30 seconds later). When the host is idle, free GPUs are granted
promptly, card by card: you may get just one card (for example GPU 1 while the host uses GPU 0).
The host tells you when it is done and how much time you have before its next job.

This skill is the channel in both directions. You write your request, cancel and release through
`gpu_time.py`. The host side writes its acknowledgment, its "you're clear" grant, warnings, owner
orders and release checks through the same `gpu_time.py`, into the same mailbox, and you read
them with it. There is no other path.

## What enforces it

`gpu_time.py` is the enforcement; this page explains it. Its tests (`test_gpu_time.py`) use a
temp-dir mailbox and need no GPU.

- The mailbox is a folder (default `data/gpu_time` inside the repo, or the folder named by the
  `GPU_TIME_ROOT` environment variable). Every message is its own file, created once and never
  changed or deleted. Reading a message adds a receipt; nothing is moved or removed.
- Every message is signed with its writer's key (the `keys` folder of the mailbox). You sign as
  `agent`. You cannot write a grant, an ack or an owner order: those types are refused unless
  signed by the host side, and a forged or copied file is ignored. Never print, copy or quote a
  key file. (Both sides run as the same user, so this stops mistakes and forgeries by other tools,
  not a hostile program running as that user.)
- A grant is refused for a GPU the host is using or has reserved, while an earlier grant is not
  yet confirmed free, while an owner order is pending, after you cancelled, or after your request
  went stale (24 hours by default). The host and you can never hold the same GPU. A release or
  process registration for anything but your current allocation is refused as stale.
- `check-grant` and `run` refuse to start work on an allocation that is not current, not active,
  or does not have the time you need.
- While an owner order ("Orders from the GPU owner to start a job") is pending, NO new GPU work
  may start: `check-grant` says NO-GO whatever the job's length, and `run` admits a job only
  through a signed `admit` record that the mailbox refuses while an order is pending or when the
  job would outlive your effective end (your grant's end, or the owner's deadline if that is
  sooner). Work that was already running may finish until the owner's deadline. No new grant is
  issued to anyone while an owner order is pending.
- On the owner's order the host waits at most 5 minutes from the moment the order was recorded.
  After that your allocation is revoked and the processes you registered on it are ended, by exact
  process id, never by name. Release before then. The host's job starts only once the GPUs are
  verified free; if they are not, the host keeps the order pending and keeps checking, so anything
  you leave running only delays it.

## The commands

Run from the repo root. Write any long `--why` or `--note` text plainly (no backticks).

    python tools/gpu_mailbox/gpu_time.py init                      # once: folders, config, keys
    python tools/gpu_mailbox/gpu_time.py request --why "train a small model" [--minutes 90] [--gpus all] [--request-id ID]
    python tools/gpu_mailbox/gpu_time.py status
    python tools/gpu_mailbox/gpu_time.py inbox --side agent --mark-read
    python tools/gpu_mailbox/gpu_time.py check-grant --allocation AL --need-minutes 30
    python tools/gpu_mailbox/gpu_time.py run --allocation AL --need-minutes 30 -- python my_job.py
    python tools/gpu_mailbox/gpu_time.py register-pid --allocation AL --pid 1234
    python tools/gpu_mailbox/gpu_time.py release --allocation AL --note "done"
    python tools/gpu_mailbox/gpu_time.py cancel --request-id RQ
    python tools/gpu_mailbox/gpu_time.py verify [--full]           # signatures + chain audit

Request fields:

- `--why` (required, 1 to 500 characters): what the GPUs are for.
- `--minutes` (optional, 1 to 1440): how long you want. Leave it out to take the whole gap until
  the host's next job. The grant is never longer than the gap either way.
- `--gpus` (optional): `all` (the default) or a comma list of GPU numbers such as `1` or `0,1`.
  The numbers are nvidia-smi's GPU index.
- `--partial` / `--exact` (optional): with `--gpus all` you accept any free subset by default
  (`--exact` = only all of them); with an explicit list you need all of them by default (`--partial`
  = any of them). A partial grant names exactly the GPUs you got; use only those.
- `--request-id` (optional): your own id. Sending the same id with the same content again is the
  same request, not a second one (safe to retry). The same id with different content is refused.
- `--valid-hours` (optional, default 24): after this the request is closed as stale.

## What comes back, in order

Each message names the request id and, from the grant on, the allocation id. Match on them.

1. **ack**: "Got your GPU request ... This is a place in line, not permission". Do not touch the
   GPUs.
2. **status_note / no_window** (maybe): you are still waiting, and why: the host is not finished,
   the GPUs still hold the host's models, telemetry is down, or there is too little time before the
   host's next job (under 10 minutes usable). Keep waiting.
3. **grant**: "You're clear. You have X until the next host job starts." Its fields: request id,
   allocation id, gpus (exactly the GPUs granted; requested_gpus and partial say whether you got
   fewer than you asked for), start, expires (when you must be done), next start, remaining time,
   the handoff allowance (the minutes kept free before the start), timezone (shown in the
   `GPU_TIME_TZ` zone, stored as UTC), and the exact release command. A partial grant leaves the
   other GPUs you asked for OUTSTANDING: each one arrives later as its own grant (a second
   allocation id) the moment it is free. You may hold several allocations at once (on different
   GPUs); release each by its own id. Requests are served strictly oldest first per GPU. If you
   asked for exact GPUs and only some are free, a **reserve** message tells you a GPU is being held
   for you (up to 10 minutes) so no younger request takes it. If no next start is known the grant
   says so and has no end: it lasts until you release it or an owner/scheduled start reclaims it.
   Only now may you use the GPUs, only those named, and only until `expires` (if there is one).
   Pin your job to the granted GPU(s) by index, e.g. for GPU 1:
   `CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=1`.
4. **warning**: "5-minute warning". Start nothing new. Finish or checkpoint, then release.
5. **owner_start**: "Orders from the GPU owner to start a job -- you have 5 minutes to finish up",
   with an exact deadline. Same as a warning but the deadline is hard: start nothing new (the
   mailbox refuses it anyway), checkpoint, stop, release.
6. **schedule_change**: the next host job moved earlier; your end time is earlier. A later start
   never lengthens your grant.
7. **expire / revoke / preempt**: your time is over, or the host needs the GPUs. Stop at once and
   release.
8. **release_verified / release_unverified**: the host checked that your processes are gone and
   the GPUs show nothing new. Unverified means something is still running; stop it.
9. **reject**: your request closed (stale, or refused). Send a new one if you still need time.

## How to work with it

1. Request. Then wait. Poll with `status` and `inbox --side agent --mark-read`, or arm
   `gpu_time.py watch --side agent --seconds 3600` in the background.
2. When woken, run `inbox --side agent --mark-read` and act on every message, oldest first.
3. Before starting any GPU job, run `check-grant --allocation AL --need-minutes N` with an honest N
   for the job. Exit 0 ("GO") means current, active, no owner order pending and enough time.
   Anything else ("NO-GO") means do not start it. check-grant is a preview; the binding decision is
   the `admit` record that `run` writes.
4. Start GPU jobs through `run --allocation AL --need-minutes N -- <command>`. It writes the atomic
   `admit` record first (refused = the job never starts), registers the process so the host can
   tell when it is gone, and stops the process it started if the grant ends or the owner's deadline
   passes while it runs. If you start a GPU process another way, register it right away with
   `register-pid` (that path has no atomic admission; prefer `run`).
5. When your work is done, release at once with `release --allocation AL`. Early release gives the
   GPUs back; on an owner order it lets the host's job start right away instead of after the full
   5 minutes.
6. On a warning, an owner order, a revoke, an expiry or a preemption: start nothing new, checkpoint,
   stop your processes, then release. Never keep going past the stated time.
7. Wanting more time after a grant ends means a new request. A grant is never extended.

## After a restart or a lost connection

Run `status`. It shows your requests, your allocations with what is left, owner orders and how many
messages you have not read. Then `inbox --side agent --mark-read`. Trust `status`, not memory: if
your allocation shows anything but `active` with time left, it is over; stop and release.

Reject any grant that is expired, revoked, cancelled, not your current allocation, or whose request
you cancelled. `check-grant` does this for you; when it says NO-GO, do not use the GPUs.

## Errors

- Exit 2 "mailbox not initialised": the one-time setup was not run (`gpu_time.py init`). Ask the
  owner; do not create it yourself unless told to.
- Exit 3 REFUSED: the reason is printed (stale allocation, already released, cancelled, bad field).
  Read it; do not retry the same thing.
- Exit 4 from `verify`: a message file failed its signature or chain check. It is ignored
  automatically; tell the owner.
- Exit 5 from `probe`: GPU telemetry could not be read. The host will not call the GPUs free while
  that lasts. Under WDDM nvidia-smi shows "[N/A]" for every process's own memory; that is normal
  and is never read as 0 MB. What decides "free" is the per-GPU memory and utilization (`probe`
  shows both under "gpus"); a GPU whose numbers cannot be read counts as not free.

## Rules

- No GPU use without a current grant. No GPU use past `expires`.
- Never open, print or quote a key file.
- This skill does not start, pause or touch the host's own work; it only asks for time and answers.
