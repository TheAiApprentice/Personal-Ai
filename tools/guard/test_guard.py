"""Tests for guard.py. Every case runs guard.py as a subprocess with the hook JSON on stdin.

Run:  python -m pytest tools/guard
The banned text below is only ever sent to guard.py as JSON; nothing here runs it.

The protected file lives in a made-up home folder under the system temp folder. It is never created:
guard.py only compares text, so nothing real is read. Windows paths are used on purpose (the hook
is written for Windows and Git Bash path styles); the tests need a drive-lettered temp folder.
"""
import base64
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path, PureWindowsPath

import pytest

GUARD = Path(__file__).resolve().parent / "guard.py"

_home = PureWindowsPath(tempfile.gettempdir()) / "demohome"
_prot = _home / "secrets_dir"
_drive = _home.drive.rstrip(":").lower()
TOKENS = {
    "@HOME@": str(_home),
    "@HOMEF@": _home.as_posix(),
    "@PA@": str(_home / "project"),
    "@PROT@": str(_prot),
    "@PROTF@": _prot.as_posix(),
    "@PROTDD@": str(_prot).replace("\\", "\\\\"),
    "@PROTG@": "/" + _drive + _prot.as_posix()[2:],
    "@PROTGG@": "//" + _drive + _prot.as_posix()[2:],
    "@ROOT@": _home.anchor,
    "@SHORTHOME@": str(_home.parent / "DEMOHO~1"),
}
ENV = dict(os.environ, GUARD_HOME=str(_home), GUARD_PROTECTED_DIR=str(_prot), GUARD_PROTECTED_NAME="secrets.json")


def ex(s):
    for k in sorted(TOKENS, key=len, reverse=True):
        s = s.replace(k, TOKENS[k])
    return s


PROT = ex("@PROT@")
PA = ex("@PA@")
HOME = ex("@HOME@")


def run_guard(payload, raw=None):
    stdin = raw if raw is not None else json.dumps(payload)
    p = subprocess.run([sys.executable, str(GUARD)], input=stdin, capture_output=True, text=True,
                       timeout=20, env=ENV)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout) if p.stdout.strip() else None


def bash(cmd, tool="Bash", cwd=PA):
    return {"tool_name": tool, "tool_input": {"command": ex(cmd)}, "cwd": ex(cwd)}


def reason(out):
    assert out, "expected a deny"
    h = out["hookSpecificOutput"]
    assert h["hookEventName"] == "PreToolUse" and h["permissionDecision"] == "deny"
    return h["permissionDecisionReason"]


R1 = "closing programs by name"
R2 = "Recycle Bin"
R3 = "Edit or Write tool"
R4 = "protected secrets file is never opened"
R5 = "no 'python -'"

WIN = pytest.mark.skipif(sys.platform != "win32", reason="Windows path forms")


def winonly(*case):
    """Mark a parametrized case as Windows-only (backslashes, drive letters, 8.3 names, %VARS%)."""
    return pytest.param(case, marks=WIN)

