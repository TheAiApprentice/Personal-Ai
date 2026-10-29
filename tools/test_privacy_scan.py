"""Tests for privacy_scan.py. Every bad sample is built from pieces at run time, so this file itself stays clean."""
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SCAN = HERE / "privacy_scan.py"
REPO = HERE.parent
sys.path.insert(0, str(HERE))
import privacy_scan as ps  # noqa: E402

BAD = {
    "path": "see " + "C" + ":" + "\\" + "stuff" + "\\" + "file.txt",
    "path-home": "open /" + "home" + "/someone/notes",
    "name": "written by " + "Za" + "ch",
    "email": "mail me at a" + "@" + "example.com",
    "chat-id": "channel " + "1" * 18,
    "ip": "host " + ".".join(["192", "168", "1", "20"]),
    "token-sk": "key " + "sk" + "-" + "A" * 30,
    "token-assign": 'api_key = "' + "abcd1234" * 3 + '"',
    "token-hex": "digest " + "ab12" * 12,
    "wallet-eth": "pay 0" + "x" + "a1" * 20,
    "wallet-btc": "send to bc" + "1" + "q" * 38,
    "system": "the " + "Co" + "re system",
    "term-a": "the " + "pipe" + "line is busy",
    "term-b": "ask " + "Cod" + "ex",
    "term-c": "the " + "super" + "visor restarts it",
    "term-fallen": "Fall" + "en Stor" + "ie",
    "term-e": "run " + "pm" + "2 list",
    "term-f": "a " + "watch" + "dog",
    "term-port1": "port " + "81" + "88",
    "term-port2": "port " + "81" + "89",
    "term-exe": "runs as " + "python" + ".exe",
    "term-upper": "the " + "PIPE" + "LINE",
    "chat-service": "uses " + "Dis" + "cord",
}


def run(folder):
    return subprocess.run([sys.executable, str(SCAN), str(folder)], capture_output=True, text=True, timeout=60)


def test_clean_folder_passes(tmp_path):
    (tmp_path / "a.md").write_text("Plain text about building with AI.\nVersion 1.2.3 is fine.\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("x = 'relative/path.txt'\n", encoding="utf-8")
    p = run(tmp_path)
    assert p.returncode == 0 and "PASS" in p.stdout


@pytest.mark.parametrize("name", sorted(BAD))
def test_each_private_shape_is_found(tmp_path, name):
    (tmp_path / "x.md").write_text("line one\n" + BAD[name] + "\nline three\n", encoding="utf-8")
    p = run(tmp_path)
    assert p.returncode == 1, p.stdout
    assert "x.md:2:" in p.stdout


@pytest.mark.parametrize("fname", ["data.db", "store.sqlite", "notes.bak", "file.txt.bak-20261001", "pic.png", "shot.JPG",
                                   "logo.svg"])
def test_forbidden_file_types_fail(tmp_path, fname):
    (tmp_path / fname).write_bytes(b"x")
    p = run(tmp_path)
    assert p.returncode == 1 and fname in p.stdout


@pytest.mark.parametrize("phrase", ["a PowerShell " + "pipe" + "line", "the render " + "pipe" + "line", "a data " + "pipe" + "line"])
def test_generic_pipeline_phrases_are_warnings_not_silent(tmp_path, phrase):
    (tmp_path / "x.md").write_text("intro\n" + phrase + " here\n", encoding="utf-8")
    p = run(tmp_path)
    assert p.returncode == 0 and "WARN" in p.stdout and "x.md:2" in p.stdout


def test_allowed_phrase_does_not_hide_a_real_term_on_the_same_line(tmp_path):
    (tmp_path / "x.md").write_text("a data " + "pipe" + "line and the " + "super" + "visor\n", encoding="utf-8")
    assert run(tmp_path).returncode == 1


def test_port_numbers_inside_longer_numbers_are_ignored(tmp_path):
    (tmp_path / "x.md").write_text("size 28" + "188" + " bytes, id 81" + "881\n", encoding="utf-8")
    assert run(tmp_path).returncode == 0


def test_pycache_is_only_a_warning(tmp_path):
    (tmp_path / "ok.md").write_text("fine\n", encoding="utf-8")
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "m.cpython-312.pyc").write_bytes(b"\0")
    p = run(tmp_path)
    assert p.returncode == 0 and "WARN" in p.stdout


def test_the_repo_itself_is_clean():
    findings, _warnings, n = ps.scan(REPO)
    assert findings == [], findings[:5]
    assert n > 40


def test_bad_folder_is_a_usage_error(tmp_path):
    assert run(tmp_path / "missing").returncode == 2
