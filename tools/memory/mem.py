"""Agent memory (v1, a SQLite stand-in for a future PostgreSQL + pgvector store).

One SQLite file: data/memory.db (created on first use, never shipped). Tables are shaped like the
planned Postgres schema so `export` -> import is a straight copy when the box exists.

Layers:
  user        long-term preferences, history and personal context for one user
  project     living specification: goals, decisions, status, bugs
  experience  what worked, what failed, why
  knowledge   general facts and lessons usable by every user
  archive     raw chat log (table `archive`, append-only, never edited)

Status: proposed -> trusted (the gatekeeper commits it), or uncertain / deprecated /
quarantined. Normal agents `propose`; the gatekeeper (the personal session for now)
`commit`s. `add` is propose+commit in one step for the gatekeeper.

Seats: a stable agent role/address. Memories can belong to a seat, so
whatever model sits in that seat later inherits them.

Projects carry an intent and an optional parent, so `intent <project>` prints the chain
from the task up to the top goal (the anti-scope-creep check).

All text goes in with --text or, safer from a shell, --text-file.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = Path(os.environ.get("AI_MEMORY_DB", ROOT / "data" / "memory.db"))
LAYERS = ("user", "project", "experience", "knowledge")
STATUSES = ("proposed", "trusted", "uncertain", "deprecated", "quarantined")
LIVE = ("trusted", "uncertain")  # what search/brief show by default
DEFAULT_USER = "owner"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY, display_name TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'owner',
  created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS seats (
  id TEXT PRIMARY KEY, role TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, intent TEXT NOT NULL,
  parent_id TEXT REFERENCES projects(id), status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS memories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL REFERENCES users(id),
  seat_id TEXT REFERENCES seats(id),
  project_id TEXT REFERENCES projects(id),
  layer TEXT NOT NULL CHECK (layer IN ('user','project','experience','knowledge')),
  content TEXT NOT NULL,
  tags TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL CHECK (status IN ('proposed','trusted','uncertain','deprecated','quarantined')),
  source TEXT NOT NULL DEFAULT '',
  proposed_by TEXT NOT NULL,
  approved_by TEXT,
  status_reason TEXT,
  supersedes INTEGER REFERENCES memories(id),
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL, last_used_at TEXT);
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
  content, tags, content='memories', content_rowid='id');
CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
  INSERT INTO memories_fts(rowid, content, tags) VALUES (new.id, new.content, new.tags); END;
CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE OF content, tags ON memories BEGIN
  INSERT INTO memories_fts(memories_fts, rowid, content, tags) VALUES ('delete', old.id, old.content, old.tags);
  INSERT INTO memories_fts(rowid, content, tags) VALUES (new.id, new.content, new.tags); END;
CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
  INSERT INTO memories_fts(memories_fts, rowid, content, tags) VALUES ('delete', old.id, old.content, old.tags); END;
CREATE TABLE IF NOT EXISTS archive (
  id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, channel TEXT NOT NULL,
  direction TEXT NOT NULL CHECK (direction IN ('in','out')), author TEXT NOT NULL,
  message_id TEXT, content TEXT NOT NULL);
CREATE TRIGGER IF NOT EXISTS archive_no_update BEFORE UPDATE ON archive BEGIN
  SELECT RAISE(ABORT, 'archive is append-only'); END;
CREATE TRIGGER IF NOT EXISTS archive_no_delete BEFORE DELETE ON archive BEGIN
  SELECT RAISE(ABORT, 'archive is append-only'); END;
CREATE TABLE IF NOT EXISTS audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, actor TEXT NOT NULL,
  action TEXT NOT NULL, target TEXT NOT NULL, detail TEXT NOT NULL DEFAULT '');
CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit BEGIN
  SELECT RAISE(ABORT, 'audit is append-only'); END;
CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit BEGIN
  SELECT RAISE(ABORT, 'audit is append-only'); END;
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def est(ts: str | None) -> str:
    """Storage is UTC; display is 12-hour in the AI_MEMORY_TZ zone (default America/New_York),
    e.g. 'Sep 30 9:19 PM'. Without a tz database the machine's local zone is used."""
    if not ts:
        return "-"
    d = datetime.fromisoformat(ts)
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    try:
        from zoneinfo import ZoneInfo
        d = d.astimezone(ZoneInfo(os.environ.get("AI_MEMORY_TZ", "America/New_York")))
    except Exception:
        d = d.astimezone()
    return d.strftime("%b %d").replace(" 0", " ") + " " + d.strftime("%I:%M %p").lstrip("0")


