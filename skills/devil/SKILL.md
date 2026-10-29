---
name: devil
description: Red-team a specific artifact for the owner and deliver a graded PDF report - an overall 1-10 score, a 1-10 grade per area, the blunt case against it, and detailed fixes. Triggers on "/devil", "devil", "devil this", "/devil [artifact]", "red-team this", or when the owner sends a file, idea, plan, product, course or set of skills and says devil.
---

# Devil: Graded Red-Team Report (PDF)

## What This Does

Tears an artifact apart before it ships, then says exactly how to fix it. The owner's order: **"improve the devil skill to
send reports over in PDF, scale it 1-10, with grades on how the stuff is, and give what needs to improve, more detail the
better."**

Every devil run produces:
1. an **overall score 1-10** with a blunt two-to-three sentence verdict;
2. **3 to 10 graded areas**, each scored 1-10, each with *what is wrong* and *what to improve* (detailed, concrete);
3. a short *what is already good* list (only real strengths);
4. a **fix-in-this-order** priority list;
5. a *not checked* line naming anything the review could not see.

It goes to the owner as a **PDF attached to a message**, plus a short summary (score + the top 3 problems).

Devil is the owner thinking: it is not tied to any other project. Red-team the thing as he
framed it. No ledger, no agents, no installs, no follow-up offers.

## When To Use

- `/devil`, `devil this`, `devil [thing]`, "red-team this", or a message with a file and "devil".
- `/devil {N}` still means exactly N points in the summary; the PDF keeps its full graded breakdown.
- Do NOT invoke on your own. Only when asked.

## Process

### Step 1: Get the whole target
- A chat attachment: download it into the scratchpad with the chat client. Zips: unzip into a new folder. PDFs:
  `pdftotext -layout`.
- **Read all of it** (code too, not just its README) before grading. If a claim can be checked in the files, check it.
  Quote the artifact; never grade what you did not read.
- If unclear what is being devil'd, ask "devil what?" and stop.

### Step 2: Grade it
Pick 3-10 areas that matter for *this* thing (a product: content, usability, mechanics, layout, legal/store, price/value;
a plan: math, risk, cost, time, evidence; code/skills: correctness, enforcement, failure handling, claims vs reality).

Scale, used for the overall score and every area:
- **10** ready to ship
- **8-9** strong, small fixes
- **6-7** decent, real work needed
- **4-5** weak, big problems
- **1-3** not usable yet

Be honest both ways: a 9 is allowed if it is earned; do not grade down to seem tough.

### Step 3: Write the report data
Create a JSON file (see the `scripts/render_report.py` header for the exact shape): `title`, `subtitle`, `overall_score`,
`verdict`, `areas[{name, score, wrong[], improve[]}]`, `keep[]`, `priority[]`, `not_checked`.

Writing rules:
- **Plain words.** Short sentences, like talking to a person. Technical words only when the artifact is technical and the
  word is right.
- **Blunt in "wrong".** "This is wrong / this will not land", never "this might be a concern".
- **Detailed in "improve".** Each fix says what to change and how, specific enough to act on (numbers, names, examples).
  Every area under 10 must have at least one fix.
- **Real points only.** Never pad. Attack the artifact, never the person.
- **Facts you could not verify are labelled** (for example "from memory, not checked online").

### Step 4: Render and send
```
python skills/devil/scripts/render_report.py --data <report.json> --out "<scratchpad>/<Short_Title>_Devil_Report.pdf"
```
It refuses bad data (score not 1-10, fewer than 3 areas, an area under 10 with no fix, no priority list), never overwrites,
renders with headless Edge/Chrome and checks the score is in the PDF text. It prints `RENDERED <path> <bytes>`.

Then send it with the summary through your chat client, as a reply to his message. The summary must fit the chat's length
limit, with 12-hour times only. Say "sent" only after the attachment is verified. Summary: overall score and band, the
top 3 problems in one line each, "full report attached".

### Step 5: Stop
No "want me to fix it?" The owner decides. If he then asks for the fixes to be done, that is a separate job.

## What NOT To Do
- Don't grade from the README or the notes alone -- read the thing.
- Don't soften the verdict, and don't manufacture problems to look tough.
- Don't skip the PDF for a long review, and don't paste the whole report into the chat.
- Don't tie it to any other project unless the owner says so.

## Provenance note
This is an upgraded version of a red-team skill that came from an earlier skill (PDF report, 1-10 grades).
The delivery steps were rewritten for a generic chat client; the report format and `scripts/render_report.py` are
otherwise unchanged.
