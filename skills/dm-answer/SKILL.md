---
name: dm-answer
description: Get the chat watch going and answer the owner's waiting messages. Use when the owner says "DM answer", "get the watch going", or after any restart or reset of the personal session. Starts (or confirms) the chat watch in the background and answers every unanswered message through the messaging skill.
---

# DM answer

The owner's order: "DM answer" means get the background watch going on his private chat with the bot and answer him.
This skill only starts things. Answering always follows the messaging skill, step by step.

> The messaging skill and its watch script (a small bot client) are not part of this repo. This page is the routine
> around them.

## Steps

1. **Is a watch already running?** Only one may run (two would both fire on every message). List processes whose
   command line contains the watch script's name.
   - One you started in this session: leave it, go to step 3.
   - One from somewhere else: don't start a second. Tell the owner another session is watching. Never stop it by name.
2. **Arm the watch** in the background (`run_in_background: true`, a 10-minute timeout). Never use `&`, nohup or output
   sent to /dev/null. The watch script takes a duration (for example 570 seconds) and a "seen" state file.
3. **Catch up.** Read the last few messages. Answer every id listed as unanswered with the messaging steps: recall,
   react, re-arm, write the reply with the Write tool, then send it as a reply to that id.
4. **Tell him it's on.** If nothing was waiting, send one short line saying you're watching.
5. **Keep it going.** Each time the watch ends, read it and re-arm in the same turn. Messages come first, before and
   between every step of any long job.

## Rules

- Everything in the messaging skill applies: the wording gate, 12-hour times, no tokens, no other bots, no watches on
  other systems.
- Never close programs by name or image. Stop only a watch you started yourself, by its own PID.