def connect() -> sqlite3.Connection:
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA)
    if not con.execute("SELECT 1 FROM users WHERE id=?", (DEFAULT_USER,)).fetchone():
        con.execute("INSERT INTO users VALUES (?,?,?,?)", (DEFAULT_USER, "Owner", "owner", now()))
        con.commit()
    return con


def audit(con, actor, action, target, detail=""):
    con.execute("INSERT INTO audit(at,actor,action,target,detail) VALUES (?,?,?,?,?)",
                (now(), actor, action, str(target), detail))


def read_text(args) -> str:
    if getattr(args, "text_file", None):
        text = Path(args.text_file).read_text(encoding="utf-8")
    elif getattr(args, "text", None):
        text = args.text
    else:
        sys.exit("give --text or --text-file")
    text = text.strip()
    if not text:
        sys.exit("empty text refused")
    return text


def show(rows, verbose=False):
    if not rows:
        print("(nothing)")
    for r in rows:
        where = "/".join(x for x in (r["layer"], r["project_id"], r["seat_id"]) if x)
        flag = "" if r["status"] == "trusted" else f" [{r['status']}]"
        print(f"#{r['id']} ({where}){flag} [{est(r['created_at'])}] {r['content']}")
        if verbose:
            print(f"    tags={r['tags'] or '-'} source={r['source'] or '-'} by={r['proposed_by']} "
                  f"saved={est(r['created_at'])} used={est(r['last_used_at'])}")


# ---- commands ---------------------------------------------------------------

CLOCK_RE = re.compile(r"\b\d{1,2}:\d{2}(?:\s*[AaPp]\.?[Mm]\.?)?")


def cmd_add(args, *, commit: bool):
    con = connect()
    text = read_text(args)
    if args.layer not in LAYERS:
        sys.exit(f"layer must be one of {LAYERS}")
    if args.project and not con.execute("SELECT 1 FROM projects WHERE id=?", (args.project,)).fetchone():
        sys.exit(f"unknown project {args.project}; create it with `project add` first")
    if args.seat and not con.execute("SELECT 1 FROM seats WHERE id=?", (args.seat,)).fetchone():
        sys.exit(f"unknown seat {args.seat}; create it with `seat add` first")
    dup = con.execute("SELECT id FROM memories WHERE content=? AND status IN ('proposed','trusted','uncertain')",
                      (text,)).fetchone()
    if dup:
        print(f"already saved as #{dup['id']}")
        return
    status = (args.status or "trusted") if commit else "proposed"
    t = now()
    cur = con.execute(
        "INSERT INTO memories(user_id,seat_id,project_id,layer,content,tags,status,source,proposed_by,"
        "approved_by,supersedes,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (args.user, args.seat, args.project, args.layer, text, args.tags or "", status, args.source or "",
         args.by, args.by if commit else None, args.supersedes, t, t))
    mid = cur.lastrowid
    if args.supersedes:
        con.execute("UPDATE memories SET status='deprecated', status_reason=?, updated_at=? WHERE id=?",
                    (f"superseded by #{mid}", t, args.supersedes))
    audit(con, args.by, "add" if commit else "propose", mid, args.layer)
    con.commit()
    print(f"{'saved' if commit else 'proposed'} #{mid} ({status}) at {est(t)}")
    typed = CLOCK_RE.findall(text)
    if typed:
        print(f"WARNING: the text has a typed time ({', '.join(typed)}). The real save time is {est(t)}, "
              "stamped automatically. Don't type the current time into a memory; check it or drop it.")


