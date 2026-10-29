# Wipe rules

- Delete means the Windows Recycle Bin, never a permanent delete. The owner checks the bin and decides. Emptying the bin
  is his.
- One message from him is the order. When his words name the thing, move it in the same turn, no confirmation question.
  When they could mean more than one thing, list the candidates with full paths and let him pick; never guess, never pick
  for him.
- Literal paths only, found by listing the folder. Never a wildcard or a pattern: a glob delete once destroyed four
  finished videos that only shared the start of a name, and five folders with "cursed" in their names held one target.
- A similar name is not the same thing. Check each path is the one he means.
- Links and junctions are never followed or moved: a move through one can reach somewhere else.
- Before moving, prove the bin will keep it: Windows deletes permanently when the bin is set to delete on removal or the
  item is bigger than the bin.
- After moving, prove it: gone from disk AND listed in the bin. Only then call it done.
- Every term in his order gets a check: if he says "the old drafts from Tuesday", each path must be a draft, old, and from
  Tuesday.
- Never touch a protected system's folders (set `WIPE_PROTECTED`), the memory (`data/`) or secrets files.
