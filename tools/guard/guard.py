"""PreToolUse guard hook for an AI coding agent: refuses banned commands before they run.

Wire it as a PreToolUse hook for the tools Bash, PowerShell, Read and Grep (Edit and Write are never
blocked here). It reads the hook JSON on stdin and prints a deny decision, or nothing to allow.

Rules (no override tokens for any rule):
  R1  closing programs by name (taskkill /IM, taskkill without /PID, pkill, killall,
      Stop-Process -Name). An agent may stop only a process it started, by its own PID. The names python, pythonw, py, node and
      ollama are skipped here because a separate user-level hook handles them.
  R2  hard deletes (rm, Remove-Item, del, shutil.rmtree, os.remove ...). Deleting goes to the
      Recycle Bin through a helper instead.
  R3  shell heredocs / here-strings / inline python or node that write files (the shell can
      turn backslashes into hidden control characters). Use the editor tools.
  R4  one protected file (a secrets file): never opened, printed or quoted. Its location comes from
      the environment: GUARD_PROTECTED_DIR (default: <repo>/private) and GUARD_PROTECTED_NAME
      (default: secrets.json). GUARD_HOME overrides the home folder used to expand ~, $HOME and
      %USERPROFILE% (default: the real home folder). Nothing outside this repo is read.
  R5  python reading its script from stdin ("python -", or a heredoc fed to python): such
      processes can hang and spin a CPU core for days.

Method: heredoc and here-string bodies are cut out first; quoted strings are never treated as
commands. The exceptions are bodies of python/py -c, node -e, bash/sh -c, cmd /c, powershell -Command,
and heredocs fed to python/node/bash, which are checked as code. The command is split on
; && || | & newline ( ) and the first word of each piece is matched.
Fail open: any error or unreadable input exits 0 and allows. Deny prints the hook JSON and exits 0.
Stdlib only, no subprocess, no network.
"""
import base64
import fnmatch
import json
import os
import posixpath
import re
import sys

MSG = {
    "R1": "guard: closing programs by name is never allowed; stop only a process you started, by its own PID. "
          "Use taskkill /PID <pid> /F or Stop-Process -Id <pid>.",
    "R2": "guard: deletes go to the Recycle Bin. Use your recycle helper on the exact path "
          "(dry run first, then execute) instead of a hard delete.",
    "R3": "guard: edit files with the Edit or Write tool, not shell heredocs or inline Python "
          "(backslashes get corrupted).",
    "R4": "guard: the protected secrets file is never opened, printed or quoted. Ask the owner for what you need.",
    "ENC": "guard: encoded commands can't be checked; run the command plainly.",
    "R5": "guard: no 'python -' or heredocs fed to python: they can hang reading stdin and spin a CPU core. "
          "Write a .py file with the Write tool and run it.",
}


def _flat(s):
    """Lower-case, forward slashes, no repeated or trailing slash."""
    s = s.lower().replace("\\", "/")
    s = re.sub(r"(?<![\w:.])/{2,}[?.]/{1,2}", "", s)
    s = re.sub(r"(?<!^)/{2,}", "/", s)
    return s.rstrip("/") if len(s) > 3 else s


_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HOME = _flat(os.environ.get("GUARD_HOME") or os.path.expanduser("~"))
PROT_NAME = os.environ.get("GUARD_PROTECTED_NAME", "secrets.json").lower()
PROT_DIR = _flat(os.environ.get("GUARD_PROTECTED_DIR") or os.path.join(_ROOT, "private"))
PROT_CFG = PROT_DIR + "/" + PROT_NAME
PROT_BASE = PROT_DIR.rsplit("/", 1)[-1]

SKIP_NAME = re.compile(r"^(python[0-9.]*|pythonw|py|node|ollama)(\.exe)?$")
PYRE = re.compile(r"^(python[0-9.]*|pythonw|py)$")
SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
SKIPW = {"env", "sudo", "command", "call", "&", ".", "time", "nohup", "exec", "builtin"}
DELETERS = {"rm", "rmdir", "rd", "del", "erase", "unlink", "remove-item", "ri", "clear-recyclebin"}
STOPPERS = {"stop-process", "spps", "kill"}
GETPROC = {"get-process", "gps", "ps"}
CIM = {"get-ciminstance", "gcim", "get-wmiobject", "gwmi", "remove-ciminstance", "invoke-cimmethod",
       "remove-wmiobject", "invoke-wmimethod"}