DENY_CMDS = [
    # R5
    (R5, "python - <<'EOF'\nprint('hi')\nEOF"),
    (R5, "python - <<'EOF'\nprint(open('f.txt').read())\nEOF"),
    (R5, "python3 <<'E'\nprint(1)\nE"),
    (R5, "echo 'print(1)' | python -"),
    (R5, "cd x && python - 2>/dev/null"),
    # R1
    (R1, "taskkill /IM chrome.exe /F"),
    (R1, "taskkill //F //IM chrome.exe"),
    (R1, 'taskkill /F /FI "IMAGENAME eq chrome.exe"'),
    (R1, "taskkill /F"),
    (R1, "taskkill /IM python.exe /IM chrome.exe"),
    (R1, "Stop-Process -Name chrome"),
    (R1, "Stop-Process -ProcessName chrome -Force"),
    (R1, "spps -Name chrome"),
    (R1, "Get-Process chrome | Stop-Process"),
    (R1, "gps chrome | kill"),
    (R1, "Get-Process | Stop-Process -Force"),
    (R1, "pkill chrome"),
    (R1, "killall chrome"),
    (R1, 'wmic process where "name=\'chrome.exe\'" delete'),
    (R1, "wmic process where name='chrome.exe' call terminate"),
    (R1, "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | Invoke-CimMethod -MethodName Terminate"),
    (R1, "echo hi && taskkill /IM chrome.exe"),
    (R1, "cmd /c taskkill /IM chrome.exe"),
    # R2
    (R2, "rm -rf somedir"),
    (R2, "rm scratch.txt"),
    (R2, "rmdir old"),
    (R2, "rd /s /q old"),
    (R2, "del scratch.txt"),
    (R2, "erase scratch.txt"),
    (R2, "unlink a.txt"),
    (R2, "git rm file.py"),
    (R2, "Remove-Item @HOME@\\temp\\x.txt"),
    (R2, "Remove-Item -Recurse -Force @HOME@\\temp\\x"),
    (R2, "ri x.txt"),
    (R2, "Clear-RecycleBin -Force"),
    (R2, "cmd /c del x.txt"),
    (R2, 'cmd /c "rd /s /q old"'),
    (R2, "echo a; rm x"),
    (R2, "ls && rm x"),
    (R2, "bash -c 'rm x'"),
    (R2, 'python -c "import shutil; shutil.rmtree(\'d\')"'),
    (R2, 'python -c "import os; os.remove(\'f\')"'),
    (R2, 'python -c "import os; os.unlink(\'f\')"'),
    (R2, 'python -c "import os; os.rmdir(\'f\')"'),
    (R2, 'python -c "from pathlib import Path; Path(\'f\').unlink()"'),
    (R2, 'python -c "from pathlib import Path; Path(\'f\').rmdir()"'),
    (R2, "python - <<'EOF'\nimport shutil\nshutil.rmtree('d')\nEOF"),
    # R3
    (R3, "cat <<'EOF' > notes.txt\nhello\nEOF"),
    (R3, "cat > notes.txt <<'EOF'\nhello\nEOF"),
    (R3, "cat >> notes.txt <<EOF\nhello\nEOF"),
    (R3, "tee notes.txt <<'EOF'\nhello\nEOF"),
    (R3, "cat <<'EOF' | tee notes.txt\nhello\nEOF"),
    (R3, "python - <<'EOF'\nopen('f.txt','w').write('x')\nEOF"),
    (R3, "python3 <<'EOF'\nfrom pathlib import Path\nPath('f').write_text('x')\nEOF"),
    (R3, "py - <<'EOF'\nPath('f').write_bytes(b'x')\nEOF"),
    (R3, "node <<'EOF'\nrequire('fs').writeFileSync('f','x')\nEOF"),
    (R3, "python -c \"open('f.txt','w').write('x')\""),
    (R3, "python -c \"open('f.txt', mode='a').write('x')\""),
    (R3, "python -c \"from pathlib import Path; Path('f').write_text('x')\""),
    (R3, "node -e \"require('fs').writeFileSync('f','x')\""),
    (R3, "@'\nhello\n'@ | Set-Content notes.txt", "PowerShell"),
    (R3, "@'\nhello\n'@ | Out-File notes.txt", "PowerShell"),
    (R3, "@\"\nhello\n\"@ | Add-Content notes.txt", "PowerShell"),
    (R3, "@'\nhello\n'@ > notes.txt", "PowerShell"),
    (R3, "@'\nhello\n'@ >> notes.txt", "PowerShell"),
    (R3, "$t = @'\nhello\n'@\nSet-Content notes.txt $t", "PowerShell"),
    (R3, "bash -c \"cat > f <<EOF\nx\nEOF\""),
    # R4
    (R4, "cat @PROT@\\secrets.json"),
    (R4, "cat @PROTF@/secrets.json"),
    winonly(R4, "cat @PROTG@/secrets.json"),
    winonly(R4, "cat @PROTGG@/secrets.json"),
    (R4, "cat ~/secrets_dir/secrets.json"),
    (R4, "cat $HOME/secrets_dir/secrets.json"),
    (R4, "Get-Content $env:USERPROFILE\\secrets_dir\\secrets.json", "PowerShell"),
    (R4, "type %USERPROFILE%\\secrets_dir\\secrets.json"),
    (R4, "Get-Content @PROTDD@\\\\secrets.json", "PowerShell"),
    (R4, "gc '@PROT@\\secrets.json'", "PowerShell"),
    (R4, "grep token ../secrets_dir/secrets.json"),
    (R4, "head -5 secrets_dir/secrets.json", "Bash", "@HOME@"),
    (R4, "cat secrets.json", "Bash", "@PROT@"),
    (R4, "Get-Content .\\secrets.json", "PowerShell", "@PROT@"),
    (R4, "cp @PROTF@/secrets.json x.json"),
    (R4, "Copy-Item @PROT@\\secrets.json x.json", "PowerShell"),
    (R4, "notepad @PROT@\\secrets.json", "PowerShell"),
    (R4, "findstr token @PROT@\\secrets.json"),
    (R4, "Select-String token @PROT@\\secrets.json", "PowerShell"),
    (R4, "echo ok; cat @PROTF@/secrets.json"),
    winonly(R4, "cat @PROTF@/secr*.json"),
    (R4, "python -c \"print(open(r'@PROT@\\secrets.json').read())\""),
    (R4, "python - <<'EOF'\nprint(open(r'@PROTF@/secrets.json').read())\nEOF"),
    winonly(R4, "cd @PROTF@ && cat secrets.json"),
]

