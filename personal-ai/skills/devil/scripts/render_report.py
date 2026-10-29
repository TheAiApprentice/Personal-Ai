"""render_report.py -- turn a devil report (JSON) into a PDF for the owner.

    python render_report.py --data report.json --out "Report Name.pdf"

report.json shape (all text plain, no HTML -- it is escaped):
{
  "title": "What is being devil'd",
  "subtitle": "one line: what it is, what was read",
  "overall_score": 4,                 # 1-10
  "verdict": "two or three blunt sentences",
  "areas": [                          # 3-10 areas, each graded 1-10
    {"name": "Characters", "score": 2,
     "wrong": ["blunt weakness", "..."],
     "improve": ["concrete detailed fix", "..."]}
  ],
  "keep": ["what is genuinely good -- optional, short"],
  "priority": ["first thing to fix", "second", "..."],
  "not_checked": "what the review could not see (optional)"
}

Renders with headless Edge (or Chrome), then checks the PDF exists, is not tiny,
and -- when pdftotext is available -- that the overall score text is in it.
Prints RENDERED <path> <bytes> on success; exits non-zero otherwise.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

def _browsers() -> tuple:
    """Edge or Chrome: the usual install folders (from the environment), then whatever is on PATH."""
    out = []
    for var in ("ProgramFiles(x86)", "ProgramFiles"):
        base = os.environ.get(var)
        if base:
            out.append(os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe"))
            out.append(os.path.join(base, "Google", "Chrome", "Application", "chrome.exe"))
    for name in ("msedge", "chrome", "google-chrome", "chromium"):
        found = shutil.which(name)
        if found:
            out.append(found)
    return tuple(out)


BROWSERS = _browsers()

SCALE = [
    (10, "Ready to ship"),
    (8, "Strong -- small fixes"),
    (6, "Decent -- real work needed"),
    (4, "Weak -- big problems"),
    (1, "Not usable yet"),
]


def band(score: int) -> str:
    for floor, label in SCALE:
        if score >= floor:
            return label
    return SCALE[-1][1]


def colour(score: int) -> str:
    return "#1f7a3a" if score >= 8 else "#9a6b00" if score >= 6 else "#b3471d" if score >= 4 else "#9b1c1c"


def esc(s) -> str:
    return html.escape(str(s or ""))


def ul(items) -> str:
    items = [i for i in (items or []) if str(i).strip()]
    return "<ul>" + "".join(f"<li>{esc(i)}</li>" for i in items) + "</ul>" if items else ""


def check(data: dict) -> list[str]:
    errs = []
    if not str(data.get("title", "")).strip():
        errs.append("title is required")
    s = data.get("overall_score")
    if not isinstance(s, int) or not 1 <= s <= 10:
        errs.append("overall_score must be a whole number 1-10")
    areas = data.get("areas") or []
    if len(areas) < 3:
        errs.append("give at least 3 graded areas")
    for a in areas:
        sc = a.get("score")
        if not isinstance(sc, int) or not 1 <= sc <= 10:
            errs.append(f"area {a.get('name')!r}: score must be a whole number 1-10")
        if sc is not None and isinstance(sc, int) and sc < 10 and not a.get("improve"):
            errs.append(f"area {a.get('name')!r}: scored under 10 but has no 'improve' items")
    if not data.get("priority"):
        errs.append("priority list is required")
    return errs


def build_html(d: dict) -> str:
    s = d["overall_score"]
    areas_html = ""
    for a in d["areas"]:
        sc = a["score"]
        areas_html += (
            f'<section class="area"><div class="ahead"><h3>{esc(a.get("name"))}</h3>'
            f'<span class="pill" style="background:{colour(sc)}">{sc}/10 &middot; {esc(band(sc))}</span></div>'
            + (f'<h4>What is wrong</h4>{ul(a.get("wrong"))}' if a.get("wrong") else "")
            + (f'<h4>What to improve</h4>{ul(a.get("improve"))}' if a.get("improve") else "")
            + "</section>"
        )
    grades = "".join(
        f'<li><b>{esc(a.get("name"))}</b> <span style="color:{colour(a["score"])}">{a["score"]}/10</span></li>'
        for a in d["areas"])
    rng = {10: "10", 8: "8-9", 6: "6-7", 4: "4-5", 1: "1-3"}
    scale = "".join(f"<li><b>{rng[f]}</b> {esc(l)}</li>" for f, l in SCALE)
    keep = f'<h2>What is already good</h2>{ul(d.get("keep"))}' if d.get("keep") else ""
    nc = f'<p class="nc"><b>Not checked:</b> {esc(d.get("not_checked"))}</p>' if d.get("not_checked") else ""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{esc(d['title'])}</title>
<style>
body{{font-family:Georgia,'Times New Roman',serif;color:#1d1d1f;background:#fff;max-width:760px;margin:36px auto;padding:0 16px;line-height:1.5;font-size:11pt}}
h1{{font-size:21pt;margin:0;color:#6b1d12}} .sub{{color:#555;margin:4px 0 16px}}
.score{{display:flex;align-items:center;gap:14px;border:2px solid {colour(s)};border-radius:10px;padding:10px 14px;margin:10px 0 6px}}
.big{{font-size:30pt;font-weight:bold;color:{colour(s)};line-height:1}} .band{{font-size:13pt;font-weight:bold}}
h2{{font-size:14pt;color:#6b1d12;border-bottom:1px solid #ddd;padding-bottom:2px;margin:22px 0 6px}}
h3{{font-size:12pt;margin:0}} h4{{font-size:10.5pt;margin:8px 0 2px;color:#333}}
.area{{border:1px solid #e3e3e3;border-radius:8px;padding:8px 12px;margin:10px 0;page-break-inside:avoid}}
.ahead{{display:flex;justify-content:space-between;align-items:center;gap:8px}}
.pill{{color:#fff;border-radius:12px;padding:2px 10px;font-size:9.5pt;white-space:nowrap}}
ul{{margin:3px 0 6px 20px;padding:0}} li{{margin:2px 0}} .cols{{display:flex;gap:28px}} .cols ul{{margin-left:18px}}
.nc{{color:#555;font-size:9.5pt;margin-top:18px}}
@media print{{body{{margin:0 auto}} h2,h3{{page-break-after:avoid}}}}
</style></head><body>
<h1>{esc(d['title'])}</h1><div class="sub">{esc(d.get('subtitle'))}</div>
<div class="score"><div class="big">{s}/10</div><div><div class="band">{esc(band(s))}</div><div>{esc(d.get('verdict'))}</div></div></div>
<div class="cols"><div><h4>Grades</h4><ul>{grades}</ul></div><div><h4>Scale</h4><ul>{scale}</ul></div></div>
<h2>Graded breakdown</h2>{areas_html}
{keep}
<h2>Fix in this order</h2><ol>{''.join(f'<li>{esc(p)}</li>' for p in d['priority'])}</ol>
{nc}
</body></html>"""