WRITERS = {"set-content", "add-content", "out-file", "sc", "ac", "tee-object", "tee"}
READERS = {"cat", "type", "gc", "get-content", "more", "less", "head", "tail", "grep", "rg", "findstr",
           "select-string", "sls", "cp", "copy", "copy-item", "notepad", "code", "start", "ii",
           "invoke-item"}
CDS = {"cd", "chdir", "set-location", "sl", "pushd", "push-location"}
VARS = re.compile(r"\$env:userprofile|\$\{env:userprofile\}|%userprofile%|\$\{home\}|\$home|"
                  r"\$userprofile|\$env:home")
HEREDOC = re.compile(r"<<(?!<)-?\s*(['\"]?)([A-Za-z_]\w*)\1")

PY_DEL = re.compile(r"\bshutil\s*\.\s*rmtree|\bos\s*\.\s*(?:remove|unlink|rmdir|removedirs)\s*\(|"
                    r"\.\s*(?:unlink|rmdir)\s*\(|\b(?:unlinkSync|rmSync|rmdirSync)\s*\(|"
                    r"\bfs\s*\.\s*(?:promises\s*\.\s*)?(?:rm|unlink|rmdir)\s*\(")
DOTNET_DEL = re.compile(r"\[(?:system\.)?io\.(?:file|directory)\]::delete")
DOTNET_READ = re.compile(r"::(?:readall\w+|openread|opentext|open|copy|readlines)\b|streamreader")
CODE_WRITE = re.compile(
    r"\bopen\s*\((?:[^()]|\([^()]*\))*?,\s*(?:mode\s*=\s*)?['\"][rbt]*[wax][bt+]*['\"]\s*[,)]|"
    r"\.\s*(?:write_text|write_bytes)\s*\(|"
    r"\b(?:writeFileSync|writeFile|appendFileSync|appendFile|createWriteStream)\s*\(")
CODE_READ = re.compile(r"open|read|load|copy|cat\b|print|type\b", re.I)


# ---------------------------------------------------------------- paths

def norm(s):
    s = VARS.sub(lambda m: HOME, s.lower())
    s = s.replace("\\", "/")
    s = re.sub(r"(?<![\w:.])/{2,}[?.]/{1,2}", "", s)  # \\?\ and \\.\ prefixes
    s = re.sub(r"/{2,}", "/", s)
    s = re.sub(r"(?<![\w:.])~(?=/|$)", lambda m: HOME, s)
    s = re.sub(r"(?<![\w:.])/(?:mnt/)?([a-z])/", r"\1:/", s)
    return s


def _short_rules():
    """8.3 short names (PROT~1) of the home folder, the protected folder and the protected file."""
    rules = []
    for name in (HOME.rsplit("/", 1)[-1], PROT_BASE):
        pre = re.sub(r"[^a-z0-9_]", "", name)[:4]
        if pre:
            rules.append((re.compile(re.escape(pre) + r"[a-z0-9_]*~\d+"), name))
    stem = PROT_NAME.rsplit(".", 1)[0]
    pre = re.sub(r"[^a-z0-9_]", "", stem)[:4]
    if pre:
        rules.append((re.compile(re.escape(pre) + r"[a-z0-9_]*~\d+(\.[a-z0-9]*)?"), PROT_NAME))
    return rules


SHORT_RULES = _short_rules()


def clean_segments(p):
    """Windows ignores trailing dots/spaces on a name; map the 8.3 short names of the protected paths."""
    out = []
    for s in p.split("/"):
        if s and not re.fullmatch(r"\.+", s):
            s = s.rstrip(". ")
            for rx, full in SHORT_RULES:
                if rx.fullmatch(s):
                    s = full
                    break
        out.append(s)
    return "/".join(out)


def resolve(tok, cwd):
    t = norm(tok.strip("'\""))
    t = re.sub(r"^-{1,2}[a-z-]+[:=]", "", t).strip("'\"")
    if not re.match(r"[a-z]:/", t):
        t = cwd + "/" + t
    return posixpath.normpath(clean_segments(t))


