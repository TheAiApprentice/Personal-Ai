"""Decision Log: every decision the owner made, with dates, newest first. "What did I decide about X?"

    python tools/memory/decisions.py                       all live decisions
    python tools/memory/decisions.py clock                 decisions about a topic (words, any order)
    python tools/memory/decisions.py --project demo        only one project
    python tools/memory/decisions.py --history clock       include replaced decisions, marked REPLACED
    python tools/memory/decisions.py --plain --history X   one plain line each: when, who decided, what, replaced by
    python tools/memory/decisions.py --html out.html       the whole log as one HTML page

A decision is a memory that is tagged decision or rule, or is in the user layer, or says the owner
said / picked / decided / chose / wants / approved / paused. Read straight from the memory db;
nothing is copied, so the log can't drift from memory. New decisions should be saved with
--tags decision.
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
import mem  # noqa: E402

SAYS = re.compile(r"\b(?:owner|user)\b[^.]{0,40}\b(said|says|picked|decided|decision|chose|wants|approved|paused|resumed|answers?"
                  r"|never asked|does not|doesn't|is not|isn't|questioned)\b"
                  r"|\bdecisions?\b|\bon hold\b|\bskipped\b", re.I)


def is_decision(r) -> bool:
    tags = f",{r['tags']},"
    return ",decision," in tags or ",rule," in tags or r["layer"] == "user" or bool(SAYS.search(r["content"]))


def decisions(topic: str | None = None, project: str | None = None, history: bool = False) -> list:
    con = mem.connect()
    statuses = ("trusted", "uncertain", "deprecated") if history else ("trusted", "uncertain")
    sql = f"SELECT * FROM memories WHERE status IN ({','.join('?' * len(statuses))})"
    params = list(statuses)
    if project:
        sql += " AND project_id=?"; params.append(project)
    rows = [r for r in con.execute(sql + " ORDER BY id DESC", params).fetchall() if is_decision(r)]
    if topic:
        words = [w.lower() for w in re.findall(r"\w+", topic)]
        rows = [r for r in rows if all(w in (r["content"] + " " + r["tags"]).lower() for w in words)]
    return rows


def where(r) -> str:
    return r["project_id"] or ("you" if r["layer"] == "user" else r["layer"])


def text_lines(rows) -> list[str]:
    out = []
    for r in rows:
        flag = " REPLACED" if r["status"] == "deprecated" else ""
        out.append(f"#{r['id']} {mem.est(r['created_at'])} [{where(r)}]{flag} {r['content']}")
    return out


def to_html(rows, out: Path, title: str) -> None:
    by_proj: dict[str, list] = {}
    for r in rows:
        by_proj.setdefault(where(r), []).append(r)
    parts = [f"<!doctype html><html><head><meta charset='utf-8'><title>Decision Log</title><style>"
             "@page{size:Letter;margin:0.6in}body{font-family:'Segoe UI',Arial,sans-serif;font-size:10.5pt;line-height:1.4;color:#1d1d1f}"
             "h1{font-size:19pt;margin:0}h2{font-size:12.5pt;color:#2b5797;border-bottom:2px solid #2b5797;margin:16px 0 6px}"
             ".d{margin:0 0 7px}.when{color:#666;font-size:9pt}.rep{color:#999;text-decoration:line-through}</style></head><body>",
             f"<h1>{html.escape(title)}</h1><p class='when'>{len(rows)} decisions, newest first, grouped by project. "
             "Straight from the agent's memory.</p>"]
    for proj in sorted(by_proj):
        parts.append(f"<h2>{html.escape(proj)}</h2>")
        for r in by_proj[proj]:
            cls = " rep" if r["status"] == "deprecated" else ""
            parts.append(f"<div class='d{cls}'><span class='when'>{mem.est(r['created_at'])} (#{r['id']})</span><br>"
                         f"{html.escape(r['content'])}</div>")
    parts.append("</body></html>")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(parts), encoding="utf-8")
    print(f"wrote {out} ({len(rows)} decisions)")
    sys.exit(0)


def who_decided(r) -> str:
    """The owner's own words are saved as 'Owner (...)' or in the user layer; anything else is the agent's note."""
    if r["layer"] == "user" or r["content"].lstrip().startswith("Owner"):
        return "Owner"
    return "me (my note or idea, not a rule from the owner)"


def plain_lines(rows) -> list[str]:
    """Short plain-text answer for a DM: when (EST, 12-hour), who, what, and what replaced it."""
    out = []
    for r in rows:
        line = f"{mem.est(r['created_at'])} - {who_decided(r)}: {r['content']} (#{r['id']})"
        if r["status"] == "deprecated":
            line += f" REPLACED ({r['status_reason'] or 'no reason saved'})"
        out.append(line)
    return out


def main():
    ap = argparse.ArgumentParser(prog="decisions", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("topic", nargs="*")
    ap.add_argument("--project"); ap.add_argument("--history", action="store_true"); ap.add_argument("--html")
    ap.add_argument("--plain", action="store_true", help="one plain line per decision: when, who, what, replaced by")
    a = ap.parse_args()
    topic = " ".join(a.topic) or None
    rows = decisions(topic, a.project, a.history)
    if a.html:
        to_html(rows, Path(a.html), "Decision Log" + (f": {topic}" if topic else ""))
    lines = plain_lines(rows) if a.plain else text_lines(rows)
    if rows:
        print("\n".join(lines))
    elif a.plain:
        print("No record" + (f" of a decision about '{topic}'." if topic else "."))
    else:
        print("No decisions found" + (f" about '{topic}'." if topic else "."))



if __name__ == "__main__":
    main()
