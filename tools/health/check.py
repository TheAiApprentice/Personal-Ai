"""Health Check: one command that tests every part of this repo and says OK or BROKEN per part.

    python tools/health/check.py            all checks, one line each, exit 1 if anything is broken
    python tools/health/check.py --fast     skip the slow test suites (files, pointers, memory, skills only)
    python tools/health/check.py --json     machine-readable result

Checks (each prints OK, WARN, SKIP, KNOWN or BROKEN):
  guard hook   the guard refuses a banned command and lets a safe one through
  junk chars   no hidden control characters in code, docs or manifests (the shell can create them)
  pointers     every repo path the README files point to still exists
  memory       the memory database opens and the brief loads (on a throwaway database in a temp folder)
  skills       every skills/<name>/ has a SKILL.md and a valid manifest.json
  skill index  skills/README.md lists every skill
  memory dupes near-duplicate memories (SKIP when the default database does not exist)
  tests        every pytest suite in SUITES below (skipped with a note if the folder does not exist)

Everything is read from inside this repo; nothing outside it is opened.
Known failures (KNOWN below) are reported as KNOWN, not BROKEN, with the reason. Change that list
only when the reason is real and written down.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable

SUITES = {  # name -> test folder (skipped with a note if the folder does not exist)
    "guard hook": "tools/guard",
    "decision log": "tools/memory",
    "gpu mailbox": "tools/gpu_mailbox",
    "health check": "tools/health",
}

# test id fragment -> reason it fails for a reason outside the code (empty: nothing is excused)
KNOWN: dict[str, str] = {}

POINTER_FILES = ["README.md", "skills/README.md", "tools/gpu_mailbox/SKILL.md"]
TOP_DIRS = ("tools", "skills", "skills-repo")
JUNK_GLOBS = ["README.md", "tools/**/*.py", "tools/**/*.md", "skills/**/*.md", "skills/**/*.json",
              "skills/**/*.py"]
JUNK = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
MANIFEST_KEYS = ("id", "purpose", "permissions", "status")


def run(cmd, timeout=900, cwd=ROOT, env=None):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=timeout, env=env)
    return p.returncode, p.stdout + p.stderr


def check_suite(name, folder):
    path = ROOT / folder
    if not path.is_dir():
        return ("SKIP", f"{name} tests: no test folder yet")
    code, out = run([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(path)], cwd=path.parent)
    summary = next((l.strip(" =") for l in reversed(out.splitlines()) if re.search(r"\d+ (passed|failed|error)", l)),
                   "no summary")
    failed = re.findall(r"^(?:FAILED|ERROR) (\S+)", out, re.M)
    unknown = [f for f in failed if not any(k in f for k in KNOWN)]
    known = [f for f in failed if f not in unknown]
    if code == 0:
        return ("OK", f"{name} tests: {summary}")
    if failed and not unknown:
        why = "; ".join(sorted({KNOWN[k] for f in known for k in KNOWN if k in f}))
        return ("KNOWN", f"{name} tests: {summary} (all failures are known: {why})")
    if not failed:
        return ("BROKEN", f"{name} tests: could not run ({summary})")
    return ("BROKEN", f"{name} tests: {summary}; new failures: {', '.join(f.split('::')[-1] for f in unknown)}")


def check_skills():
    folders = sorted(p for p in (ROOT / "skills").glob("*") if p.is_dir())
    if not folders:
        return ("SKIP", "skills: no skills folder yet")
    bad = []
    for d in folders:
        if not (d / "SKILL.md").is_file():
            bad.append(f"{d.name}: no SKILL.md")
            continue
        try:
            m = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            bad.append(f"{d.name}: manifest.json missing or not valid JSON")
            continue
        miss = [k for k in MANIFEST_KEYS if k not in m]
        if miss:
            bad.append(f"{d.name}: manifest lacks {', '.join(miss)}")
        elif m["id"] != d.name:
            bad.append(f"{d.name}: manifest id is {m['id']}")
    if bad:
        return ("BROKEN", "skills: " + "; ".join(bad[:8]))
    return ("OK", f"skills: {len(folders)} skills, each with a SKILL.md and a valid manifest.json")


def check_index():
    readme = ROOT / "skills" / "README.md"
    if not readme.is_file():
        return ("SKIP", "skill index: no skills/README.md yet")
    text = readme.read_text(encoding="utf-8")
    names = [p.name for p in (ROOT / "skills").glob("*") if p.is_dir()]
    missing = [n for n in names if f"`{n}`" not in text]
    if missing:
        return ("BROKEN", f"skill index: skills/README.md does not list {', '.join(sorted(missing)[:8])}")
    return ("OK", f"skill index: skills/README.md lists all {len(names)} skills")


def check_memory():
    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ, AI_MEMORY_DB=str(Path(tmp) / "health.db"))
        code, out = run([PY, "tools/memory/mem.py", "brief", "--recent", "1"], env=env)
    if code == 0 and "===" in out:
        return ("OK", "memory: a fresh database is created by the code and the brief loads")
    return ("BROKEN", f"memory: brief failed ({out.strip().splitlines()[-1] if out.strip() else 'no output'})")


def pointer_targets(text):
    for tok in re.findall(r"`([^`\s]+)`", text):
        tok = tok.strip().rstrip(".,:;)")
        norm = tok.replace("\\", "/")
        if any(c in norm for c in "<>*{}$|") or norm.startswith(("http", "-", "/")):
            continue
        if norm.split("/")[0] in TOP_DIRS and "/" in norm:
            yield tok, norm


def check_pointers():
    missing = []
    for pattern in POINTER_FILES:
        for f in ROOT.glob(pattern):
            text = f.read_text(encoding="utf-8", errors="replace")
            for tok, norm in pointer_targets(text):
                # a path may be written from the repo root or from the file's own folder
                if not ((ROOT / norm).exists() or (f.parent / norm).exists()):
                    missing.append(f"{f.relative_to(ROOT).as_posix()} -> {tok}")
    if missing:
        return ("BROKEN", "pointers: " + str(len(missing)) + " missing: " + "; ".join(sorted(set(missing))[:12]))
    return ("OK", "pointers: every path the README files point to exists")


def _words(text):
    return {w for w in re.findall(r"[a-z0-9]{3,}", text.lower())}


def check_memory_dupes(threshold=0.6):
    """Live memories in the same layer/project/seat that say nearly the same thing: one should supersede the other."""
    import sqlite3
    db = Path(os.environ.get("AI_MEMORY_DB", ROOT / "data" / "memory.db"))
    if ROOT not in db.resolve().parents:
        return ("SKIP", "memory dupes: database is outside this repo, not read")
    if not db.exists():
        return ("SKIP", "memory dupes: no database")
    con = sqlite3.connect(db); con.row_factory = sqlite3.Row
    rows = con.execute("SELECT id, layer, project_id, seat_id, content FROM memories "
                       "WHERE status IN ('trusted','uncertain')").fetchall()
    groups = {}
    for r in rows:
        groups.setdefault((r["layer"], r["project_id"], r["seat_id"]), []).append((r["id"], _words(r["content"])))
    pairs = []
    for items in groups.values():
        for i, (a, wa) in enumerate(items):
            for b, wb in items[i + 1:]:
                if wa and wb and len(wa & wb) / len(wa | wb) >= threshold:
                    pairs.append(f"#{a}/#{b}")
    if pairs:
        return ("WARN", f"memory dupes: {len(pairs)} near-duplicate pair(s) to merge with --supersedes: {', '.join(pairs[:10])}")
    return ("OK", f"memory dupes: none among {len(rows)} live memories")


def check_guard():
    """The guard hook: one deny and one pass sample come out right."""
    guard = ROOT / "tools" / "guard" / "guard.py"
    if not guard.is_file():
        return ("BROKEN", "guard hook: tools/guard/guard.py is missing")

    def ask(cmd):
        p = subprocess.run([PY, str(guard)], input=json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}}),
                           capture_output=True, text=True, timeout=20)
        return p.returncode, p.stdout
    try:
        c1, deny = ask("taskkill /IM chrome.exe /F")
        c2, ok = ask("taskkill /PID 1234 /F")
    except Exception as e:
        return ("BROKEN", f"guard hook: could not run guard.py ({e})")
    if c1 != 0 or '"permissionDecision": "deny"' not in deny:
        return ("BROKEN", "guard hook: a banned command was not refused")
    if c2 != 0 or ok.strip():
        return ("BROKEN", "guard hook: a safe command was refused")
    return ("OK", "guard hook: refuses a banned command, lets a safe one through")


def check_junk():
    bad = []
    for pattern in JUNK_GLOBS:
        for f in ROOT.glob(pattern):
            if "__pycache__" in f.parts or "node_modules" in f.parts or not f.is_file():
                continue
            text = f.read_text(encoding="utf-8", errors="replace")
            for i, line in enumerate(text.splitlines(), 1):
                if JUNK.search(line):
                    bad.append(f"{f.relative_to(ROOT).as_posix()}:{i}")
    if bad:
        return ("BROKEN", f"junk chars: hidden control characters at {', '.join(sorted(set(bad))[:12])}")
    return ("OK", "junk chars: none in code, docs or manifests")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fast", action="store_true", help="skip the test suites")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    results = [check_guard(), check_junk(), check_pointers(), check_memory(), check_skills(), check_index(),
               check_memory_dupes()]
    if not args.fast:
        results += [check_suite(n, f) for n, f in SUITES.items()]
    broken = [r for r in results if r[0] == "BROKEN"]
    if args.json:
        print(json.dumps({"ok": not broken, "results": [{"status": s, "detail": d} for s, d in results]}, indent=1))
    else:
        for s, d in results:
            print(f"{s:6} {d}")
        print(f"\n{'ALL OK' if not broken else f'{len(broken)} BROKEN'} "
              f"({sum(r[0] == 'OK' for r in results)} ok, {sum(r[0] == 'WARN' for r in results)} to tidy, "
              f"{sum(r[0] == 'KNOWN' for r in results)} known, "
              f"{sum(r[0] == 'SKIP' for r in results)} skipped)")
    sys.exit(1 if broken else 0)


if __name__ == "__main__":
    main()
