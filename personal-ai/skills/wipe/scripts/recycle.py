"""recycle -- send named files or folders to the Windows Recycle Bin, safely and provably.

    python recycle.py --path "<literal absolute path>" [--path ...] --order-file <his words> [--execute]

The assistant's wipe: a Recycle Bin mover with gates.

Gates (each refuses with exit 3 and moves nothing):
  * the order file holds the owner's words (the result keeps them);
  * every --path is a literal, absolute path that exists -- no wildcard characters;
  * no path is a link or junction, and none sits inside a named folder;
  * no path is protected: a drive root, a Windows/Program Files/user-profile root, anything
    under a folder named in WIPE_PROTECTED (folders separated by the OS path separator; also
    siblings whose names start with the same text), the repo root or one of its top-level
    folders, the data/ folder (memory), or a secrets file;
  * the Recycle Bin can keep it: Windows deletes PERMANENTLY an item bigger than the bin, or
    when the bin is set to delete on removal, so those cases refuse.
Default is a dry run. --execute moves each path with SendToRecycleBin through a hidden
PowerShell (the path list travels in a JSON file, never on a command line), then proves every
path is gone from disk AND listed in the bin. Result JSON in data/wipes/ (inside the repo).
Never deletes permanently. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import struct
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
PAI = os.path.abspath(os.path.join(HERE, "..", "..", ".."))       # skills/wipe/scripts -> the repo root
STATE = os.path.join(PAI, "data", "wipes")
PROTECTED_PREFIXES = [os.path.normcase(os.path.abspath(p)) for p in
                      os.environ.get("WIPE_PROTECTED", "").split(os.pathsep) if p.strip()]
WILD = set("*?[]")
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
BIN_MARGIN = 0.90            # refuse when the move would fill more than this much of the bin
EXIT_REFUSED, EXIT_VERIFY = 3, 4
SECRET_NAMES = {"api.env", ".env", "config.json", "credentials.json", "token.json"}
PROTECTED_ROOTS = [os.path.expanduser("~")] + [
    os.environ[v] for v in ("WINDIR", "ProgramFiles", "ProgramFiles(x86)", "ProgramData") if os.environ.get(v)]
USER_FOLDERS = ("Desktop", "Documents", "Downloads", "Pictures", "Videos", "Music", "OneDrive", "AppData")


def norm(p):
    return os.path.normcase(os.path.abspath(p)).rstrip("\\/")


def inside(p, root):
    p, r = norm(p), norm(root)
    return p == r or p.startswith(r + os.sep)


def is_link(p):
    try:
        if os.path.islink(p):
            return True
        if getattr(os.path, "isjunction", None) and os.path.isjunction(p):
            return True
        return bool(getattr(os.lstat(p), "st_file_attributes", 0) & 0x400)   # reparse point
    except OSError:
        return False


def stamp():
    return time.strftime("%Y%m%d-%H%M%S")


def write_json_new(path, obj):
    """Create a NEW json file (never overwrite); -2, -3 ... if the name is taken."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    data = (json.dumps(obj, indent=1, ensure_ascii=False, default=str) + "\n").encode("utf-8")
    base, ext = os.path.splitext(path)
    cand, n = path, 1
    while True:
        try:
            fd = os.open(cand, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0))
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            return cand
        except FileExistsError:
            n += 1
            cand = "%s-%d%s" % (base, n, ext)