def cmd_commit(args):
    con = connect()
    row = con.execute("SELECT status FROM memories WHERE id=?", (args.id,)).fetchone()
    if not row:
        sys.exit(f"no memory #{args.id}")
    if row["status"] != "proposed":
        sys.exit(f"#{args.id} is {row['status']}, not proposed")
    con.execute("UPDATE memories SET status=?, approved_by=?, updated_at=? WHERE id=?",
                (args.status, args.by, now(), args.id))
    audit(con, args.by, "commit", args.id, args.status)
    con.commit()
    print(f"#{args.id} -> {args.status}")


def cmd_status(args):
    con = connect()
    if args.status not in STATUSES:
        sys.exit(f"status must be one of {STATUSES}")
    if not con.execute("SELECT 1 FROM memories WHERE id=?", (args.id,)).fetchone():
        sys.exit(f"no memory #{args.id}")
    con.execute("UPDATE memories SET status=?, status_reason=?, updated_at=? WHERE id=?",
                (args.status, args.reason, now(), args.id))
    audit(con, args.by, "status", args.id, f"{args.status}: {args.reason}")
    con.commit()
    print(f"#{args.id} -> {args.status}")


def _fts_query(q: str) -> str:
    words = [w for w in "".join(c if c.isalnum() else " " for c in q).split() if len(w) > 1]
    return " OR ".join(f'"{w}"*' for w in words)


def search(con, q, layer=None, statuses=LIVE, limit=10, project=None):
    fq = _fts_query(q)
    if not fq:
        return []
    sql = ("SELECT m.* FROM memories_fts f JOIN memories m ON m.id=f.rowid WHERE memories_fts MATCH ? "
           f"AND m.status IN ({','.join('?' * len(statuses))})")
    params = [fq, *statuses]
    if layer:
        sql += " AND m.layer=?"; params.append(layer)
    if project:
        sql += " AND m.project_id=?"; params.append(project)
    sql += " ORDER BY bm25(memories_fts), m.updated_at DESC LIMIT ?"
    params.append(limit)
    rows = con.execute(sql, params).fetchall()
    if rows:
        con.execute(f"UPDATE memories SET last_used_at=? WHERE id IN ({','.join('?' * len(rows))})",
                    (now(), *[r["id"] for r in rows]))
        con.commit()
    return rows


def cmd_search(args):
    con = connect()
    statuses = STATUSES if args.all else LIVE
    show(search(con, args.query, args.layer, statuses, args.limit, args.project), args.verbose)


def cmd_list(args):
    con = connect()
    sql = "SELECT * FROM memories WHERE 1=1"; params = []
    if args.layer:
        sql += " AND layer=?"; params.append(args.layer)
    if args.status:
        sql += " AND status=?"; params.append(args.status)
    elif not args.all:
        sql += f" AND status IN ({','.join('?' * len(LIVE))})"; params += LIVE
    if args.project:
        sql += " AND project_id=?"; params.append(args.project)
    if args.days:
        sql += " AND created_at>=?"
        params.append((datetime.now(timezone.utc) - timedelta(days=args.days)).isoformat(timespec="seconds"))
    sql += " ORDER BY id DESC LIMIT ?"; params.append(args.limit)
    show(con.execute(sql, params).fetchall(), args.verbose)


def intent_chain(con, pid):
    chain, seen = [], set()
    while pid and pid not in seen:
        seen.add(pid)
        p = con.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
        if not p:
            break
        chain.append(p); pid = p["parent_id"]
    return chain


