---
name: why
description: Answer "why did we/you ...", "why is X like that", "why" with the history from memory - what was decided, when, who decided, what replaced it. Plain words in the message. Never invents a reason.
---

# Why

The owner's order: ask why something was decided and get the history, straight in the chat.

## Steps

1. Pick the topic: one to three key words from his question (no filler words). `decisions.py` needs every word to
   appear, so if nothing comes back, retry with fewer or different words.
2. Run `python tools/memory/decisions.py --plain --history <topic words>`. It prints one line each, newest first: when
   (12-hour, the time it was saved), who decided, what, and REPLACED (by #N).
3. Run `python tools/memory/recall.py "<his question>"` for his past messages and related memories the decision list
   missed (the "OWNER SAID" part shows his own words and times).
4. Answer in the message, plain words, short: what was decided, when, who (the owner, or the assistant). Anything marked
   as the assistant's own note was its idea, not his rule: say so. If a decision was replaced, say what replaced it and
   that the old one is history. Times 12-hour.
5. Reason only from what memory shows. If memory has the decision but no reason, say "I have the decision but not why". If
   nothing is found, say "no record". Never guess a reason.

## Done when

The answer cites what memory holds (dates, who) and nothing else. Send it through the chat client as usual.