# ------------------------------------------------------------------ gates
def protected(a):
    """Why this absolute path must never be moved, or ''."""
    n = norm(a)
    if os.path.splitdrive(a)[1] in ("\\", "/", ""):
        return "a drive root"
    for pref in PROTECTED_PREFIXES:
        if n.startswith(pref):
            return "it is under a protected folder (WIPE_PROTECTED) -- the assistant never touches it"
    for r in PROTECTED_ROOTS:
        if r and n == norm(r):
            return "a system or user-profile root"
    home = os.path.expanduser("~")
    if os.path.dirname(n) == norm(home) and os.path.basename(a) in USER_FOLDERS:
        return "a top-level user folder (%s)" % os.path.basename(a)
    if n == norm(PAI):
        return "the repo root"
    if os.path.dirname(n) == norm(PAI):
        return "a top-level repo folder or file -- only things inside them"
    if inside(a, os.path.join(PAI, "data")):
        return "the memory (data/) -- memory is append-only"
    if os.path.basename(n) in SECRET_NAMES:
        return "a secrets/config file"
    # a folder that HOLDS something protected is refused too
    for inner in [os.path.join(PAI, "data")] + PROTECTED_PREFIXES:
        if inside(inner, a):
            return "it contains %s" % os.path.basename(inner)
    return ""


def gates(paths):
    bad = []
    for p in paths:
        if any(c in WILD for c in p):
            bad.append("%s: wildcard characters are not allowed" % p)
            continue
        if not os.path.isabs(p):
            bad.append("%s: not an absolute path" % p)
            continue
        a = os.path.abspath(p)
        if not os.path.lexists(a):
            bad.append("%s: does not exist" % p)
            continue
        why = protected(a)
        if why:
            bad.append("%s: %s" % (p, why))
        if is_link(a):
            bad.append("%s: is a link/junction" % p)
        elif os.path.isdir(a):
            for dp, dns, fns in os.walk(a):
                for n in dns + fns:
                    if is_link(os.path.join(dp, n)):
                        bad.append("%s: holds a link/junction %s" % (p, os.path.join(dp, n)))
                dns[:] = [d for d in dns if not is_link(os.path.join(dp, d))]
    seen = set()
    for p in paths:
        n = norm(p)
        if n in seen:
            bad.append("%s: listed twice" % p)
        seen.add(n)
        for q in paths:
            if q != p and inside(q, p) and norm(q) != n:
                bad.append("%s is inside %s: name only the outer one" % (q, p))
    return bad


