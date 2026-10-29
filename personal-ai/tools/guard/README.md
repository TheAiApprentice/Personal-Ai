# Guard hook

A PreToolUse hook for an AI coding agent. Before the agent runs a shell, PowerShell, read or search call, the hook reads
the call and either lets it through or refuses it with a reason. Rules in a prompt can be ignored; rules in a hook can't.

## Rules

| Rule | Refuses | Why |
|---|---|---|
| R1 | Closing programs by name (`taskkill /IM`, `taskkill` without `/PID`, `pkill`, `killall`, `Stop-Process -Name`) | One name can match many programs. An agent may stop only a process it started, by its own PID |
| R2 | Hard deletes (`rm`, `Remove-Item`, `del`, `shutil.rmtree`, `os.remove` ...) | Deleting goes to the Recycle Bin through a helper, so nothing is lost by mistake |
| R3 | Shell heredocs, here-strings and inline code that write files | The shell can turn backslashes into hidden control characters. Files are edited with the editor tools |
| R4 | Opening, printing or quoting one protected secrets file | Its location comes from `GUARD_PROTECTED_DIR` and `GUARD_PROTECTED_NAME` (default `private/secrets.json`) |
| R5 | Python reading its script from standard input (`python -`, a heredoc fed to python) | Such processes can hang and spin a CPU core for days |

There are no override tokens. Each rule exists because it went wrong once on a real machine.

## How it decides

Heredoc and here-string bodies are cut out first, and quoted strings are never treated as commands. The exceptions are
code bodies (`python -c`, `node -e`, `bash -c`, `cmd /c`, `powershell -Command`, heredocs fed to an interpreter), which are
checked as code. The command is split on `;`, `&&`, `||`, `|`, `&`, newlines and brackets, and the first word of each
piece is matched. If anything goes wrong reading the input, the hook allows the call (fail open) rather than blocking
the agent. Standard library only, no network.

## Use it

Wire `guard.py` as a PreToolUse hook for the Bash, PowerShell, Read and Grep tools. It reads the hook JSON on standard
input and prints a deny decision, or nothing to allow.

Try it:

    echo {"tool_name":"Bash","tool_input":{"command":"taskkill /IM notepad.exe"}} | python guard.py

prints a deny with the R1 reason. `taskkill /PID 1234 /F` prints nothing (allowed).

## Tests

    python -m pytest -q -p no:cacheprovider tools/guard

Expected: `201 passed`. The tests use made-up paths under a temp folder and never touch real files.
