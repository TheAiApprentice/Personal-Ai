# GPU-time mailbox

A signed, append-only mailbox for sharing GPUs between an AI agent and the host system that owns them. The agent asks for
time; the host answers with an acknowledgment, a "you're clear" grant with an end time, a 5-minute warning, or a revoke;
the agent releases and the host checks the release. One file, `gpu_time.py`, is the whole channel both ways.

## Why it's built this way

- **Nothing is rewritten.** Each message is its own numbered file, created once and never changed or deleted. The state is
  worked out from all the files in order, so there's no state file to get out of sync.
- **Every message is signed.** Each side has its own key (HMAC-SHA256). Each file also carries a hash of the file before it
  and a hash of the code that wrote it. A message with a bad signature, a broken chain, the wrong signer or an illegal step
  is ignored, so a delayed, replayed or forged message can't change a newer grant.
- **Grants end.** A grant names the GPUs and an end time. `check-grant` says GO or WAIT, and `run` refuses to start work
  without a current grant.
- **Stated limits.** The keys stop unsigned and wrong-side writes. They can't stop a hostile process running as the same
  user that reads the key files. That's said plainly, not hidden.

## Use it

    python gpu_time.py init                                   once: folders, config, keys
    python gpu_time.py request --minutes 90 --why "train a model" --gpus all
    python gpu_time.py inbox --side agent --mark-read
    python gpu_time.py check-grant --allocation <id> --need-minutes 30
    python gpu_time.py run --allocation <id> -- <command ...>
    python gpu_time.py release --allocation <id>
    python gpu_time.py verify --full                          check every signature and the chain

The mailbox lives in `data/gpu_time` (set `GPU_TIME_ROOT` to move it). Minutes per request: 1 to 1440.
`SKILL.md` is the agent's side of the protocol, step by step.

## Tests

    python -m pytest -q -p no:cacheprovider tools/gpu_mailbox

Expected: `34 passed`. They cover request, ack, grant, check, release, signatures, the append-only chain, forged and stale
grants, and the minutes limits, all in a temp folder.