PASS_CMDS = [
    "taskkill /PID 1234 /F",
    "taskkill /PID 1234 /T /F",
    "Stop-Process -Id 1234",
    "Stop-Process -Id 1234 -Force",
    "kill 1234",
    "kill -9 1234",
    "Get-Process -Id 1234 | Stop-Process",
    "taskkill /IM python.exe /F",          # left to the user-level hook, not doubled here
    "Stop-Process -Name python",
    "Remove-Item Env:FOO",
    "Remove-Item -Path Variable:x",
    "Remove-Item Function:foo",
    "python tools/recycle.py --path \"@HOME@\\x.txt\" --order-file o.txt",
    "python tools/recycle.py --path \"@HOME@\\x.txt\" --order-file o.txt --execute",
    "git commit -m \"$(cat <<'EOF'\ntaskkill /IM chrome.exe and rm -rf and cat > f <<X\nEOF\n)\"",
    "git commit -m @'\nfix: stop using rm -rf, open('f','w')\n'@",
    "python tools/memory/mem.py add --text \"never run rm -rf or taskkill /IM x.exe\" --layer knowledge",
    "echo rm -rf x",
    "echo \"del x; Remove-Item y\"",
    "git status",
    "git log --grep rm",
    "ls -la",
    "python -c \"print(1)\"",
    "python -c \"print(open('f.txt').read())\"",
    "python -c \"print(open('f.txt','r').read())\"",
    "python -c \"import json; print(json.dumps({'a': 1}))\"",
    "node -e \"console.log(1)\"",
    "cat <<'EOF'\nhello rm -rf\nEOF",
    "cat notes.txt",
    "cat projects/news/config.json",
    "cat @PA@/secrets.json",
    "cat @HOMEF@/secrets_dir-Update/secrets.json",
    "cat @PROTF@/README.md",
    "ls @PROTF@",
    "echo see @PROTF@/secrets.json",
    "git commit -m \"note: never cat @PROTF@/secrets.json\"",
    "cat secrets.json",
    "pytest -q 2>&1 | tail -5",
    "python x.py > out.txt",
    "echo hi > /dev/null 2>&1",
]


@pytest.mark.parametrize("case", DENY_CMDS, ids=lambda c: c[1][:60].replace("\n", "|"))
def test_denies(case):
    rule, cmd = case[0], case[1]
    tool = case[2] if len(case) > 2 else "Bash"
    cwd = case[3] if len(case) > 3 else "@PA@"
    assert rule in reason(run_guard(bash(cmd, tool, cwd)))