def cmd_brief(args):
    """What a fresh session (or a new model in the seat) loads first."""
    con = connect()
    print("=== ABOUT THE OWNER ===")
    show(con.execute("SELECT * FROM memories WHERE layer='user' AND status IN ('trusted','uncertain') "
                     "AND user_id=? ORDER BY id", (args.user,)).fetchall())
    print("\n=== PROJECTS (intent chain, top goal last) ===")
    projects = con.execute("SELECT * FROM projects WHERE status='active' ORDER BY id").fetchall()
    if not projects:
        print("(none)")
    for p in projects:
        chain = " -> ".join(f"{x['name']}: {x['intent']}" for x in intent_chain(con, p["id"]))
        print(f"[{p['id']}] {chain}")
        for m in con.execute("SELECT * FROM memories WHERE project_id=? AND status IN ('trusted','uncertain') "
                             "ORDER BY id DESC LIMIT ?", (p["id"], args.per_project)).fetchall():
            print(f"    #{m['id']} {m['content']}")
    print("\n=== RECENT EXPERIENCE (what worked / failed) ===")
    show(con.execute("SELECT * FROM memories WHERE layer='experience' AND status IN ('trusted','uncertain') "
                     "ORDER BY id DESC LIMIT ?", (args.recent,)).fetchall())
    if args.seat:
        print(f"\n=== SEAT {args.seat} ===")
        show(con.execute("SELECT * FROM memories WHERE seat_id=? AND status IN ('trusted','uncertain') "
                         "ORDER BY id", (args.seat,)).fetchall())
    pend = con.execute("SELECT COUNT(*) FROM memories WHERE status='proposed'").fetchone()[0]
    quar = con.execute("SELECT COUNT(*) FROM memories WHERE status='quarantined'").fetchone()[0]
    last = con.execute("SELECT at FROM archive ORDER BY id DESC LIMIT 1").fetchone()
    print(f"\n{pend} proposed waiting for the gatekeeper | {quar} quarantined | "
          f"last chat logged {est(last['at']) if last else '-'}")


def archive_message(direction: str, author: str, message_id: str | None, text: str,
                    channel: str = "chat:dm", at: str | None = None) -> bool:
    """Append one chat message to the raw archive. Skips a message_id already logged in the
    same direction, so the bot can call this on every read without duplicates. `at` is the
    message's own send time (ISO, any offset); without it the time of logging is used.
    Returns True if added."""
    text = (text or "").strip()
    if not text or direction not in ("in", "out"):
        return False
    if at:
        at = datetime.fromisoformat(at).astimezone(timezone.utc).isoformat(timespec="seconds")
    con = connect()
    if message_id and con.execute("SELECT 1 FROM archive WHERE message_id=? AND direction=?",
                                  (str(message_id), direction)).fetchone():
        return False
    con.execute("INSERT INTO archive(at,channel,direction,author,message_id,content) VALUES (?,?,?,?,?,?)",
                (at or now(), channel, direction, author, str(message_id) if message_id else None, text))
    con.commit()
    return True


def cmd_log(args):
    text = read_text(args)
    added = archive_message(args.direction, args.author, args.message_id, text, args.channel)
    print(f"logged {args.direction} ({len(text)} chars)" if added else "already logged (same message id)")


def cmd_history(args):
    con = connect()
    rows = con.execute("SELECT * FROM archive WHERE content LIKE ? ORDER BY id DESC LIMIT ?",
                       (f"%{args.contains or ''}%", args.limit)).fetchall()
    for r in reversed(rows):
        print(f"[{est(r['at'])}] {r['author']} ({r['direction']}): {r['content'][:500]}")


