---
name: second-opinion
description: Independent check of work made by another model (a coding agent, a chat assistant, a future local model), so nothing grades itself. Use when the owner says "second opinion", "check the other model's work", "is this right", or sends output plus the maker's own report. Never use it on the assistant's own work; say so and suggest another model checks it instead.
---

# Second Opinion

Master brief, section 11: "The system that creates a candidate cannot alter or grade itself." One earlier run had a chat
model write an adventure and also audit it. This skill is the fix. A different model does the checking.

## Steps

1. **Who made it?** If the assistant (this seat) made it, stop. Tell the owner it can't fairly grade its own work and
   suggest another model review it.
2. **Read the work before the maker's claims.** Read the artifact itself first: code, PDF, data. Only then read the
   maker's report or summary, and compare.
3. **Re-check the claims that matter.** Run the tests yourself if there are tests. Recount numbers the report states.
   Open the files it says it changed. A claim you couldn't check gets marked "not checked", never "true".
4. **Look for what self-review misses:**
   - defects the maker's own checks can't see (layout, art, tone, leaked internal text)
   - places the maker graded generously
   - places the maker changed the rules to pass, such as raised limits, skipped tests or loosened checks
5. **Report.** It's short in the message: agree, partly agree or disagree, plus the top disagreements. Send a PDF via the
   devil renderer when the review is long. Grade it 1-10 only if the owner asks.
6. **Save** real disagreements to memory under the project (`--layer project`) so the next run of that maker can be
   checked against them.

## Rules

- Be fair both ways. Confirming good work is a valid result, and don't invent problems to look independent.
- Quote the work, don't paraphrase it, when you disagree.
- On the future box the same rule applies: the writer model and the judge model are never the same.