@pytest.mark.parametrize("cmd", PASS_CMDS, ids=lambda c: c[:60].replace("\n", "|"))
def test_passes(cmd):
    assert run_guard(bash(cmd)) is None
    assert run_guard(bash(cmd, "PowerShell")) is None


def test_secrets_json_bare_is_fine_outside_protected_folder():
    assert run_guard(bash("cat secrets.json", cwd="@PA@")) is None
    assert run_guard(bash("cat secrets.json", cwd="@PROT@\\sub")) is None  # a sub folder's own file


def test_powershell_here_string_arg_passes():
    assert run_guard(bash("git commit -m @'\ntext\n'@", "PowerShell")) is None
    assert run_guard(bash("python tools/x.py --text @\"\nhello\n\"@", "PowerShell")) is None


# ---- Read and Grep

@WIN
def test_read_protected_denied():
    for fp in ["@PROT@\\secrets.json", "@PROTF@/secrets.json", ex("@PROT@\\SECRETS.JSON").upper(),
               "@PROTG@/secrets.json", "~/secrets_dir/secrets.json", "../secrets_dir/secrets.json"]:
        assert R4 in reason(run_guard({"tool_name": "Read", "tool_input": {"file_path": ex(fp)}, "cwd": PA}))
    assert R4 in reason(run_guard({"tool_name": "Read", "tool_input": {"file_path": "secrets.json"}, "cwd": PROT}))


def test_read_other_files_pass():
    for fp in ["@PA@\\README.md", "@PROT@\\README.md", "@PA@\\projects\\news\\config.json",
               "@HOME@\\secrets_dir-Update\\secrets.json"]:
        assert run_guard({"tool_name": "Read", "tool_input": {"file_path": ex(fp)}, "cwd": PA}) is None


@WIN
def test_grep_protected_denied():
    g = lambda ti: run_guard({"tool_name": "Grep", "tool_input": ti, "cwd": PA})
    assert R4 in reason(g({"pattern": "x", "path": PROT + "\\secrets.json"}))
    assert R4 in reason(g({"pattern": "x", "path": PROT, "output_mode": "content"}))
    assert R4 in reason(g({"pattern": "x", "path": PROT, "output_mode": "content", "glob": "*.json"}))
    assert R4 in reason(g({"pattern": "x", "path": PROT, "output_mode": "content", "glob": "secrets.json"}))
    assert R4 in reason(g({"pattern": "x", "path": PROT, "output_mode": "content", "glob": "*.{py,json}"}))
    assert R4 in reason(g({"pattern": "x", "path": PROT, "output_mode": "content", "glob": "**/secrets.*"}))


def test_grep_other_passes():
    g = lambda ti: run_guard({"tool_name": "Grep", "tool_input": ti, "cwd": PA})
    assert g({"pattern": "x", "path": PROT, "output_mode": "content", "glob": "*.py"}) is None
    assert g({"pattern": "x", "path": PROT, "output_mode": "files_with_matches"}) is None
    assert g({"pattern": "x", "path": PROT, "output_mode": "count"}) is None
    assert g({"pattern": "x", "path": PA, "output_mode": "content"}) is None
    assert g({"pattern": "x", "path": PA + "\\projects\\news\\config.json"}) is None
    assert g({"pattern": "x", "path": PROT, "output_mode": "content", "type": "py"}) is None


def test_other_tools_ignored():
    for tool in ("Edit", "Write", "Glob"):
        assert run_guard({"tool_name": tool, "tool_input": {"file_path": PROT + "\\secrets.json"}, "cwd": PA}) is None


# ---- hardening round

def enc(text):
    return base64.b64encode(ex(text).encode("utf-16-le")).decode()


