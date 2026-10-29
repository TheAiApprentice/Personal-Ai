"""Privacy scan: walk a folder and fail if anything private could be inside it.

    python tools/privacy_scan.py .            scan the folder (exit 0 = clean, 1 = findings, 2 = bad usage)
    python tools/privacy_scan.py . --quiet    findings only, no summary line

What it looks for, in every text file:
  path         a drive-lettered path, a user-profile or home-folder path
  name         the owner's personal name or an e-mail address
  chat-id      a 17-20 digit number (chat user / bot / channel ids look like this)
  ip           an IPv4 address
  token        an API key or token shape (sk-..., AIza..., ghp_..., xox?-..., JWT, bot tokens,
               key = "long secret" assignments, 40+ character hex strings)
  wallet       a Bitcoin or Ethereum wallet address shape
  system-name  the capitalised names of two outside systems this repo must not describe
  system-term  words that point at an outside system (see PATTERNS); generic phrases listed in
               ALLOWED_PHRASES are allow-listed and shown as WARN
and by file name (a .pdf is skipped: it is rendered from an .html that is scanned):
  db           a database file (.db .sqlite .sqlite3)
  backup       a .bak file or a name containing .bak-
  image        an image file (.png .jpg .jpeg .gif .webp .bmp .ico .tif .tiff .svg)
A __pycache__ folder or .pyc file is only a WARNING (a test run makes them; see .gitignore).

The patterns are written so this file does not match itself. Standard library only; reads files
under the folder you give it and nothing else.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

TEXT_EXT = {".py", ".md", ".json", ".html", ".htm", ".txt", ".toml", ".yml", ".yaml", ".cfg", ".ini", ".csv",
            ".js", ".css", ".ps1", ".sh", ".bat", ".gitignore", ""}
BINARY_OK = {".pdf"}      # rendered from a scanned .html next to it (the review packet); content not readable as text
DB_EXT = {".db", ".sqlite", ".sqlite3"}
IMG_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".tif", ".tiff", ".svg"}
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", "node_modules"}

NAME = "[Zz]ach" + "(?:n|ary)?"   # the owner's name and handle, built in pieces so this file stays clean

PATTERNS = [
    ("path", re.compile(r"\b[A-Za-z]:[\\/]")),
    ("path", re.compile(r"(?<![\w.])[\\/]Users[\\/]")),
    ("path", re.compile(r"(?<![\w.])/home/[A-Za-z0-9_.-]+")),
    ("name", re.compile(r"\b" + NAME + r"\b")),
    ("name", re.compile(r"[\w.+-]+@[\w-]+\.[A-Za-z]{2,}")),
    ("chat-id", re.compile(r"(?<![\w.])\d{17,20}(?![\w.])")),
    ("ip", re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])")),
    ("token", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}")),
    ("token", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}")),
    ("token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}")),
    ("token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("token", re.compile(r"\beyJ[\w-]{10,}\.[\w-]{10,}\.[\w-]{10,}")),
    ("token", re.compile(r"\b[MNO][A-Za-z0-9_-]{23,27}\.[A-Za-z0-9_-]{6,7}\.[A-Za-z0-9_-]{27,}")),
    ("token", re.compile(r"(?i)\b(?:api[_-]?key|token|secret|password|passwd)\b\s*[:=]\s*['\"][A-Za-z0-9_\-+/=]{16,}['\"]")),
    ("token", re.compile(r"\b[0-9a-fA-F]{40,}\b")),
    ("wallet", re.compile(r"\b0x[a-fA-F0-9]{40}\b")),
    ("wallet", re.compile(r"\bbc1[ac-hj-np-z02-9]{20,80}\b")),
    ("wallet", re.compile(r"(?<![\w-])[13][a-km-zA-HJ-NP-Z1-9]{25,34}(?![\w-])")),
    ("system-name", re.compile(r"\b[C]ore\b|\b[C]ORE\b")),
    ("system-name", re.compile(r"[d]iscord", re.I)),
    # names and details of an outside system this repo must not describe (case-insensitive)
    ("system-term", re.compile(r"\b[p]ipeline\b|\b[C]odex\b|\b[s]upervisor\b|\b[F]allen\s+[S]torie\b|\b[p]m2\b"
                               r"|\b[w]atchdog\b|\b818[89]\b|\b[p]ython\.exe\b", re.I)),
]

# Generic, legitimate uses of the system terms. A match that sits inside one of these exact phrases is a
# WARNING (listed, never silent); anything else is a finding. Matched case-insensitively.
ALLOWED_PHRASES = [
    "powershell pipeline", "render pipeline", "data pipeline", "stop-process pipeline", "build pipeline",
    "taskkill /im python.exe", "/im python.exe",
]
_ALLOWED_RX = re.compile("|".join(re.escape(p) for p in ALLOWED_PHRASES), re.I)


def classify_file(path: Path) -> str | None:
    n = path.name.lower()
    ext = path.suffix.lower()
    if ext in DB_EXT:
        return "db"
    if ext == ".bak" or ".bak-" in n or n.endswith(".bak"):
        return "backup"
    if ext in IMG_EXT:
        return "image"
    return None


def scan_text(text: str):
    """-> list of (line number, kind, snippet) for one file's text."""
    out = []
    for no, line in enumerate(text.splitlines(), 1):
        for kind, rx in PATTERNS:
            if kind == "system-term":
                # blank out allow-listed phrases; whatever still matches is a finding, the rest a warning
                rest = _ALLOWED_RX.sub(lambda mm: " " * len(mm.group(0)), line)
                m = rx.search(rest)
                if m:
                    lo = max(0, m.start() - 15)
                    out.append((no, kind, line[lo:m.end() + 15].strip()[:80]))
                elif rx.search(line):
                    m = rx.search(line)
                    lo = max(0, m.start() - 15)
                    out.append((no, "warn:" + kind, line[lo:m.end() + 15].strip()[:80]))
                continue
            m = rx.search(line)
            if m:
                lo = max(0, m.start() - 15)
                out.append((no, kind, line[lo:m.end() + 15].strip()[:80]))
    return out