def is_cfg(res):
    if res == PROT_CFG:
        return True
    return any(c in res for c in "*?[") and fnmatch.fnmatchcase(PROT_CFG, res)


def base(t):
    b = t.strip("'\"").replace("\\", "/").rsplit("/", 1)[-1].lower()
    b = re.sub(r"\.(exe|cmd|bat|com)$", "", b)
    if PYRE.match(b):
        return "python"
    return b


def cmd_index(toks):
    k = 0
    while k < len(toks):
        t = toks[k]
        if t.lower() in SKIPW or re.match(r"^[A-Za-z_]\w*=", t) or (t.startswith("$") and "=" in t):
            k += 1
        else:
            break
    return k


def skipname(n):
    return bool(SKIP_NAME.match(n.strip("'\"").lower()))


# ---------------------------------------------------------------- lexing

def lex(text):
    """-> list of (separator before it, tokens). Quotes are removed from tokens."""
    segs, toks, cur = [], [], []
    st = {"sep": "", "has": False}

    def tok():
        if st["has"]:
            toks.append("".join(cur))
            cur.clear()
            st["has"] = False

    def seg(nsep):
        tok()
        segs.append((st["sep"], list(toks)))
        toks.clear()
        st["sep"] = nsep

    i, n, q = 0, len(text), None
    while i < n:
        c = text[i]
        nx = text[i + 1] if i + 1 < n else ""
        if q:
            if c == "\\" and q == '"' and nx == '"':
                cur.append('"'); i += 2; continue
            if c == "`" and q == '"' and nx and nx in '"`$':
                cur.append(nx); i += 2; continue
            if c == q:
                q = None
            else:
                cur.append(c)
            i += 1
            continue
        if c in "'\"":
            q = c; st["has"] = True
        elif c == "`":
            if nx == "\n":
                i += 1
            elif nx and nx in "\"'`$ ":
                cur.append(nx); st["has"] = True; i += 1
            else:
                seg("`")
        elif c in " \t":
            tok()
        elif c in "\n;":
            seg("")
        elif c == "|":
            if nx == "|":
                i += 1; seg("||")
            else:
                seg("|")
        elif c == "&":
            prev = text[i - 1] if i else ""
            if nx == "&":
                i += 1; seg("&&")
            elif prev in "<>" or (nx and nx in "<>"):
                cur.append(c); st["has"] = True
            else:
                seg("&")
        elif c == "{" and cur and cur[-1] == "$":
            j = text.find("}", i)
            j = n - 1 if j < 0 else j
            cur.append(text[i:j + 1]); i = j
        elif c in "(){}":
            seg("(")
        elif c == "#" and not cur and not st["has"]:
            j = text.find("\n", i)
            i = n if j < 0 else j - 1
        else:
            cur.append(c); st["has"] = True
        i += 1
    seg("")
    return segs


def extract_docs(text):
    """Cut heredoc and here-string bodies out. -> (text without bodies, docs)."""
    lines = text.split("\n")
    out, docs, i = [], [], 0
    while i < len(lines):
        line = lines[i]
        m = re.search(r"@(['\"])\s*$", line)
        if m:
            q = m.group(1)
            j = next((k for k in range(i + 1, len(lines)) if re.match(r"\s*" + q + "@", lines[k])), None)
            if j is not None:
                tail = lines[j].lstrip()[2:]
                head = line[:m.start()]
                docs.append(("ps", head, tail, "\n".join(lines[i + 1:j])))
                out.append(head + '""' + tail)
                i = j + 1
                continue
        m = HEREDOC.search(line)
        if m:
            word = m.group(2)
            j = next((k for k in range(i + 1, len(lines)) if lines[k].strip() == word), None)
            if j is not None:
                docs.append(("sh", line, "", "\n".join(lines[i + 1:j])))
                out.append(line)
                i = j + 1
                continue
        out.append(line)
        i += 1
    return "\n".join(out), docs


def splitraw(line):
    return re.split(r";|&&|\|\|?|\$\(|\(|\)|`|\n", line)