HARD_DENY = [
    # 1. Get-Process | filter | Stop-Process
    (R1, "Get-Process | Where-Object {$_.Name -eq 'chrome'} | Stop-Process", "PowerShell"),
    (R1, "Get-Process | ? {$_.Name -eq 'chrome'} | Stop-Process -Force", "PowerShell"),
    (R1, "Get-Process | Where-Object {$_.Name -like 'chr*'} | Stop-Process", "PowerShell"),
    (R1, "gps | where {$_.Name -match 'chrome'} | kill", "PowerShell"),
    (R1, "Get-Process | Where Name -eq chrome | Stop-Process", "PowerShell"),
    # 2. stdin redirect
    winonly(R4, "python x.py < @PROT@\\secrets.json"),
    winonly(R4, "python x.py <@PROT@\\secrets.json"),
    winonly(R4, "node x.js < ~/secrets_dir/secrets.json"),
    # 3. encoded commands
    (R1, "powershell -EncodedCommand " + enc("taskkill /IM chrome.exe"), "PowerShell"),
    (R2, "pwsh -enc " + enc("Remove-Item x.txt"), "PowerShell"),
    (R4, "powershell -NoProfile -e " + enc("Get-Content @PROT@\\secrets.json"), "PowerShell"),
    ("encoded commands can't be checked", "powershell -EncodedCommand !!notbase64!!", "PowerShell"),
    ("encoded commands can't be checked", "pwsh -enc QQ", "PowerShell"),
    # 4. path variants
    (R4, "type @PROT@\\secrets.json.", "PowerShell"),
    (R4, "type \"@PROT@\\secrets.json \""),
    winonly(R4, "type @HOME@\\secrets_dir.\\secrets.json"),
    winonly(R4, "type \\\\?\\@PROT@\\secrets.json"),
    winonly(R4, "type //?/@PROTF@/secrets.json"),
    winonly(R4, "type @PROT@\\SECRET~1.JSO"),
    winonly(R4, "type @SHORTHOME@\\secrets_dir\\secrets.json"),
    # 5. cheap deletes and reads
    (R2, "node -e \"require('fs').unlinkSync('f')\""),
    (R2, "node -e \"require('fs').rmSync('d',{recursive:true})\""),
    (R2, "node -e \"require('fs').rmdirSync('d')\""),
    (R2, "[System.IO.File]::Delete('@HOME@\\x.txt')", "PowerShell"),
    (R2, "[IO.File]::Delete('@HOME@\\x.txt')", "PowerShell"),
    (R2, "[IO.Directory]::Delete('@HOME@\\x', $true)", "PowerShell"),
    (R2, "$null = [IO.File]::Delete('@HOME@\\x.txt')", "PowerShell"),
    (R2, "find . -name '*.tmp' -delete"),
    (R2, "find . -name '*.tmp' -exec rm {} \\;"),
    winonly(R4, "[IO.File]::ReadAllText('@PROT@\\secrets.json')", "PowerShell"),
    winonly(R4, "[System.IO.File]::ReadAllBytes(\"$env:USERPROFILE\\secrets_dir\\secrets.json\")", "PowerShell"),
]

HARD_PASS = [
    "Get-Process -Id 1234 | Stop-Process",
    "Get-Process | Where-Object {$_.Id -eq 5} | Stop-Process -Id 5",
    "Get-Process | Select-Object Name, Id",
    "Get-Process | Where-Object {$_.Name -eq 'chrome'}",
    "powershell -Command \"Get-Date\"",
    "powershell -EncodedCommand " + enc("Get-Date"),
    "python x.py < input.txt",
    "type @PROT@\\README.md",
    "type @PROT@\\conf\\settings.json",
    "[IO.File]::ReadAllText('@PA@\\NOTES.md')",
    "[IO.File]::Exists('@HOME@\\x.txt')",
    "find . -name '*.py'",
    "find . -name '*.py' -exec grep foo {} \\;",
    "node -e \"console.log(require('fs').readFileSync('f','utf8'))\"",
    "git commit -m \"mention [IO.File]::Delete and unlinkSync\"",
]


@pytest.mark.parametrize("case", HARD_DENY, ids=lambda c: c[1][:60])
def test_hardening_denies(case):
    tool = case[2] if len(case) > 2 else "Bash"
    assert case[0] in reason(run_guard(bash(case[1], tool)))


