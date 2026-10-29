"""Smoke test for check.py: it runs inside this repo and prints OK/SKIP/WARN per part, nothing BROKEN.

It uses --fast (no nested test runs) and a throwaway home folder and memory database in a temp
dir, so nothing outside this repo is read or written.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

CHECK = Path(__file__).resolve().parent / "check.py"
REPO = CHECK.parents[2]
STATUS = re.compile(r"^(OK|SKIP|WARN)\s+\S")


def run_check(tmp_path, *args):
    env = dict(os.environ, AI_MEMORY_DB=str(tmp_path / "smoke.db"), HOME=str(tmp_path), USERPROFILE=str(tmp_path))
    return subprocess.run([sys.executable, str(CHECK), "--fast", *args], capture_output=True, text=True,
                          env=env, cwd=str(tmp_path), timeout=300)


def test_prints_ok_or_skip_per_part(tmp_path):
    p = run_check(tmp_path)
    assert p.returncode == 0, p.stdout + p.stderr
    lines = [l for l in p.stdout.splitlines() if l.strip() and not l.startswith(("ALL OK", "("))]
    assert len(lines) >= 6
    for l in lines:
        assert STATUS.match(l), l
    for part in ("guard hook", "junk chars", "pointers", "memory:", "skills", "skill index"):
        assert any(part in l for l in lines), part
    assert "BROKEN" not in p.stdout
    assert "ALL OK" in p.stdout


def test_json_mode_and_no_outside_paths(tmp_path):
    p = run_check(tmp_path, "--json")
    assert p.returncode == 0, p.stdout + p.stderr
    data = json.loads(p.stdout)
    assert data["ok"] is True
    assert all(r["status"] in ("OK", "SKIP", "WARN") for r in data["results"])
    # the report names no absolute path, so nothing outside the repo was read
    assert str(REPO) not in p.stdout and str(tmp_path) not in p.stdout


def test_memory_check_leaves_no_database_in_repo(tmp_path):
    run_check(tmp_path)
    assert not (REPO / "data").exists()
    assert not list(REPO.rglob("*.db"))