# ------------------------------------------------------------------ the Recycle Bin
_PS_MOVE = r"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName Microsoft.VisualBasic
$raw = Get-Content -LiteralPath $env:WIPE_RECYCLE_LIST -Raw -Encoding UTF8
$items = ConvertFrom-Json -InputObject $raw
$out = @()
foreach ($p in $items) {
  $r = @{ path = [string]$p; ok = $false; error = '' }
  try {
    if (Test-Path -LiteralPath $p -PathType Container) {
      [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory($p, 'OnlyErrorDialogs', 'SendToRecycleBin', 'ThrowException')
    } elseif (Test-Path -LiteralPath $p -PathType Leaf) {
      [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile($p, 'OnlyErrorDialogs', 'SendToRecycleBin', 'ThrowException')
    } else { $r.error = 'not found' }
    if (-not (Test-Path -LiteralPath $p)) { $r.ok = $true }
  } catch { $r.error = $_.Exception.Message }
  $out += ,$r
}
ConvertTo-Json -InputObject $out -Compress
"""


def move_to_bin(paths, state_dir):
    """[{"path", "ok", "error"}] -- each path sent to the Recycle Bin by a hidden PowerShell."""
    lst = write_json_new(os.path.join(state_dir, "%s-recycle-list.json" % stamp()), list(paths))
    env = dict(os.environ, WIPE_RECYCLE_LIST=lst)
    r = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden",
                        "-Command", _PS_MOVE], capture_output=True, text=True, timeout=3600, stdin=subprocess.DEVNULL,
                       encoding="utf-8", errors="replace", env=env, creationflags=NO_WINDOW)
    text = (r.stdout or "").strip()
    try:
        data = json.loads(text.splitlines()[-1]) if text else []
    except ValueError:
        data = []
    data = [data] if isinstance(data, dict) else data
    by = {os.path.normcase(x.get("path", "")): x for x in data if isinstance(x, dict)}
    out = []
    for p in paths:
        x = by.get(os.path.normcase(p)) or {"ok": False, "error": "no answer from PowerShell (exit %s): %s"
                                            % (r.returncode, ((r.stderr or "") + text)[:300])}
        out.append({"path": p, "ok": bool(x.get("ok")), "error": str(x.get("error") or "")})
    return out


def _user_sid():
    r = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                        "[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value"],
                       capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL, creationflags=NO_WINDOW)
    sid = (r.stdout or "").strip()
    if not re.fullmatch(r"S-1-[0-9-]+", sid):
        raise RuntimeError("cannot read the user SID (%r)" % sid[:80])
    return sid


def _bin_dir(drive, sid):
    return "%s\\$Recycle.Bin\\%s" % (drive, sid)


def tree_size(path):
    """Bytes under a file or folder; never follows links."""
    if os.path.isfile(path) and not is_link(path):
        try:
            return os.path.getsize(path)
        except OSError:
            return 0
    total = 0
    for dp, dn, fn in os.walk(path):
        dn[:] = [d for d in dn if not is_link(os.path.join(dp, d))]
        for f in fn:
            try:
                total += os.lstat(os.path.join(dp, f)).st_size
            except OSError:
                pass
    return total


def bin_info(drives):
    """Bin capacity (MB) and delete-on-remove setting from the registry, and how much the user's
    own $Recycle.Bin already holds on each drive."""
    info = {"caps_mb": [], "nuke": False, "used": {}, "error": None}
    try:
        import winreg
        base = r"Software\Microsoft\Windows\CurrentVersion\Explorer\BitBucket"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, base) as k:
            try:
                info["nuke"] |= bool(winreg.QueryValueEx(k, "NukeOnDelete")[0])
            except OSError:
                pass
            with winreg.OpenKey(k, "Volume") as vols:
                i = 0
                while True:
                    try:
                        name = winreg.EnumKey(vols, i)
                    except OSError:
                        break
                    i += 1
                    with winreg.OpenKey(vols, name) as v:
                        for val in ("MaxCapacity", "NukeOnDelete"):
                            try:
                                x = winreg.QueryValueEx(v, val)[0]
                            except OSError:
                                continue
                            if val == "MaxCapacity":
                                info["caps_mb"].append(int(x))
                            else:
                                info["nuke"] |= bool(x)
        sid = _user_sid()
        for d in sorted(set(drives)):
            p = _bin_dir(d, sid)
            info["used"][d] = tree_size(p) if os.path.isdir(p) else 0
    except Exception as e:                         # noqa: BLE001
        info["error"] = "%s: %s" % (type(e).__name__, e)
    return info


def bin_problems(paths, info, sizes):
    """Reasons the bin would DELETE instead of keep (empty list = safe to send)."""
    if info.get("error"):
        return ["cannot read the Recycle Bin settings (%s), so cannot prove the move would not be a permanent "
                "delete" % info["error"]]
    bad = []
    if info.get("nuke"):
        bad.append("the Recycle Bin is set to delete files immediately (NukeOnDelete) -- a move would be permanent")
    caps = [c for c in info.get("caps_mb") or [] if c > 0]
    if not caps:
        return bad + ["no Recycle Bin capacity is recorded, so cannot prove the move would not be a permanent delete"]
    cap = min(caps) * 1024 * 1024
    per = {}
    for p in paths:
        d = os.path.splitdrive(os.path.abspath(p))[0].upper() or "?"
        per[d] = per.get(d, 0) + sizes[p]
    for d, n in sorted(per.items()):
        used = int((info.get("used") or {}).get(d, 0))
        if used + n > cap * BIN_MARGIN:
            bad.append("%s: this is %.2f GB and the bin already holds %.2f GB of its %.2f GB limit -- Windows "
                       "would permanently delete to make room" % (d, n / 2**30, used / 2**30, cap / 2**30))
    return bad


def _read_i_file(path):
    """(original_path, size) of a $I metadata file, version 1 or 2, or None."""
    try:
        with open(path, "rb") as f:
            b = f.read(4096)
        ver, size = struct.unpack("<qq", b[:16])
        if ver == 2:
            n = struct.unpack("<i", b[24:28])[0]
            name = b[28:28 + 2 * n].decode("utf-16le")
        else:
            name = b[24:24 + 520].decode("utf-16le")
        return name.split("\x00")[0], size
    except Exception:                              # noqa: BLE001
        return None


def in_bin(paths):
    """The subset of `paths` the Recycle Bin now lists as an original location (with its $R data
    still present), or None when the bin cannot be read."""
    try:
        sid = _user_sid()
        seen = set()
        for d in sorted({os.path.splitdrive(os.path.abspath(p))[0].upper() for p in paths}):
            b = _bin_dir(d, sid)
            if not os.path.isdir(b):
                continue
            names = os.listdir(b)
            for n in names:
                if n.startswith("$I"):
                    got = _read_i_file(os.path.join(b, n))
                    if got and any(x.startswith("$R" + n[2:]) for x in names):
                        seen.add(os.path.normcase(os.path.abspath(got[0])))
        return {p for p in paths if os.path.normcase(os.path.abspath(p)) in seen}
    except Exception:                              # noqa: BLE001
        return None


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description="Send named files/folders to the Windows Recycle Bin (dry run unless --execute).")
    ap.add_argument("--path", action="append", required=True, help="a literal absolute path (repeat for more)")
    ap.add_argument("--order-file", required=True, help="a file holding the owner's words, verbatim")
    ap.add_argument("--execute", action="store_true", help="really move them (default is a dry run)")
    a = ap.parse_args()
    try:
        order = open(a.order_file, encoding="utf-8").read().strip()
    except OSError as e:
        print("REFUSED: cannot read the order file (%s)" % e)
        return EXIT_REFUSED
    if not order:
        print("REFUSED: the order file is empty; it must hold the owner's words")
        return EXIT_REFUSED
    raw = list(a.path)
    bad = gates(raw)
    if bad:
        print("REFUSED (nothing moved):\n  " + "\n  ".join(bad))
        return EXIT_REFUSED
    paths = [os.path.abspath(p) for p in raw]
    sizes = {p: tree_size(p) for p in paths}
    for p in paths:
        print("PLAN %s (%s, %d bytes)" % (p, "folder" if os.path.isdir(p) else "file", sizes[p]))
    bad = bin_problems(paths, bin_info([os.path.splitdrive(p)[0].upper() for p in paths]), sizes)
    if bad:
        print("REFUSED (nothing moved):\n  " + "\n  ".join(bad))
        return EXIT_REFUSED
    if not a.execute:
        print("DRY RUN: nothing moved (add --execute)")
        return 0
    moved = move_to_bin(paths, STATE)
    gone = [p for p in paths if not os.path.lexists(p)]
    listed = in_bin(paths)
    result = {"schema": "personal_ai_recycle_v1", "at": time.strftime("%Y-%m-%dT%H:%M:%S"), "order": order,
              "paths": paths, "sizes": sizes, "moved": moved, "gone": gone,
              "in_bin": sorted(listed) if listed is not None else None}
    rp = write_json_new(os.path.join(STATE, "%s-recycle-result.json" % stamp()), result)
    for m in moved:
        print("%s %s %s" % ("RECYCLED" if m["ok"] else "FAILED", m["path"], m["error"]))
    if listed is None:
        print("IN BIN: could not read the Recycle Bin listing")
    else:
        print("IN BIN: %d of %d path(s) listed in the Recycle Bin" % (len(listed), len(paths)))
    print("RESULT %s" % rp)
    ok = len(gone) == len(paths) and listed is not None and set(paths) <= listed
    print("RECYCLE CLEAN" if ok else "RECYCLE NOT CLEAN -- check the result file")
    return 0 if ok else EXIT_VERIFY


if __name__ == "__main__":
    raise SystemExit(main())
