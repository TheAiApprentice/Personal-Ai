"""Recall before acting: what already exists for a job or a message from the owner.

    python tools/memory/recall.py "make the weekly report like the last one"

Prints, in this order:
  SKILLS        skills whose id, purpose or triggers match (from skills/*/manifest.json)
  MEMORY        saved facts and decisions that match (live memories, best first)
  OWNER SAID    the owner's own past messages that match (raw chat archive), so an order that
                was never saved as a memory still turns up

Run it before any job and before answering a message that acts on something.
Read-only: it never writes memory (search() only touches last_used_at).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import mem  # noqa: E402

STOP = set("""a an the and or but if then than so to of in on at by for with from into onto up down out over
under about after before again also all any are as be been being both can could did do does doing done dont
each few had has have having he her here hers him his how i im ill ive is it its itll just me more most my no
nor not now off once only other our ours own same she should some such that thats their theirs them there these
they this those through too very was we were what when where which while who whom why will would you your
yours yes ok okay like get got go going make made want need let lets one two still even ever never every thing
things stuff really think know see said say tell told asked ask""".split())


def keywords(text: str, limit: int = 10) -> list[str]:
    words = re.findall(r"[a-z0-9][a-z0-9.\-]*", text.lower())
    out = []
    for w in words:
        w = w.strip(".-")
        if len(w) < 3 or w in STOP or w in out:
            continue
        out.append(w)
    return out[:limit]


def skills(words: list[str], limit: int = 5):
    hits = []
    for f in sorted((ROOT / "skills").glob("*/manifest.json")):
        try:
            m = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        hay = " ".join([m.get("id", ""), m.get("purpose", ""), " ".join(m.get("triggers", []))]).lower()
        score = sum(1 for w in words if w in hay)
        if score:
            hits.append((score, m.get("id", f.parent.name), m.get("purpose", "")))
    hits.sort(key=lambda h: -h[0])
    return hits[:limit]


def owner_said(con, words: list[str], limit: int = 5):
    if not words:
        return []
    rows = con.execute("SELECT at, content FROM archive WHERE direction='in' ORDER BY id DESC LIMIT 5000").fetchall()
    scored = []
    for r in rows:
        low = r["content"].lower()
        score = sum(1 for w in words if w in low)
        if score >= 1:  # one matching word is enough; best matches still sort first
            scored.append((score, r["at"], r["content"]))
    scored.sort(key=lambda s: (s[0], s[1]), reverse=True)  # best match first, newest first on ties
    return scored[:limit]


def recall(text: str, n_mem: int = 6, n_said: int = 5) -> str:
    words = keywords(text)
    if not words:
        return "RECALL: no keywords in that text."
    con = mem.connect()
    out = [f"RECALL for: {' '.join(words)}"]
    sk = skills(words)
    out.append("  SKILLS: " + ("; ".join(f"{s[1]} ({s[2][:90]})" for s in sk) if sk else "none match"))
    rows = mem.search(con, " ".join(words), limit=n_mem)
    out.append("  MEMORY:" + ("" if rows else " none match"))
    for r in rows:
        out.append(f"    #{r['id']} [{mem.est(r['created_at'])}] {r['content'][:260]}")
    said = owner_said(con, words, n_said)
    out.append("  OWNER SAID:" + ("" if said else " none match"))
    for _, at, content in said:
        out.append(f"    [{mem.est(at)}] {content[:200]}")
    return "\n".join(out)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        sys.exit('usage: recall.py "<the job or message>"')
    print(recall(" ".join(argv)))


if __name__ == "__main__":
    main()
