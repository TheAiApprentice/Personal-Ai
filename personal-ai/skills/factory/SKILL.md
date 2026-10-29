---
name: factory
description: How the main session runs any multi-step job - the main session orchestrates and stays on the owner's messages, helper agents do the work (spec writer, builder, parallel read-only reviewers, at most 2 fix rounds, approver that finishes or escalates to the owner). Use for any job with more than one step, any build or change, and whenever a seat's work is handed out. Not for a one-line answer.
---

# Factory

The owner's order: build the "AI software factory" set up for each seat and for the assistant in general. The main
session is the orchestrator. It stays on the owner's messages, hands work to helper agents and only relays their
results. It doesn't do the building itself.

Each job is an item on the open-items board with a stage. The job list is the board, nothing else.

Helpers: `factory-spec`, `factory-builder`, `factory-reviewer`, `factory-approver` (agent files). Every helper prompt
carries the hard lines; they are already in each agent file.

> The board tool, the agent files and the gate script named below are not part of this repo. This page is the
> procedure.

## Steps (every job, in order)

0. **Busy gate.** Before any build step, run the busy-gate check (a script that says GO or WAIT). WAIT = the machine
   may be busy: no build work at all, CPU or GPU, for the main seat or any helper. Request time
   with the gpu-time skill and start only when the grant comes. After every helper job, run the leftovers check and stop
   anything of ours it lists, by PID. Talking with the owner, memory and planning in chat are not build work.

1. **Memory first.** Recall the owner's words. If a skill already does this job, run that skill instead (it may use the
   factory for its own steps). Work out the seat: the assistant itself or one project seat. Unclear which seat, or the
   job could mean two things: ask the owner one quick question first.
2. **Board item.** Add the job to the board, in the owner's words, at stage `spec`.
3. **Spec.** Hand to `factory-spec` with his exact words, the seat, and the recall output. It returns a short spec: goal
   in his words, steps, "done when" checks, and anything outward-facing. It never adds requirements he didn't ask for.
   If the spec has an open question only the owner can answer, go to step 8 (escalate) before building.
4. **Build.** Move the board item to `build`. Hand the spec to `factory-builder`, or to the seat's own agent when the
   job belongs to a seat, with the spec pasted in and the hard-lines block from the builder's agent file. It returns
   what changed and what it actually ran. It also leaves a **proof**: a short script or command, with its expected
   output, that a reviewer can run to see the thing really works end to end.
5. **Review.** Move the item to `review`. Start the reviewers in parallel, all `factory-reviewer`, each told its one
   lens and given the spec plus the builder's report:
   - **correctness**: does it work, do the tests and the health check pass; runs the builder's proof and FAILs if it is
     missing or doesn't show the behavior;
   - **safety**: the owner's hard lines (see the agent file) and privacy (no personal name or paths in anything
     public);
   - **match**: does it do what he asked, no more and no less, and does it follow the seat's rules.
   Each returns PASS or FAIL with a short list of concrete fixes. Small jobs (one file or one short change, nothing
   outward-facing) get one reviewer covering all three lenses; everything else gets all three.
6. **Fix rounds (at most 2).** Any FAIL: move the item back to `build`, hand the fixes to the builder, then review again
   (only the lenses that failed, plus correctness). The board refuses a third round; after 2 rounds with a FAIL left,
   escalate.
7. **Approve.** Hand everything to `factory-approver`. It finishes the job or escalates:
   - Finish: saves what was built or decided to memory with the seat's `--seat`/`--project`, then marks the item
     `approved` and done.
   - Escalate: anything outward-facing always escalates, even if every review passed.
8. **Escalate.** Mark the item `escalated` with one short question. The main session asks the owner that one question.
   When he answers, save his answer to memory and carry on from the step it unblocks. Only he closes an escalated item.
9. **Relay.** The main session tells the owner the result in plain words. Long reports go out as a PDF.

## Always escalates to the owner

Sending anything (email, message, post), publishing, spending money, installs that need admin, signing in to any
account, starting servers, scheduled tasks, GPU use outside a gpu-time grant.

## Models per role

Use the best model for each role, and the top tier isn't always needed. So: spec writer and approver on the larger
model, builder and reviewers on the mid-size model. The agent files set these; change them there.

## Rules

- Only the owner's rules apply: the project rules file, memory, and the seat's own rules. Helpers never add their own.
- A seat job uses that seat's rules only. Nothing carries over.
- Pause means stop: when the owner says pause, stop the factory and every helper, and wait for resume.
- Reviewers are read-only. Only the builder changes files.