@pytest.mark.parametrize("cmd", HARD_PASS, ids=lambda c: c[:60])
def test_hardening_passes(cmd):
    assert run_guard(bash(cmd, "PowerShell")) is None


@WIN
def test_grep_rooted_above_protected_folder():
    g = lambda ti: run_guard({"tool_name": "Grep", "tool_input": ti, "cwd": PA})
    assert R4 in reason(g({"pattern": "x", "path": HOME, "output_mode": "content", "glob": "**/secrets.json"}))
    assert R4 in reason(g({"pattern": "x", "path": HOME, "output_mode": "content", "glob": "secrets_dir/*.json"}))
    assert R4 in reason(g({"pattern": "x", "path": ex("@ROOT@"), "output_mode": "content", "glob": "secrets.json"}))
    assert g({"pattern": "x", "path": HOME, "output_mode": "content", "glob": "*.py"}) is None
    assert g({"pattern": "x", "path": HOME, "output_mode": "files_with_matches", "glob": "**/secrets.json"}) is None


@WIN
def test_read_path_variants_denied():
    for fp in [PROT + "\\secrets.json.", PROT + "\\secrets.json ", "\\\\?\\" + PROT + "\\secrets.json",
               PROT + "\\SECRET~1.JSO"]:
        assert R4 in reason(run_guard({"tool_name": "Read", "tool_input": {"file_path": fp}, "cwd": PA}))


def test_bom_stdin_still_denies():
    raw = b"\xef\xbb\xbf" + json.dumps(bash("taskkill /IM chrome.exe")).encode()
    p = subprocess.run([sys.executable, str(GUARD)], input=raw, capture_output=True, timeout=20, env=ENV)
    assert p.returncode == 0 and b'"deny"' in p.stdout


@WIN
def test_defaults_point_inside_the_repo():
    """With no GUARD_* variables the protected file is <repo>/private/secrets.json."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GUARD_")}
    repo = GUARD.parents[2]
    payload = {"tool_name": "Read", "tool_input": {"file_path": str(repo / "private" / "secrets.json")},
               "cwd": str(repo)}
    p = subprocess.run([sys.executable, str(GUARD)], input=json.dumps(payload), capture_output=True,
                       text=True, timeout=20, env=env)
    assert R4 in reason(json.loads(p.stdout))


# ---- fail open

@pytest.mark.parametrize("raw", ["", "   ", "not json", "{", "[]", "null", "{}", '{"tool_name": "Bash"}',
                                 '{"tool_name": "Bash", "tool_input": null}',
                                 '{"tool_name": "Bash", "tool_input": {"command": 5}}',
                                 '{"tool_name": "Bash", "tool_input": {"command": "echo \\"unclosed"}}'])
def test_garbage_stdin_allows(raw):
    p = subprocess.run([sys.executable, str(GUARD)], input=raw, capture_output=True, text=True, timeout=20,
                       env=ENV)
    assert p.returncode == 0 and p.stdout.strip() == ""


def test_messages_exact():
    assert reason(run_guard(bash("taskkill /IM chrome.exe"))).startswith(
        "guard: closing programs by name is never allowed; stop only a process you started, by its own PID. "
        "Use taskkill /PID <pid> /F or Stop-Process -Id <pid>.")
    assert "Recycle Bin" in reason(run_guard(bash("rm x")))
    assert reason(run_guard(bash("cat > f <<EOF\nx\nEOF"))) == (
        "guard: edit files with the Edit or Write tool, not shell heredocs or inline Python "
        "(backslashes get corrupted).")
    assert reason(run_guard(bash("cat ~/secrets_dir/secrets.json"))) == (
        "guard: the protected secrets file is never opened, printed or quoted. Ask the owner for what you need.")


# ---- speed

def test_median_under_150ms():
    payload = json.dumps(bash("git status && python tools/memory/mem.py brief"))
    times = []
    for _ in range(9):
        t = time.perf_counter()
        subprocess.run([sys.executable, str(GUARD)], input=payload, capture_output=True, text=True,
                       timeout=20, env=ENV)
        times.append((time.perf_counter() - t) * 1000)
    assert statistics.median(times) < 150, times