def cmd_project(args):
    con = connect()
    t = now()
    if args.action == "add":
        if args.parent and not con.execute("SELECT 1 FROM projects WHERE id=?", (args.parent,)).fetchone():
            sys.exit(f"unknown parent {args.parent}")
        con.execute("INSERT INTO projects VALUES (?,?,?,?,?,?,?)",
                    (args.id, args.name or args.id, args.intent, args.parent, "active", t, t))
        audit(con, args.by, "project_add", args.id, args.intent)
    elif args.action == "set":
        fields = {k: v for k, v in (("name", args.name), ("intent", args.intent),
                                    ("parent_id", args.parent), ("status", args.status)) if v}
        if not fields:
            sys.exit("nothing to change")
        con.execute(f"UPDATE projects SET {', '.join(k + '=?' for k in fields)}, updated_at=? WHERE id=?",
                    (*fields.values(), t, args.id))
        audit(con, args.by, "project_set", args.id, json.dumps(fields))
    con.commit()
    for p in intent_chain(con, args.id):
        print(f"{p['id']}: {p['intent']} ({p['status']})")


def cmd_projects(args):
    con = connect()
    for p in con.execute("SELECT * FROM projects ORDER BY status, id").fetchall():
        print(f"[{p['id']}] {p['name']} ({p['status']}) parent={p['parent_id'] or '-'}: {p['intent']}")


def cmd_intent(args):
    con = connect()
    chain = intent_chain(con, args.id)
    if not chain:
        sys.exit(f"unknown project {args.id}")
    print("Refocus: is the current work still serving this chain?")
    for depth, p in enumerate(chain):
        print("  " * depth + f"{p['name']}: {p['intent']}")


def cmd_seat(args):
    con = connect()
    if args.action == "add":
        con.execute("INSERT INTO seats VALUES (?,?,?,?)", (args.id, args.role, args.description or "", now()))
        audit(con, args.by, "seat_add", args.id, args.role)
        con.commit()
    for s in con.execute("SELECT * FROM seats ORDER BY id").fetchall():
        n = con.execute("SELECT COUNT(*) FROM memories WHERE seat_id=? AND status IN ('trusted','uncertain')",
                        (s["id"],)).fetchone()[0]
        print(f"{s['id']} ({s['role']}) {n} memories: {s['description']}")


def cmd_rules(args):
    """The rules of one seat only. Each project is its own seat; rules never carry over."""
    con = connect()
    if not con.execute("SELECT 1 FROM seats WHERE id=?", (args.seat,)).fetchone():
        sys.exit(f"unknown seat {args.seat}; see `seat list`")
    rows = con.execute("SELECT * FROM memories WHERE seat_id=? AND status IN ('trusted','uncertain') "
                       "AND (',' || tags || ',') LIKE '%,rule,%' ORDER BY id", (args.seat,)).fetchall()
    print(f"=== RULES for {args.seat} (only these apply; no other seat's rules) ===")
    show(rows)


def cmd_export(args):
    """Portable JSONL dump of every table, for the move to PostgreSQL."""
    con = connect()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with out.open("w", encoding="utf-8") as f:
        for table in ("users", "seats", "projects", "memories", "archive", "audit"):
            for r in con.execute(f"SELECT * FROM {table} ORDER BY rowid"):
                f.write(json.dumps({"table": table, "row": dict(r)}, ensure_ascii=False) + "\n"); n += 1
    print(f"exported {n} rows to {out}")


def cmd_purge(args):
    """Real deletion. Only when the owner explicitly asks for a memory to be erased."""
    con = connect()
    if not args.owner_request:
        sys.exit("purge needs --owner-request \"<what the owner said>\"; use `status ... deprecated` otherwise")
    row = con.execute("SELECT content FROM memories WHERE id=?", (args.id,)).fetchone()
    if not row:
        sys.exit(f"no memory #{args.id}")
    con.execute("UPDATE memories SET supersedes=NULL WHERE supersedes=?", (args.id,))
    con.execute("DELETE FROM memories WHERE id=?", (args.id,))
    audit(con, "owner", "purge", args.id, args.owner_request)
    con.commit()
    print(f"#{args.id} erased")