def render(html_path: str, pdf_path: str) -> None:
    browser = next((b for b in BROWSERS if os.path.exists(b)), None)
    if not browser:
        sys.exit("render_report: no Edge or Chrome found to print the PDF")
    prof = tempfile.mkdtemp(prefix="devil_pdf_")
    # Edge only writes the PDF when the path uses Windows backslashes
    out = os.path.normpath(os.path.abspath(pdf_path))
    url = "file:///" + os.path.normpath(os.path.abspath(html_path)).replace("\\", "/")
    subprocess.run([browser, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--user-data-dir={os.path.normpath(prof)}", f"--print-to-pdf={out}", url],
                   capture_output=True, timeout=120)
    for _ in range(40):                      # the browser can finish writing just after it exits
        if os.path.exists(out) and os.path.getsize(out) > 0:
            break
        time.sleep(0.5)
    shutil.rmtree(prof, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    data = json.load(open(a.data, encoding="utf-8"))
    errs = check(data)
    if errs:
        print("REPORT REFUSED:\n  " + "\n  ".join(errs))
        return 3
    if os.path.exists(a.out):
        print(f"REPORT REFUSED: {a.out} already exists (nothing is overwritten; pick a new name)")
        return 3
    html_path = os.path.splitext(a.out)[0] + ".html"
    open(html_path, "w", encoding="utf-8").write(build_html(data))
    render(html_path, a.out)
    if not os.path.exists(a.out) or os.path.getsize(a.out) < 5000:
        print(f"RENDER FAILED: {a.out} missing or too small")
        return 4
    if shutil.which("pdftotext"):
        txt = subprocess.run(["pdftotext", a.out, "-"], capture_output=True, text=True, errors="ignore").stdout
        if f"{data['overall_score']}/10" not in txt:
            print("RENDER CHECK FAILED: overall score not found in the PDF text")
            return 4
    print(f"RENDERED {a.out} {os.path.getsize(a.out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