def first_word(segtext):
    toks = [t.strip("'\"") for t in segtext.split()]
    k = cmd_index(toks)
    return base(toks[k]) if k < len(toks) else ""


def has_file_redirect(text):
    b = re.sub(r"\"[^\"\n]*\"|'[^'\n]*'", '""', text)
    for m in re.finditer(r"(?<![0-9&<>])>>?(?![&>])\s*([^\s|;&)]*)", b):
        t = m.group(1)
        if t and not re.match(r"(?i)(/dev/|\$null|nul$)", t):
            return True
    return False


# ---------------------------------------------------------------- rules

def check_code(body, cwd):
    n = norm(body)
    if (PROT_CFG in n or re.search(r"(?<![\w.-])" + re.escape(PROT_BASE + "/" + PROT_NAME), n)
            or (cwd.startswith(PROT_DIR) and PROT_NAME in n)) and CODE_READ.search(body):
        return "R4"
    if PY_DEL.search(body):
        return "R2"
    if CODE_WRITE.search(body):
        return "R3"
    return None


def r4_segment(toks, cwd):
    for i, t in enumerate(toks):  # stdin redirect: python x.py < the protected file
        p = None
        if t == "<" and i + 1 < len(toks):
            p = toks[i + 1]
        elif t.startswith("<") and not t.startswith("<<") and len(t) > 1:
            p = t[1:]
        if p and is_cfg(resolve(p, cwd)):
            return True
    reader = any(base(t) in READERS for t in toks)
    if not reader:
        return False
    if PROT_CFG in norm(" ".join(toks)):
        return True
    return any(is_cfg(resolve(t, cwd)) for t in toks)


def r1_segment(w, args):
    if w == "taskkill":
        low = [a.lower() for a in args]
        if any(re.match(r"^[/-]{1,2}\?$", a) for a in low):
            return False
        names = []
        for idx, a in enumerate(low):
            if idx + 1 >= len(args):
                continue
            if re.match(r"^[/-]{1,2}im$", a):
                names.append(args[idx + 1])
            elif re.match(r"^[/-]{1,2}fi$", a):
                m = re.search(r"imagename\s+eq\s+(\S+)", args[idx + 1], re.I)
                if m:
                    names.append(m.group(1))
        if names:
            return not all(skipname(x) for x in names)
        return not any(re.match(r"^[/-]{1,2}pid$", a) for a in low)
    if w in STOPPERS:
        for idx, a in enumerate(args):
            m = re.match(r"^-(n\w*|processname)(?:[:=](.*))?$", a, re.I)
            if m:
                val = m.group(2) if m.group(2) is not None else (args[idx + 1] if idx + 1 < len(args) else "")
                vals = [v for v in re.split(r"[,\s]+", val) if v]
                if vals and not all(v.isdigit() or skipname(v) for v in vals):
                    return True
        return False
    if w in ("pkill", "killall"):
        names = [a for a in args if not a.startswith("-")]
        return not (names and all(skipname(x) for x in names))
    if w == "wmic":
        j = " ".join(args).lower()
        if re.search(r"\b(delete|terminate)\b", j):
            names = re.findall(r"name\s*(?:=|like)\s*['\"]?([\w.*%-]+)", j)
            return bool(names) and not all(skipname(x) for x in names)
    return False


def r1_getproc(args):
    """Deny a Get-Process ... | Stop-Process pipeline unless it is by Id or only the five skipped names."""
    if any(re.match(r"^-(id|inputobject)$", a, re.I) for a in args):
        return False
    names = []
    for idx, a in enumerate(args):
        if re.match(r"^-n\w*$", a, re.I) and idx + 1 < len(args):
            names += re.split(r"[,\s]+", args[idx + 1])
        elif not a.startswith("-") and not (idx and re.match(r"^-n\w*$", args[idx - 1], re.I)):
            names += re.split(r"[,\s]+", a)
    names = [x for x in names if x]
    return not (names and all(skipname(x) for x in names))


def r2_segment(w, args):
    if w == "git":
        subs = [a for a in args if not a.startswith("-")]
        return bool(subs) and subs[0] == "rm"
    if w not in DELETERS:
        return False
    paths = [a for a in args if not a.startswith("-")]
    if paths and all(re.match(r"(?i)^(env|variable|function):", p) for p in paths):
        return False
    return True


