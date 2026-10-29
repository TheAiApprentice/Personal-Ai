"""Tests for decisions.py --plain. Uses a temp memory db, never brain/memory.db."""
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run(tmp_path, *args):
    env = dict(os.environ, AI_MEMORY_DB=str(tmp_path / "m.db"))
    return subprocess.run([sys.executable, str(HERE / "mem.py"), *args], capture_output=True, text=True, env=env), env


def decisions(tmp_path, *args):
    env = dict(os.environ, AI_MEMORY_DB=str(tmp_path / "m.db"))
    return subprocess.run([sys.executable, str(HERE / "decisions.py"), *args], capture_output=True, text=True, env=env)


def add(tmp_path, text, *extra):
    r, _ = run(tmp_path, "add", "--layer", "user", "--tags", "decision", *extra, "--text", text)
    assert r.returncode == 0, r.stderr
    return r.stdout


def test_plain_who_when_and_replaced(tmp_path):
    add(tmp_path, "Owner (Oct 10): clips are sped up 1.2x.")
    add(tmp_path, "Owner (Oct 11): clips are sped up 1.5x.", "--supersedes", "1")
    out = decisions(tmp_path, "--plain", "--history", "clips").stdout
    assert "Owner:" in out and "1.5x" in out and "REPLACED (superseded by #2)" in out
    assert " AM" in out or " PM" in out
    live = decisions(tmp_path, "--plain", "clips").stdout
    assert "1.2x" not in live


def test_plain_my_note_is_flagged(tmp_path):
    r, _ = run(tmp_path, "add", "--layer", "project", "--tags", "decision", "--text", "I chose to name the file foo.")
    assert r.returncode == 0, r.stderr
    out = decisions(tmp_path, "--plain", "foo").stdout
    assert "me (my note or idea, not a rule from the owner)" in out


def test_plain_no_record(tmp_path):
    out = decisions(tmp_path, "--plain", "zebra").stdout
    assert out.startswith("No record")