def scan(root: Path):
    """-> (findings, warnings, files_scanned). findings: (relative path, line, kind, snippet)."""
    findings, warnings, n = [], [], 0
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root).as_posix()
        parts = set(p.relative_to(root).parts)
        if "__pycache__" in parts or p.suffix == ".pyc":
            if p.is_file():
                warnings.append(f"{rel}: compiled/cache file (ignored by .gitignore)")
            continue
        if parts & (SKIP_DIRS - {"__pycache__"}):
            continue
        if not p.is_file():
            continue
        kind = classify_file(p)
        if kind:
            findings.append((rel, 0, kind, "file type not allowed in the repo"))
            continue
        if p.suffix.lower() in BINARY_OK:
            continue
        if p.suffix.lower() not in TEXT_EXT:
            findings.append((rel, 0, "file-type", "unknown file type, not scanned: add it to TEXT_EXT or remove it"))
            continue
        n += 1
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            findings.append((rel, 0, "file-type", "not valid UTF-8 text"))
            continue
        for no, k, snip in scan_text(text):
            if k.startswith("warn:"):
                warnings.append(f"{rel}:{no}: allow-listed {k[5:]}: {snip}")
            else:
                findings.append((rel, no, k, snip))
    return findings, warnings, n


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)
    root = Path(a.folder).resolve()
    if not root.is_dir():
        print(f"not a folder: {a.folder}", file=sys.stderr)
        return 2
    findings, warnings, n = scan(root)
    for rel, no, kind, snip in findings:
        print(f"{rel}:{no}: {kind}: {snip}" if no else f"{rel}: {kind}: {snip}")
    cache_w = [w for w in warnings if "allow-listed" not in w]
    for w in warnings:
        if "allow-listed" in w:
            print(f"WARN {w}")
    for w in cache_w[:5]:
        print(f"WARN {w}")
    if len(cache_w) > 5:
        print(f"WARN ... and {len(cache_w) - 5} more cache files")
    if not a.quiet:
        print(f"privacy scan: {n} text files scanned, {len(findings)} finding(s), {len(warnings)} warning(s)"
              f" -> {'FAIL' if findings else 'PASS'}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