def analyze(text, cwd, depth=0):
    if depth > 4 or not text:
        return None
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    stripped, docs = extract_docs(text)
    segs = lex(stripped)
    r5 = False  # python reading stdin; reported only if no other rule matches
    whole = " ".join(" ".join(t) for _, t in segs).lower()
    if DOTNET_READ.search(whole) and any(is_cfg(resolve(t, cwd)) for _, ts in segs for t in ts):
        return "R4"
    for i, (sep, toks) in enumerate(segs):
        if not toks:
            continue
        for t in toks:  # $( ... ) inside double quotes is code too
            if "$(" in t:
                for inner in re.findall(r"\$\(([^()]*)\)", t):
                    r = analyze(inner, cwd, depth + 1)
                    if r:
                        return r
        if r4_segment(toks, cwd):
            return "R4"
        k = cmd_index(toks)
        if k >= len(toks):
            continue
        w, args = base(toks[k]), toks[k + 1:]
        if DOTNET_DEL.search(w) or (w.startswith("$") and DOTNET_DEL.search(" ".join(toks).lower())):
            return "R2"
        if w == "find":
            low = [a.lower() for a in args]
            if "-delete" in low:
                return "R2"
            for idx, a in enumerate(low):
                if a in ("-exec", "-execdir") and idx + 1 < len(args) and base(args[idx + 1]) in DELETERS:
                    return "R2"
        if w in CDS:
            p = [a for a in args if not a.startswith("-") and a.lower() != "/d"]
            if p:
                cwd = resolve(p[0], cwd)
        if r1_segment(w, args):
            return "R1"
        if w in STOPPERS and sep == "|" and not any(re.match(r"^-id$", a, re.I) for a in args):
            # walk back through the same statement (pipes and { } script blocks, e.g. Where-Object {...})
            j = i
            while j >= 0:
                tj = segs[j][1]
                kj = cmd_index(tj) if tj else 0
                if tj and kj < len(tj) and base(tj[kj]) in GETPROC and r1_getproc(tj[kj + 1:]):
                    return "R1"
                if segs[j][0] in ("", "&&", "||", "&"):
                    break
                j -= 1
        if w in CIM and "win32_process" in " ".join(args).lower():
            names = re.findall(r"name\s*(?:=|-eq|-like|like)\s*['\"]?([\w.*%-]+)", " ".join(args).lower())
            if (names and not all(skipname(x) for x in names)
                    and re.search(r"terminate|remove-ciminstance|remove-wmiobject|stop-process", whole)):
                return "R1"
        if r2_segment(w, args):
            return "R2"
        # code run inline
        body = None
        if w == "python":
            for idx, a in enumerate(args):
                if re.match(r"^-[A-Za-z]*c$", a) and idx + 1 < len(args):
                    body = args[idx + 1]
                    break
            if body is None and args and args[-1] == "-" and sep == "|" and i:
                body = " ".join(segs[i - 1][1])
            if body is not None:
                r = check_code(body, cwd)
                if r:
                    return r
            if "-" in args:
                r5 = True
        elif w == "node":
            for idx, a in enumerate(args):
                if a in ("-e", "--eval", "-p", "--print") and idx + 1 < len(args):
                    r = check_code(args[idx + 1], cwd)
                    if r:
                        return r
            if args and args[-1] == "-" and sep == "|" and i:
                r = check_code(" ".join(segs[i - 1][1]), cwd)
                if r:
                    return r
        elif w in SHELLS:
            for idx, a in enumerate(args):
                if re.match(r"^-[a-z]*c[a-z]*$", a) and idx + 1 < len(args):
                    r = analyze(args[idx + 1], cwd, depth + 1)
                    if r:
                        return r
                    break
        elif w == "cmd":
            for idx, a in enumerate(args):
                if a.lower() in ("/c", "/k"):
                    r = analyze(" ".join(args[idx + 1:]), cwd, depth + 1)
                    if r:
                        return r
                    break
        elif w in ("powershell", "pwsh"):
            for idx, a in enumerate(args):
                if a.lower() in ("-c", "-co", "-com", "-comm", "-comma", "-comman", "-command"):
                    r = analyze(" ".join(args[idx + 1:]), cwd, depth + 1)
                    if r:
                        return r
                    break
                if len(a) >= 2 and a[0] in "-/" and "encodedcommand".startswith(a[1:].lower()):
                    try:
                        raw = base64.b64decode("".join(args[idx + 1:idx + 2]), validate=True)
                        decoded = raw.decode("utf-16-le")
                    except Exception:
                        return "ENC"
                    r = analyze(decoded, cwd, depth + 1)
                    if r:
                        return r
                    break
        elif w == "wsl" and args:
            r = analyze(" ".join(args), cwd, depth + 1)
            if r:
                return r
    # heredocs and here-strings
    has_ps = False
    for kind, head, tail, body in docs:
        if kind == "ps":
            has_ps = True
            if any(first_word(s) in ("python", "node") for s in splitraw(tail)):
                r = check_code(body, cwd)
                if r:
                    return r
            continue
        parts = splitraw(head)
        idx = next((x for x, s in enumerate(parts) if "<<" in s), 0)
        fws = [first_word(s) for s in parts[idx:]]
        if any(f in ("python", "node") for f in fws):
            r = check_code(body, cwd)
            if r:
                return r
            if any(base(f) == "python" for f in fws if f):
                r5 = True
        elif any(f in SHELLS for f in fws):
            r = analyze(body, cwd, depth + 1)
            if r:
                return r
        seg0 = HEREDOC.sub("", parts[idx])
        if has_file_redirect(seg0) or has_file_redirect(" ".join(HEREDOC.sub("", p) for p in parts[idx + 1:])):
            return "R3"
        for s in parts[idx:]:
            toks = s.split()
            kk = cmd_index(toks)
            if kk < len(toks) and base(toks[kk]) == "tee" and any(not a.startswith("-") for a in toks[kk + 1:]):
                return "R3"
    if has_ps:
        for _, toks in segs:
            kk = cmd_index(toks)
            if kk < len(toks) and base(toks[kk]) in WRITERS:
                return "R3"
        if has_file_redirect(stripped):
            return "R3"
    return "R5" if r5 else None