def main():
    p = argparse.ArgumentParser(prog="mem")
    p.add_argument("--by", default="personal-ai", help="actor recorded in the audit log")
    p.add_argument("--user", default=DEFAULT_USER)
    sub = p.add_subparsers(dest="cmd", required=True)

    def text_opts(sp):
        sp.add_argument("--text"); sp.add_argument("--text-file")

    for name in ("add", "propose"):
        s = sub.add_parser(name); text_opts(s)
        s.add_argument("--layer", required=True, choices=LAYERS)
        s.add_argument("--tags"); s.add_argument("--project"); s.add_argument("--seat")
        s.add_argument("--source"); s.add_argument("--supersedes", type=int)
        if name == "add":
            s.add_argument("--status", choices=("trusted", "uncertain"))
    s = sub.add_parser("commit"); s.add_argument("id", type=int)
    s.add_argument("--status", default="trusted", choices=("trusted", "uncertain"))
    s = sub.add_parser("status"); s.add_argument("id", type=int); s.add_argument("status")
    s.add_argument("--reason", required=True)
    s = sub.add_parser("search"); s.add_argument("query"); s.add_argument("--layer")
    s.add_argument("--project"); s.add_argument("--limit", type=int, default=10)
    s.add_argument("--all", action="store_true"); s.add_argument("-v", "--verbose", action="store_true")
    s = sub.add_parser("list"); s.add_argument("--layer"); s.add_argument("--status")
    s.add_argument("--project"); s.add_argument("--days", type=int); s.add_argument("--limit", type=int, default=30)
    s.add_argument("--all", action="store_true"); s.add_argument("-v", "--verbose", action="store_true")
    s = sub.add_parser("brief"); s.add_argument("--seat"); s.add_argument("--recent", type=int, default=8)
    s.add_argument("--per-project", type=int, default=5)
    s = sub.add_parser("log"); text_opts(s); s.add_argument("--direction", required=True, choices=("in", "out"))
    s.add_argument("--author", required=True); s.add_argument("--message-id")
    s.add_argument("--channel", default="chat:dm")
    s = sub.add_parser("history"); s.add_argument("--contains"); s.add_argument("--limit", type=int, default=20)
    s = sub.add_parser("project"); s.add_argument("action", choices=("add", "set")); s.add_argument("id")
    s.add_argument("--name"); s.add_argument("--intent"); s.add_argument("--parent"); s.add_argument("--status")
    sub.add_parser("projects")
    s = sub.add_parser("intent"); s.add_argument("id")
    s = sub.add_parser("seat"); s.add_argument("action", choices=("add", "list")); s.add_argument("id", nargs="?")
    s.add_argument("--role"); s.add_argument("--description")
    s = sub.add_parser("rules"); s.add_argument("seat")
    s = sub.add_parser("export"); s.add_argument("--out", default=str(ROOT / "data" / "export.jsonl"))
    s = sub.add_parser("purge"); s.add_argument("id", type=int); s.add_argument("--owner-request")

    args = p.parse_args()
    if args.cmd == "project" and args.action == "add" and not args.intent:
        p.error("project add needs --intent")
    if args.cmd == "seat" and args.action == "add" and not (args.id and args.role):
        p.error("seat add needs an id and --role")
    try:
        {"add": lambda a: cmd_add(a, commit=True), "propose": lambda a: cmd_add(a, commit=False),
         "commit": cmd_commit, "status": cmd_status, "search": cmd_search, "list": cmd_list,
         "brief": cmd_brief, "log": cmd_log, "history": cmd_history, "project": cmd_project,
         "projects": cmd_projects, "intent": cmd_intent, "seat": cmd_seat, "rules": cmd_rules, "export": cmd_export,
         "purge": cmd_purge}[args.cmd](args)
    except sqlite3.IntegrityError as e:
        sys.exit(f"refused: {e}")


if __name__ == "__main__":
    main()