# ---------------------------------------------------------------- tool entry

def expand_braces(g):
    m = re.search(r"\{([^{}]*)\}", g)
    if not m:
        return [g]
    out = []
    for alt in m.group(1).split(","):
        out += expand_braces(g[:m.start()] + alt + g[m.end():])
    return out


def grep_hits_protected(ti, cwd):
    p = ti.get("path")
    res = resolve(p, cwd) if p else cwd
    if res == PROT_CFG:
        return True
    # the protected folder itself, or any folder above it
    if not (res == PROT_DIR or PROT_DIR.startswith(res.rstrip("/") + "/")) \
            or (ti.get("output_mode") or "files_with_matches") != "content":
        return False
    typ = ti.get("type")
    if typ and typ.lower() != PROT_NAME.rsplit(".", 1)[-1]:
        return False
    g = ti.get("glob")
    if not g:
        return True
    rel = PROT_CFG[len(res.rstrip("/")) + 1:]
    for pat in expand_braces(g.lower()):
        while pat.startswith("**/"):
            pat = pat[3:]
        if fnmatch.fnmatchcase(PROT_NAME, pat) or fnmatch.fnmatchcase(rel, pat):
            return True
    return False


def decide(data):
    tool = data.get("tool_name") or ""
    ti = data.get("tool_input") or {}
    cwd = posixpath.normpath(norm(data.get("cwd") or os.getcwd())).rstrip("/")
    if tool == "Read":
        fp = ti.get("file_path")
        return "R4" if fp and is_cfg(resolve(fp, cwd)) else None
    if tool == "Grep":
        return "R4" if grep_hits_protected(ti, cwd) else None
    if tool in ("Bash", "PowerShell"):
        return analyze(ti.get("command") or "", cwd)
    return None


def main():
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8-sig", errors="replace"))
        rule = decide(data)
    except Exception:
        return 0
    if rule:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": MSG[rule]}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
