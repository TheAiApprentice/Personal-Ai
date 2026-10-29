"""gpu_time -- a signed, append-only GPU-time mailbox between an agent and the host system that owns the GPUs.

This one file is the whole channel, both ways. The agent asks for GPU time with it, and every reply
from the host side (acknowledgment, "you're clear" grant, 5-minute warning, owner-start notice,
revoke, release confirmation) is written by the host through these same functions and read back by
the agent through these same functions. Standard library only. It reads and writes only inside the
mailbox folder and never touches a token.

    python gpu_time.py init                                   # once: folders, config, keys
    python gpu_time.py request  --minutes 90 --why "train a model" [--gpus all] [--request-id ID]
    python gpu_time.py cancel   --request-id ID
    python gpu_time.py check-grant --allocation ID --need-minutes 30   # exit 0 = go (a preview)
    python gpu_time.py run      --allocation ID [--need-minutes N] -- <command ...>
    python gpu_time.py register-pid --allocation ID --pid N
    python gpu_time.py release  --allocation ID [--note "..."]
    python gpu_time.py status   [--side agent|host] [--json]
    python gpu_time.py inbox    --side agent|host [--mark-read] [--all]
    python gpu_time.py watch    --side agent|host --seconds 3600 [--interval 10]
    python gpu_time.py verify   [--full]                      # signatures + chain audit
    python gpu_time.py probe                                  # GPU telemetry (nvidia-smi)

Mailbox (default <repo>/data/gpu_time, override with GPU_TIME_ROOT):
    config.json        written once by init, never rewritten
    keys/host.key, keys/agent.key   written once by init (32 random bytes, hex)
    events/00000001.json ...        ONE event per file, created exclusively (write to tmp/,
                                    then rename; the rename refuses an existing name), never
                                    rewritten, never deleted. The state is the fold of these
                                    files; consuming a message = appending a `receipt` event.
    lock               a byte-range lock held only while appending; the OS drops it when the
                       process dies, so there is no stale lock to clean up.

Every event carries: protocol, seq (= its file name), event_id, type, by (host|agent), at (UTC ISO),
to, request_id, allocation_id, body, prev (sha256 of the previous event file's bytes), code (sha256
of the gpu_time.py that wrote it) and sig (HMAC-SHA256 with the writer side's key). The fold ignores
an event whose signature, seq, chain link or signer is wrong, and applies a valid event only when
its transition is legal in the state built from the events before it, so a delayed, replayed or
stale operation cannot change a newer allocation. Authentication is an identity reference on one
machine account: it stops unsigned, mis-signed and wrong-side writes; it cannot stop a hostile
process running as the same user that reads the key files (stated, not hidden).

Rules the rule book enforces (all decided under the mailbox lock):
  * A pending owner start order closes admission: no new grant while one is pending, and no new
    agent work on a granted allocation (check_grant refuses; `run` admits a job only through a
    signed `admit` event that is refused while an order is pending or when the job would outlive
    the effective deadline = min(grant end, owner deadline)).
  * An owner start stays PENDING until its job is actually dispatched. The dispatch can only be
    claimed while every allocation is verified free, and "done" needs that claim.
  * Per-GPU ownership: each GPU is at any moment held by the agent (an allocation not yet verified
    free), used by the host (live `host_acquire` leases), or free. The two are exclusive. Several
    agent allocations may be active at once on disjoint GPUs; a partial grant leaves the rest of
    the request outstanding.
  * Occupancy is decided by the per-GPU query (memory.used, utilization.gpu) against
    resident_block_mb / busy_util_pct; an unknown per-process value is never read as 0 MB, and a
    GPU whose numbers cannot be read is UNRESOLVED (no grant, release not verified).
  * Strict age order per GPU: a free GPU goes to the oldest waiting request that wants it; an exact
    multi-GPU request that cannot yet be fully granted gets a `reserve` hold (max reserve_s).
  * Ids are single-use: a lease, allocation or request id names exactly one acquisition, grant or
    request for ever (generated ids carry the seq of the event that created them).
  * Bounded fold: compact() writes a host-signed snapshot and MOVES covered events to archive/
    (never deleted); `verify --full` replays the whole history.

Exit codes: 0 ok, 2 usage / not initialised, 3 refused (the reason is printed), 4 verify
failed, 5 telemetry or process query failed.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import hmac
import json
import os
import re
import secrets
import subprocess
import sys
import time
import uuid

sys.dont_write_bytecode = True

PROTOCOL = 1
DEFAULT_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                            "data", "gpu_time")      # inside the repo; tests set GPU_TIME_ROOT to a temp dir
SIDES = ("host", "agent")
OWNER_GRACE_S = 300            # the agent has 5 minutes to finish up after an owner start
WARN_BEFORE_S = 300            # 5-minute warning before a grant ends
DEFAULT_ALLOWANCE_S = 120      # handoff allowance: grant ends this long before the next start
MIN_USABLE_S = 600             # a window shorter than this is reported, not granted
RESIDENT_BLOCK_MB = 2048       # a GPU using this much memory (per-GPU memory.used) is occupied
BUSY_UTIL_PCT = 60             # a GPU at or above this utilization is occupied (UNMEASURED default)
RELEASE_MARGIN_MB = 1024       # release verified if memory.used <= grant-time baseline + this
DISPATCH_LEASE_S = 420         # an owner-start dispatch claim lives this long (launcher timeout 300 s)
RESERVE_S = 600                # a GPU reserved for an older exact multi-GPU request lapses after this
ROUTE_KEY_PREFIX = "gw-"       # owner starts recorded by the host's own routes; not the agent's to retry
OWNER_ATTEMPTS_KEEP = 20       # newest failed-dispatch attempts kept on an owner start record (count kept too)
OWNER_ATTEMPT_KINDS = ("identity", "launcher_error", "launcher_refused", "launcher_exit", "unverified", "crash",
                       "dispatcher_exit", "dispatch_failed")
COMPACT_AT = 32                # a host-side append (and the tick) compacts when the live tail exceeds this.
                               # Measured (tests/load_cost_r6.py, S29): the FIRST open of each event file
                               # costs ~10-13 ms on a cold disk cache and a warm one ~0.2 ms,
                               # so a reader's worst cold load is ~(tail + 1 snapshot) first-opens.
COMPACT_KEEP = 0               # the snapshot covers every event up to the newest; readers load it + the tail
SNAPSHOT_KEEP = 3              # newest snapshots left in snapshots/; older ones are MOVED to archive/snapshots/
RETAIN_S = 7 * 24 * 3600       # a snapshot drops FINISHED records older than this (they stay in archive/):
                               # verified-free allocations, finished requests, released/expired host
                               # leases, their dedupe notes, and read messages beyond SNAPSHOT_MSGS
SNAPSHOT_MSGS = 100            # newest messages a snapshot keeps (plus unread ones inside RETAIN_S)
RETAIN_STEP_S = 3600           # the fold retires finished records at most once per this much event time
# generated ids carry the seq of the event that created them; the rule book checks it, so a
# generated id can never name a second acquisition / grant / request, with no memory needed
_GEN_ID = {"lease": re.compile(r"^cl-s(\d+)-[0-9a-f]{6}$"),
           "alloc": re.compile(r"^al-\d{12}-s(\d+)-[0-9a-f]{4}$"),
           "request": re.compile(r"^rq-\d{8}-s(\d+)-[0-9a-f]{6}$")}
NEW_ID = "@@NEW-ID@@"          # placeholder a sender uses; append() replaces it with the generated id
NO_TIME = "no set time"        # how fmt_time / fmt_when render a missing time
RECLAIM_GRACE_S = 30           # after a grant's end, registered processes are reclaimed this long later
HOST_KINDS = ("active", "reserve")
DEFAULT_VALID_H = 24           # a request not granted within this is stale
MAX_MINUTES = 24 * 60
EXIT_OK, EXIT_USAGE, EXIT_REFUSED, EXIT_VERIFY, EXIT_QUERY = 0, 2, 3, 4, 5

ALLOWED = {
    "agent": {"request", "cancel", "release", "register_pid", "admit", "receipt"},
    "host": {"ack", "grant", "no_window", "warning", "schedule_change", "expire", "revoke",
             "preempt", "release_verified", "release_unverified", "owner_start",
             "owner_start_dispatch", "owner_start_done", "owner_start_attempt", "owner_start_cancel",
             "executor_start", "executor_stop", "reserve",
             "host_acquire", "host_release",
             "status_note", "reject", "receipt"},
}
# Allocation states that still hold the GPUs until a release_verified event says otherwise.
HOLDING = ("active", "released", "revoked", "expired")
# owner_start_done result -> the owner start's terminal status. Only reachable through a
# dispatch claim, which needs every allocation verified free.
OWNER_RESULTS = {"started": "done", "already_started": "done", "gate_refused": "gate_refused",
                 "dispatch_failed": "dispatch_failed"}

_THIS_FILE = os.path.abspath(__file__)


class MailboxError(Exception):
    code = EXIT_USAGE


class Refused(MailboxError):
    code = EXIT_REFUSED


def say(*parts):
    text = " ".join(str(p) for p in parts)
    try:
        sys.stdout.write(text + "\n")
    except UnicodeEncodeError:
        sys.stdout.write(text.encode("ascii", "replace").decode("ascii") + "\n")
    sys.stdout.flush()


# ------------------------------------------------------------------ paths
def root():
    return os.path.abspath(os.environ.get("GPU_TIME_ROOT") or DEFAULT_ROOT)


def _p(*parts, base=None):
    return os.path.join(base or root(), *parts)


def code_id():
    try:
        with open(_THIS_FILE, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return "unknown"


# ------------------------------------------------------------------ clock
# The default is the real clock. Tests may set GPU_TIME_CLOCK_ORIGIN (an ISO instant),
# GPU_TIME_CLOCK_REAL0 (the real epoch second that origin maps to) and GPU_TIME_CLOCK_SCALE
# (clock seconds per real second) so several processes share one fast clock. A test clock
# is refused on the default mailbox.
def _test_clock():
    o = os.environ.get("GPU_TIME_CLOCK_ORIGIN")
    if not o:
        return None
    if os.path.normcase(root()) == os.path.normcase(os.path.abspath(DEFAULT_ROOT)):
        raise MailboxError("a test clock (GPU_TIME_CLOCK_ORIGIN) is not allowed on the default "
                           "mailbox %s" % DEFAULT_ROOT)
    return parse_iso(o), float(os.environ.get("GPU_TIME_CLOCK_REAL0") or time.time()), \
        float(os.environ.get("GPU_TIME_CLOCK_SCALE") or 1.0)


def now():
    tc = _test_clock()
    if tc:
        origin, real0, scale = tc
        return origin + _dt.timedelta(seconds=(time.time() - real0) * scale)
    return _dt.datetime.now(_dt.timezone.utc)


def clock_sleep(seconds):
    """Sleep `seconds` of clock time (shorter in real time under a scaled test clock)."""
    tc = _test_clock()
    time.sleep(max(0.0, seconds) / (tc[2] if tc else 1.0))


def parse_iso(s):
    if isinstance(s, _dt.datetime):
        d = s
    else:
        t = str(s).strip().replace(" ", "T")
        if t.endswith("Z"):
            t = t[:-1] + "+00:00"
        d = _dt.datetime.fromisoformat(t)
    if d.tzinfo is None:
        d = d.replace(tzinfo=_dt.timezone.utc)
    return d


def _ts(v):
    """An optional timestamp as an aware datetime, or None when it is missing or unreadable --
    for code that loops over many records, so one bad record never stops the others."""
    if v is None or v == "":
        return None
    try:
        return parse_iso(v)
    except (ValueError, TypeError, OverflowError):
        return None


def _grant_order(a):
    """Grant order of an allocation record: its grant generation (strictly increasing), then its id.
    Lists of allocations never follow dict order, which a snapshot does not preserve."""
    try:
        g = int(a.get("gen") or 0)
    except (TypeError, ValueError):
        g = 0
    return (g, str(a.get("allocation_id")))


def _acquire_order(l):
    """Acquisition order of a host lease record: the acquiring event's seq, then its
    time, then its id."""
    try:
        s = int(l.get("acquired_seq") or 0)
    except (TypeError, ValueError):
        s = 0
    return (s, str(l.get("acquired_at") or ""), str(l.get("lease_id")))


def _owner_deadline_of(o):
    """An owner start's deadline; if unreadable, acceptance + OWNER_GRACE_S; if that is
    unreadable too, the epoch (already passed: the most conservative answer for the holder)."""
    d = _ts(o.get("deadline"))
    if d is not None:
        return d
    a = _ts(o.get("accepted_at"))
    return (a + _dt.timedelta(seconds=OWNER_GRACE_S)) if a else _dt.datetime(1970, 1, 1, tzinfo=_dt.timezone.utc)


def iso(d):
    return parse_iso(d).astimezone(_dt.timezone.utc).isoformat()


def _tz_name():
    return os.environ.get("GPU_TIME_TZ") or "America/New_York"


def eastern():
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(_tz_name())
    except Exception:                                        # noqa: BLE001
        return None


def local(d):
    tz = eastern()
    d = parse_iso(d)
    return d.astimezone(tz) if tz else d.astimezone()


def fmt_time(d):
    """'11:00 PM EDT' (12-hour, in the GPU_TIME_TZ zone, default America/New_York, with the zone name). A missing time (None or '') is
    rendered as NO_TIME, never parsed (an optional timestamp must not crash a message)."""
    if d is None or d == "":
        return NO_TIME
    t = local(d)
    return "%s %s" % (t.strftime("%I:%M %p").lstrip("0"), t.strftime("%Z") or "ET")


def fmt_when(d, ref=None):
    """'11:00 PM EDT' today, else 'Sun 3:00 AM EST'. A missing time is NO_TIME (see fmt_time)."""
    if d is None or d == "":
        return NO_TIME
    t, r = local(d), local(ref or now())
    return fmt_time(d) if t.date() == r.date() else "%s %s" % (t.strftime("%a"), fmt_time(d))


def fmt_dur(seconds):
    s = int(max(0, round(seconds)))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return "%dh %dm" % (h, m)
    if m:
        return "%dm %ds" % (m, sec) if sec and m < 10 else "%dm" % m
    return "%ds" % sec


# ------------------------------------------------------------------ init / keys / config
def init(base=None):
    base = base or root()
    for d in ("events", "tmp", "keys"):
        os.makedirs(os.path.join(base, d), exist_ok=True)
    made = []
    cfg = os.path.join(base, "config.json")
    if not os.path.exists(cfg):
        _write_new(cfg, json.dumps({
            "protocol": PROTOCOL, "gpus": ["0", "1"], "allowance_s": DEFAULT_ALLOWANCE_S,
            "min_usable_s": MIN_USABLE_S, "owner_grace_s": OWNER_GRACE_S,
            "warn_before_s": WARN_BEFORE_S, "resident_block_mb": RESIDENT_BLOCK_MB,
            "busy_util_pct": BUSY_UTIL_PCT, "release_margin_mb": RELEASE_MARGIN_MB,
            "created_at": iso(_dt.datetime.now(_dt.timezone.utc)),
            "_what": "GPU-time mailbox settings. Written once by init; read-only after."},
            indent=1).encode("utf-8"))
        made.append(cfg)
    for side in SIDES:
        k = os.path.join(base, "keys", "%s.key" % side)
        if not os.path.exists(k):
            _write_new(k, secrets.token_hex(32).encode("ascii"))
            made.append(k)
    lk = os.path.join(base, "lock")
    if not os.path.exists(lk):
        _write_new(lk, b"\0")
        made.append(lk)
    return made


_CFG_CACHE = {}


def config(base=None):
    """config.json (written once by init). Cached per path by (mtime_ns, size), so the rule book
    does not reopen it for every request/grant/reserve event it replays (profiled: it did)."""
    p = _p("config.json", base=base)
    try:
        s = os.stat(p)
    except OSError:
        raise MailboxError("mailbox not initialised at %s (run: gpu_time.py init)" % (base or root()))
    sig = (s.st_mtime_ns, s.st_size)
    hit = _CFG_CACHE.get(p)
    if hit is None or hit[0] != sig:
        with open(p, encoding="utf-8") as f:
            hit = (sig, f.read())
        _CFG_CACHE[p] = hit
    return json.loads(hit[1])


def _key(side, base=None):
    p = _p("keys", "%s.key" % side, base=base)
    try:
        with open(p, "rb") as f:
            k = f.read().strip()
    except OSError:
        raise MailboxError("no %s key at %s (run: gpu_time.py init)" % (side, p))
    if len(k) < 32:
        raise MailboxError("%s key at %s is too short" % (side, p))
    return k


def key_fingerprint(side, base=None):
    return hashlib.sha256(_key(side, base)).hexdigest()[:16]


def _write_new(path, data):
    """Create `path` exclusively: tmp file then rename (rename never replaces on Windows,
    and os.link refuses an existing name elsewhere). Never overwrites."""
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    tmpdir = os.path.join(os.path.dirname(d), "tmp") if os.path.basename(d) == "events" else d
    os.makedirs(tmpdir, exist_ok=True)
    tmp = os.path.join(tmpdir, ".tmp-%s" % uuid.uuid4().hex)
    with open(tmp, "xb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    if os.name == "nt":
        os.rename(tmp, path)               # raises FileExistsError if path exists
    else:
        os.link(tmp, path)                 # raises FileExistsError if path exists
        os.unlink(tmp)                     # the tmp name only; the event stays


# ------------------------------------------------------------------ lock
class _Lock:
    def __init__(self, base=None, wait_s=20.0):
        self.path = _p("lock", base=base)
        self.wait_s = wait_s
        self.fd = None

    def __enter__(self):
        if not os.path.exists(self.path):
            raise MailboxError("mailbox not initialised (no lock file at %s)" % self.path)
        self.fd = os.open(self.path, os.O_RDWR)
        deadline = time.time() + self.wait_s
        while True:
            try:
                if os.name == "nt":
                    import msvcrt
                    os.lseek(self.fd, 0, 0)
                    msvcrt.locking(self.fd, msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except OSError:
                if time.time() > deadline:
                    os.close(self.fd)
                    raise MailboxError("mailbox lock busy for %.0f s" % self.wait_s)
                time.sleep(0.02)

    def __exit__(self, *exc):
        try:
            if os.name == "nt":
                import msvcrt
                os.lseek(self.fd, 0, 0)
                msvcrt.locking(self.fd, msvcrt.LK_UNLCK, 1)
        finally:
            os.close(self.fd)
        return False


# ------------------------------------------------------------------ events
def _canonical(ev):
    body = {k: v for k, v in ev.items() if k != "sig"}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _sign(ev, base=None):
    return hmac.new(_key(ev["by"], base), _canonical(ev), hashlib.sha256).hexdigest()


class Rec:
    __slots__ = ("seq", "name", "raw", "ev", "problem", "applied", "ignored")

    def __init__(self, seq, name, raw, ev, problem):
        self.seq, self.name, self.raw, self.ev, self.problem = seq, name, raw, ev, problem
        self.applied, self.ignored = False, ""


class _Recs(list):
    """The event records after the snapshot they continue (snapshot None = full history)."""
    snapshot = None


def _snap_canonical(d):
    return json.dumps({k: v for k, v in d.items() if k != "sig"}, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True).encode("ascii")


def _snapshot_names(base=None):
    d = _p("snapshots", base=base)
    try:
        return sorted((n for n in os.listdir(d) if n.startswith("snap-") and n.endswith(".json")), reverse=True)
    except OSError:
        return []


def latest_snapshot(base=None):
    """The newest snapshot whose host signature verifies, else None (an invalid one is skipped).
    A snapshot a compaction moves to archive/snapshots/ while this reads is not mistaken for an
    invalid one: the listing is taken again (bounded)."""
    d = _p("snapshots", base=base)
    try:
        k = _key("host", base)
    except MailboxError:
        return None
    for attempt in range(8):
        names = _snapshot_names(base)
        moved = False
        for n in names:
            try:
                with open(os.path.join(d, n), encoding="utf-8") as f:
                    snap = json.load(f)
            except (FileNotFoundError, PermissionError):
                moved = True                                 # moved by a compaction right now: list again
                break
            except Exception:                                # noqa: BLE001  unreadable: skip it
                continue
            try:
                good = hmac.new(k, _snap_canonical(snap), hashlib.sha256).hexdigest()
                if hmac.compare_digest(good, str(snap.get("sig") or "")) and snap.get("protocol") == PROTOCOL \
                        and "retain_step_s" in snap:
                    # only a current-format snapshot (retention inside the fold) continues exactly like a full
                    # replay; an older-format one is skipped, so the reader replays the full history instead
                    return snap
            except Exception:                                # noqa: BLE001
                continue
        if not moved:
            return None
        time.sleep(0.02)
    return None


def _has_event_files(d):
    """True if directory `d` holds at least one event file (stops at the first; archive/ is large)."""
    try:
        with os.scandir(d) as it:
            for e in it:
                if e.name.endswith(".json") and e.name[:-5].isdigit():
                    return True
    except OSError:
        return False
    return False


def _read_one(paths):
    """Bytes of the first of `paths` that can be read (an event file a compaction moved from
    events/ to archive/ after it was listed is read from archive/). Raises FileNotFoundError when
    none can be read, so the caller reads its listing again."""
    last = None
    for p in ([paths] if isinstance(paths, str) else list(paths)):
        try:
            with open(p, "rb") as f:
                return f.read()
        except (FileNotFoundError, PermissionError) as e:
            last = e
    raise FileNotFoundError("event file moved while being read: %s (%s)" % (paths, last))


def _read_files(paths_names, prev, base):
    out, keys = [], {}
    for path, n in paths_names:
        seq = int(n[:-5])
        raw = _read_one(path)
        ev, problem = None, ""
        try:
            ev = json.loads(raw.decode("utf-8"))
            if not isinstance(ev, dict):
                raise ValueError("not an object")
        except Exception as e:                               # noqa: BLE001
            problem = "unparsable (%s)" % type(e).__name__
            ev = None
        if ev is not None:
            problem = _verify_event(ev, seq, prev, keys, base)
        out.append(Rec(seq, n, raw, ev, problem))
        prev = hashlib.sha256(raw).hexdigest()
    return out


def read_events(base=None, full=False):
    """Event records to fold. Default: the newest valid snapshot (attached as .snapshot) plus the
    events after it. full=True: every event ever written (archive/ + events/), no snapshot.
    A compaction running at the same moment is tolerated by re-reading (bounded retries)."""
    d = _p("events", base=base)
    if not os.path.isdir(d):
        raise MailboxError("mailbox not initialised at %s (run: gpu_time.py init)" % (base or root()))
    if full:
        return _read_full(d, _p("archive", base=base), base)
    ad = _p("archive", base=base)
    for attempt in range(8):
        before = _snapshot_names(base)
        snap = latest_snapshot(base)
        if snap is None and _has_event_files(ad):
            return read_events(base, full=True)              # no valid snapshot: replay the whole history
        floor = int(snap["seq"]) if snap else 0
        try:
            names = sorted(n for n in os.listdir(d) if n.endswith(".json") and n[:-5].isdigit() and int(n[:-5]) > floor)
            recs = _Recs(_read_files([(os.path.join(d, n), n) for n in names], snap["anchor"] if snap else "", base))
        except (FileNotFoundError, PermissionError):       # Windows: a file being moved by a compaction
            time.sleep(0.05)
            continue
        if _snapshot_names(base) != before:
            # a compaction finished while this read ran: with an empty tail the old snapshot
            # would otherwise be returned without the events the new one covers (stale state)
            time.sleep(0.02)
            continue
        if snap and recs and recs[0].problem.startswith("chain link"):
            if latest_snapshot(base) != snap:
                time.sleep(0.05)                             # a compaction finished meanwhile: read again
                continue
            return read_events(base, full=True)              # the snapshot does not continue: replay everything
        recs.snapshot = snap
        return recs
    return read_events(base, full=True)


def _event_names(d):
    try:
        return [n for n in os.listdir(d) if n.endswith(".json") and n[:-5].isdigit()]
    except (FileNotFoundError, NotADirectoryError):
        return []


FULL_READ_ATTEMPTS = 60


def _read_full(d, ad, base):
    """Every event ever written (archive/ + events/), as one consistent history, without the
    mailbox lock (a reader must never hold up the writers). A compaction can move files from
    events/ to archive/ at any moment, so:
      1. the snapshot list is read first: the newest snapshot's seq is a floor every complete
         history reaches (the events it covers existed before the listings below);
      2. events/ is listed BEFORE archive/: an event file only ever moves events/ -> archive/ and
         archive/ never loses one, so every event that existed at the events/ listing is in one of
         the two listings;
      3. a file listed in events/ that has moved by the time it is opened is read from archive/;
      4. the listing is accepted only when its seqs run 1..N with no gap and N >= the floor;
         otherwise everything is read again. A gap or short floor that is IDENTICAL on two reads in a
         row is not a race but the real content of the folders: it is returned, and the chain and
         seq checks report it as invalid. If no read is accepted, MailboxError -- never a short
         history."""
    prev_key = None
    for attempt in range(FULL_READ_ATTEMPTS):
        snaps = _snapshot_names(base)                        # newest first
        floor = int(snaps[0][5:-5]) if snaps else 0
        ev_names = _event_names(d)                           # FIRST events/ ...
        ar_names = _event_names(ad)                          # ... THEN archive/
        where = {}
        for n in ar_names:
            where[int(n[:-5])] = ([os.path.join(ad, n)], n)
        for n in ev_names:
            where[int(n[:-5])] = ([os.path.join(d, n), os.path.join(ad, n)], n)
        seqs = sorted(where)
        complete = seqs == list(range(1, len(seqs) + 1)) and (seqs[-1] if seqs else 0) >= floor
        key = (tuple(sorted(ev_names)), tuple(sorted(ar_names)), tuple(snaps))
        if not complete and key != prev_key:
            prev_key = key
            time.sleep(0.02)
            continue                                         # a compaction moved files between the listings
        try:
            return _Recs(_read_files([(where[s][0], where[s][1]) for s in seqs], "", base))
        except (FileNotFoundError, PermissionError):
            prev_key = None
            time.sleep(0.02)                                 # moved out of both listed places: list again
    raise MailboxError("could not read a consistent full event history in %d attempts (files kept "
                       "moving); nothing short is returned" % FULL_READ_ATTEMPTS)


def _verify_event(ev, seq, prev, keys, base):
    if ev.get("protocol") != PROTOCOL:
        return "protocol %r" % ev.get("protocol")
    if ev.get("seq") != seq:
        return "seq %r does not match its file %08d" % (ev.get("seq"), seq)
    if ev.get("prev") != prev:
        return "chain link does not match the previous event file"
    by = ev.get("by")
    if by not in SIDES:
        return "unknown signer %r" % by
    if ev.get("type") not in ALLOWED[by]:
        return "%s may not write %r events" % (by, ev.get("type"))
    if by not in keys:
        try:
            keys[by] = _key(by, base)
        except MailboxError as e:
            return str(e)
    good = hmac.new(keys[by], _canonical(ev), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(good, str(ev.get("sig") or "")):
        return "bad signature"
    return ""


# ------------------------------------------------------------------ state (the fold)
class State:
    def __init__(self):
        self.requests = {}       # request_id -> dict
        self.allocs = {}         # allocation_id -> dict
        self.owner_starts = {}   # key -> dict
        self.executor = None     # the newest retry executor record (pid, created, started_at, stopped_at)
        self.host_leases = {}    # lease_id -> the host's declared use / reservation of specific GPUs
        self.reservations = []   # GPU reservations for older exact multi-GPU requests, in order
        self.last_grant_at = {}  # gpu -> time of the newest grant that included it
        self.released_lease_ids = {}     # ended host leases retired from host_leases: id -> released_at (RETAIN_S)
        self.retain_mark = None  # cutoff of the newest retention step the fold applied (ISO), None = none yet
        self.used_ids = {"lease": set(), "request": set(), "alloc": set()}   # digests of non-generated ids; never retired
        self.snapshot_seq = 0    # the snapshot this state was folded from (0 = none)
        self.pruned = {}         # finished records snapshots have left out so far (counts; they stay in archive/)
        self.gen = 0             # allocations ever granted (stale-grant guard)
        self.current = None      # newest allocation id (informational only: several may be active)
        self.messages = []       # applied events that carry `to`
        self.receipts = {}       # (event_id, side) -> {"delivered": at, "read": at}
        self.notes = set()       # dedupe keys of status_note / no_window / reject
        self.events = []         # applied events in order
        self.invalid = []        # (seq, problem)
        self.ignored = []        # (seq, why)

    # -------- queries
    def owner_pending(self):
        """Owner start orders not yet dispatched (or closed by a gate refusal), oldest first."""
        return sorted((o for o in self.owner_starts.values() if o["status"] == "pending"),
                      key=lambda o: (str(o.get("accepted_at") or ""), str(o.get("key"))))

    def owner_pending_retryable(self):
        """Pending owner starts the retry executor must dispatch: all except the host's own
        route orders (key prefix ROUTE_KEY_PREFIX), which the host dispatches itself."""
        return [o for o in self.owner_pending() if not str(o["key"]).startswith(ROUTE_KEY_PREFIX)]

    def host_gpu_clear(self):
        """True when no agent allocation still holds the GPUs (every allocation verified
        free). This is the question the host asks before its own GPU work; a pending
        owner start does not close it -- the owner start is waiting for exactly this."""
        return all(a["verified_free"] for a in self.allocs.values())

    def admission_open(self, gpu=None):
        """May a NEW agent grant be issued (on `gpu`, or on some GPU when gpu is None)?
        Never while an owner start order is pending (owner priority, contract s6). Per GPU: only
        when no agent allocation still holds that GPU. host leases are judged by the rule
        book / tick at a given time (live_host_leases)."""
        if self.owner_pending():
            return False
        if gpu is None:
            return True
        return self.agent_hold(gpu) is None

    def admission_closed_why(self, gpu=None):
        if self.owner_pending():
            o = self.owner_pending()[0]
            return "an owner start order (%s, deadline %s) is pending" % (o["key"], o["deadline"])
        if gpu is not None and self.agent_hold(gpu):
            return "GPU %s is held by allocation %s (not yet verified free)" % (gpu, self.agent_hold(gpu)["allocation_id"])
        return ""

    def holding(self):
        return sorted((a for a in self.allocs.values() if not a["verified_free"]), key=_grant_order)

    def owner_deadline(self):
        """Earliest deadline of a pending owner start (aware datetime) or None."""
        p = self.owner_pending()
        return min(_owner_deadline_of(o) for o in p) if p else None

    def effective_expires(self, aid):
        """When the holder must be done: the grant's end, or a pending owner deadline if sooner.
        None = no end known (no next start was known at grant time and no owner order is pending)."""
        al = self.allocs[aid]
        e = _ts(al.get("expires"))
        ends = [e] if e else []
        od = self.owner_deadline()
        if od:
            ends.append(od)
        return min(ends) if ends else None

    # -------- per-GPU ownership
    def agent_hold(self, gpu):
        """The agent allocation that owns `gpu` (not yet verified free), or None."""
        for a in self.allocs.values():
            if not a["verified_free"] and str(gpu) in [str(g) for g in a["gpus"]]:
                return a
        return None

    def live_host_leases(self, at=None, gpu=None, check_process=True):
        at = parse_iso(at or now())
        out = []
        for l in self.host_leases.values():
            if gpu is not None and str(gpu) not in l["gpus"]:
                continue
            if lease_live(l, at, check_process):
                out.append(l)
        return sorted(out, key=_acquire_order)                # acquisition order, never dict order

    def gpu_owner(self, gpu, at=None):
        """{"agent": allocation_id} | {"host": [lease ids]} | None for one GPU."""
        a = self.agent_hold(gpu)
        if a:
            return {"agent": a["allocation_id"]}
        ls = self.live_host_leases(at, gpu)
        if ls:
            return {"host": [l["lease_id"] for l in ls]}
        return None

    def owner_targets(self):
        """Every allocation an owner start must warn: each one still holding a GPU (active, or
        ended but not verified free), in grant order (sorted by grant generation, never dict order --
        a snapshot is written with its keys in another order, and the owner_start rule compares this list)."""
        return self.holding()

    def owner_target(self):
        """The first allocation an owner start warns (compatibility; see owner_targets)."""
        t = self.owner_targets()
        return t[0] if t else None

    def live_claim(self, key, at):
        """The owner start's dispatch claim if it is still inside its lease, else None."""
        c = (self.owner_starts.get(key) or {}).get("claim")
        made = _ts(c.get("at")) if c else None
        if made and made + _dt.timedelta(seconds=int(c.get("lease_s") or DISPATCH_LEASE_S)) > parse_iso(at):
            return c
        return None

    def active_alloc(self):
        """The newest ACTIVE allocation (compatibility); see active_allocs for all of them."""
        a = self.active_allocs()
        return a[-1] if a else None

    # -------- strict age order per GPU (reservations)
    @staticmethod
    def age_key(req):
        return (str(req.get("submitted_at") or ""), str(req.get("request_id")))

    def older(self, rid_a, rid_b):
        """True if request rid_a is older than rid_b (submission time, then id)."""
        a, b = self.requests.get(rid_a), self.requests.get(rid_b)
        return bool(a and b) and self.age_key(a) < self.age_key(b)

    def active_reservation(self, gpu, at=None):
        """The live reservation on `gpu` (the newest one, if it has not lapsed, its request is still
        waiting, and nobody has been granted that GPU since it was made), else None."""
        at = parse_iso(at or now())
        rs = [r for r in self.reservations if r["gpu"] == str(gpu)]
        if not rs:
            return None
        r = rs[-1]
        req = self.requests.get(r["request_id"]) or {}
        until, made, lg = _ts(r.get("until")), _ts(r.get("at")), _ts(self.last_grant_at.get(str(gpu)))
        if until is None or made is None:
            return None                                       # an unreadable reservation holds nothing
        if until <= at or req.get("status") not in ("acked", "partial") or (lg and lg > made):
            return None
        return r

    def may_reserve_again(self, rid, gpu, at=None):
        """A request whose reservation on `gpu` LAPSED may reserve it again only after someone else
        has been granted that GPU since the lapse (first again "next time" it frees)."""
        at = parse_iso(at or now())
        mine = [r for r in self.reservations if r["gpu"] == str(gpu) and r["request_id"] == rid]
        if not mine:
            return True
        last = mine[-1]
        until = _ts(last.get("until"))
        if until is None:
            return False                                      # unreadable: never re-reserve on it
        if until > at:
            return True                                       # not lapsed (still live or superseded)
        lg = _ts(self.last_grant_at.get(str(gpu)))
        return bool(lg and lg > until)

    def active_allocs(self):
        return sorted((a for a in self.allocs.values() if a["status"] == "active"), key=_grant_order)

    def outstanding(self, req, cfg_gpus):
        """GPUs a waiting/partial request still wants: asked-for minus already granted to it."""
        wanted = cfg_gpus if req["gpus"] == ["all"] else [str(x) for x in req["gpus"]]
        got = set(req.get("granted_gpus") or [])
        return [g for g in wanted if g not in got]

    def message(self, event_id):
        for m in self.messages:
            if m["event_id"] == event_id:
                return m
        return None

    def unread(self, side):
        return [m for m in self.messages if m.get("to") == side
                and not (self.receipts.get((m["event_id"], side)) or {}).get("read")]

    def undelivered(self, side):
        out = []
        for m in self.messages:
            if m.get("to") != side:
                continue
            r = self.receipts.get((m["event_id"], side)) or {}
            if not r.get("delivered") and not r.get("read"):
                out.append(m)
        return out

    def waiting(self, at=None):
        """Requests still in line (acked or submitted, not stale), FIFO by submission."""
        at = parse_iso(at or now())
        q = []
        for r in self.requests.values():
            vu = _ts(r.get("valid_until"))                    # one unreadable record never stops the rest
            if r.get("status") in ("submitted", "acked", "partial") and vu is not None and vu > at:
                q.append(r)
        return sorted(q, key=self.age_key)


def _id_digest(kind, ident):
    """A short digest of a caller-chosen id, kept for ever so the id is never reused."""
    return hashlib.sha256(("%s:%s" % (kind, ident)).encode("utf-8")).hexdigest()[:20]


def _generated_seq(kind, ident):
    """The seq a generated id carries, or None when `ident` is not in the generated form."""
    m = _GEN_ID[kind].match(str(ident or ""))
    return int(m.group(1)) if m else None


def _fresh_problem(kind, ident, ev, st):
    """'' if `ident` may name the new acquisition / grant / request `ev`, else why not. A
    generated id must carry `ev`'s own seq (so it is new by construction and needs no memory); an
    id in any other form (a caller-chosen lease or request id, or an id in an older format,
    e.g. al-<minute>-<hex6>) must never have been used
    (its digest is kept for ever, through retention, on the snapshot path and in a full replay)."""
    s = _generated_seq(kind, ident)
    if s is not None:
        return "" if s == ev.get("seq") else "a generated id names seq %d, not its own event's seq %r" % (s, ev.get("seq"))
    if _id_digest(kind, ident) in st.used_ids.get(kind, set()):
        return "it named an earlier %s that has since retired (ids are single-use)" % kind
    return ""


def _new_id(kind, ev):
    """The generated id for the event being appended (its seq and event id are already set)."""
    s, h = int(ev["seq"]), str(ev["event_id"])
    if kind == "lease":
        return "cl-s%d-%s" % (s, h[:6])
    if kind == "alloc":
        return "al-%s-s%d-%s" % (parse_iso(ev["at"]).strftime("%Y%m%d%H%M"), s, h[:4])
    return "rq-%s-s%d-%s" % (parse_iso(ev["at"]).strftime("%Y%m%d"), s, h[:6])


def _swap_placeholder(x, new):
    if isinstance(x, str):
        return x.replace(NEW_ID, new)
    if isinstance(x, list):
        return [_swap_placeholder(v, new) for v in x]
    if isinstance(x, dict):
        return {k: _swap_placeholder(v, new) for k, v in x.items()}
    return x


def _id_finisher(kind):
    """An append() `finish` hook: replace NEW_ID everywhere in the event with the generated id."""
    def fin(_st, ev):
        new = _new_id(kind, ev)
        for k in ("request_id", "allocation_id", "body"):
            ev[k] = _swap_placeholder(ev.get(k), new)
    return fin


def _retain(st, at):
    """Retire FINISHED records from the state, as part of the fold. Called before every valid
    event (fold() and append()) with that event's own time; it acts at most once per RETAIN_STEP_S of
    event time (st.retain_mark, part of the state and of every snapshot), so the snapshot path and a
    full replay retire exactly the same records at exactly the same events. Pure: it reads only the
    state and `at`, never the clock or the process table. The rules: an
    allocation only once verified free and older than RETAIN_S (a failed handback keeps holding its
    GPUs), a request only once finished with every allocation of it retired, a host lease leaves
    host_leases once released or past its `until` (its id stays in released_lease_ids for RETAIN_S),
    dedupe notes of retired ids, read messages beyond the newest SNAPSHOT_MSGS and unread ones older
    than RETAIN_S, and reservations of requests no longer waiting (except the newest per GPU).
    used_ids (caller-chosen ids) are never retired. Returns True when it acted."""
    cutoff = parse_iso(at) - _dt.timedelta(seconds=RETAIN_S)
    if st.retain_mark and cutoff < parse_iso(st.retain_mark) + _dt.timedelta(seconds=RETAIN_STEP_S):
        return False
    st.retain_mark = iso(cutoff)

    def old(*stamps):
        ts = [parse_iso(x) for x in stamps if x]
        return bool(ts) and max(ts) < cutoff

    drop_allocs = {k for k, a in st.allocs.items()
                   if a.get("verified_free") and a.get("status") != "active"
                   and old(a.get("verified_at"), a.get("ended_at"), a.get("released_at"), a.get("start"))}
    waiting_st = ("submitted", "acked", "partial")
    reserved = {r["request_id"] for r in st.reservations}
    drop_reqs = set()
    for k, r in st.requests.items():
        if r["status"] in waiting_st or k in reserved:
            continue
        aids = set(r.get("allocation_ids") or []) | ({r["allocation_id"]} if r.get("allocation_id") else set())
        if {a for a in aids if a in st.allocs and a not in drop_allocs}:
            continue                                     # an allocation of it is still in the state
        if old(r.get("valid_until"), r.get("submitted_at"), r.get("acked_at"), r.get("cancelled_at"), r.get("rejected_at")):
            drop_reqs.add(k)
    released = dict(st.released_lease_ids)
    live_leases = {}
    for k, v in st.host_leases.items():
        if v.get("released_at"):
            released[k] = v["released_at"]
        elif v.get("until") and old(v["until"]):
            released[k] = v["until"]                     # long expired, never released: remembered as over
        else:
            live_leases[k] = v
    released = {k: v for k, v in released.items() if not (v and old(v))}
    dropped_ids = drop_allocs | drop_reqs

    def note_kept(key):
        parts = str(key).split(":")
        return not (len(parts) >= 2 and parts[1] in dropped_ids)
    unread = [m for m in st.messages if not (st.receipts.get((m["event_id"], m.get("to"))) or {}).get("read")
              and not old(m.get("at"))]
    keep_msgs = {m["event_id"] for m in (unread + st.messages[-SNAPSHOT_MSGS:])}
    waiting = {r["request_id"] for r in st.requests.values() if r["status"] in waiting_st}
    last_per_gpu = {}
    for r in st.reservations:
        last_per_gpu[r["gpu"]] = r
    st.reservations = [r for r in st.reservations if r["request_id"] in waiting or last_per_gpu.get(r["gpu"]) is r]
    for name, n in (("allocations", len(drop_allocs)), ("requests", len(drop_reqs))):
        st.pruned[name] = int(st.pruned.get(name, 0)) + n
    st.requests = {k: v for k, v in st.requests.items() if k not in drop_reqs}
    st.allocs = {k: v for k, v in st.allocs.items() if k not in drop_allocs}
    st.messages = [m for m in st.messages if m["event_id"] in keep_msgs]
    st.receipts = {k: v for k, v in st.receipts.items() if k[0] in keep_msgs}
    st.notes = {n for n in st.notes if note_kept(n)}
    st.host_leases = live_leases
    st.released_lease_ids = released
    return True


def _state_to_snapshot(st, at=None):
    """The state as a snapshot body: exactly the fold state. Retention already happened inside
    the fold (_retain), so nothing is left out here and a reader starting from this snapshot folds
    the following events exactly as a full replay does. `at` is accepted for compatibility and not
    used. invalid / ignored keep their newest 50 entries (reports only; the rule book never reads
    them)."""
    return {"requests": st.requests, "allocs": st.allocs,
            "owner_starts": st.owner_starts, "gen": st.gen,
            "current": st.current, "messages": st.messages,
            "receipts": [[k[0], k[1], v] for k, v in st.receipts.items()],
            "notes": sorted(st.notes), "executor": st.executor, "host_leases": st.host_leases,
            "released_leases": st.released_lease_ids, "reservations": st.reservations, "last_grant_at": st.last_grant_at,
            "invalid": st.invalid[-50:], "ignored": st.ignored[-50:], "pruned": dict(st.pruned or {}),
            "retain_s": RETAIN_S, "retain_step_s": RETAIN_STEP_S, "retain_mark": st.retain_mark,
            "used_ids": {k: sorted(v) for k, v in st.used_ids.items()}}


def _state_from_snapshot(snap):
    st = State()
    st.requests = snap.get("requests") or {}
    st.allocs = snap.get("allocs") or {}
    st.owner_starts = snap.get("owner_starts") or {}
    st.gen = int(snap.get("gen") or 0)
    st.current = snap.get("current")
    st.messages = list(snap.get("messages") or [])
    st.receipts = {(a, b): v for a, b, v in snap.get("receipts") or []}
    st.notes = set(snap.get("notes") or [])
    st.executor = snap.get("executor")
    st.host_leases = snap.get("host_leases") or {}
    st.released_lease_ids = dict(snap.get("released_leases") or {})
    st.pruned = dict(snap.get("pruned") or {})
    st.reservations = list(snap.get("reservations") or [])
    st.last_grant_at = snap.get("last_grant_at") or {}
    st.invalid = [tuple(x) for x in snap.get("invalid") or []]
    st.ignored = [tuple(x) for x in snap.get("ignored") or []]
    st.retain_mark = snap.get("retain_mark")
    used = snap.get("used_ids") or {}
    st.used_ids = {k: set(used.get(k) or []) for k in ("lease", "request", "alloc")}
    st.snapshot_seq = int(snap.get("seq") or 0)
    return st


State.to_snapshot = _state_to_snapshot
State.from_snapshot = staticmethod(_state_from_snapshot)


def lease_live(l, at, check_process=True):
    """A host lease is live while it is not released, its `until` (if any) is later than `at`,
    and its holder process (if named) is still the same running process. Liveness only ever goes
    from live to not live, so a rule decided on it stays decided when the log is folded again."""
    if l.get("released_at"):
        return False
    u = _ts(l.get("until"))
    if u is not None and u <= parse_iso(at):
        return False                                          # (an unreadable `until` bounds nothing: still live)
    if l.get("holder_pid") and check_process:
        return same_process(int(l["holder_pid"]), l.get("holder_created"))
    return True


def problem_for(st, ev, base=None):
    """Why `ev` is not a legal transition from `st` ('' when it is). The one rule book:
    used before an append AND by the fold, so a stale event is ignored even if written."""
    t, by, at = ev["type"], ev["by"], parse_iso(ev["at"])
    rid, aid, b = ev.get("request_id"), ev.get("allocation_id"), ev.get("body") or {}
    req = st.requests.get(rid) if rid else None
    al = st.allocs.get(aid) if aid else None
    if t == "request":
        if req:
            return "request id %s already exists" % rid
        if not rid or len(str(rid)) > 80:
            return "a request needs a request id of 1-80 characters"
        fp = _fresh_problem("request", rid, ev, st)
        if fp:
            return "request id %s already exists: %s" % (rid, fp)
        m = b.get("minutes")
        if m is not None and (not isinstance(m, int) or not 1 <= m <= MAX_MINUTES):
            return "minutes must be a whole number from 1 to %d" % MAX_MINUTES
        gpus = b.get("gpus")
        try:
            allowed = set(config(base).get("gpus") or [])
        except MailboxError:
            allowed = set()
        if not isinstance(gpus, list) or not gpus or not (gpus == ["all"] or set(gpus) <= allowed):
            return "gpus must be [\"all\"] or a subset of %s" % sorted(allowed)
        if b.get("partial") is not None and not isinstance(b.get("partial"), bool):
            return "partial must be true or false"
        if not isinstance(b.get("why"), str) or not b["why"].strip() or len(b["why"]) > 500:
            return "why must be 1-500 characters"
        if parse_iso(b.get("valid_until")) <= at:
            return "valid_until is not in the future"
        return ""
    if t == "cancel":
        if not req:
            return "no request %s" % rid
        if req["by"] != by:
            return "only the requester can cancel %s" % rid
        if req["status"] not in ("submitted", "acked", "partial"):
            return "request %s is %s; only a waiting request can be cancelled (release a grant instead)" \
                % (rid, req["status"])
        return ""
    if t == "ack":
        if not req:
            return "no request %s" % rid
        return "" if req["status"] == "submitted" else "request %s is %s, not waiting for an ack" % (rid, req["status"])
    if t == "reject":
        if not req:
            return "no request %s" % rid
        return "" if req["status"] in ("submitted", "acked", "partial") else "request %s is %s" % (rid, req["status"])
    if t == "grant":
        if not req:
            return "no request %s" % rid
        if req["status"] not in ("acked", "partial"):
            return "request %s is %s; only an acknowledged, waiting request can be granted" % (rid, req["status"])
        if parse_iso(req["valid_until"]) <= at:
            return "request %s went stale at %s" % (rid, req["valid_until"])
        if not st.admission_open():
            return "admission is closed: %s" % st.admission_closed_why()
        if b.get("gen") != st.gen + 1:
            return "stale grant: generation %r, expected %d" % (b.get("gen"), st.gen + 1)
        if not aid or aid in st.allocs:
            return "allocation id %r is missing or used" % aid
        fp = _fresh_problem("alloc", aid, ev, st)
        if fp:
            return "allocation id %r is missing or used: %s" % (aid, fp)
        try:
            cfg_gpus = [str(x) for x in (config(base).get("gpus") or [])]
        except MailboxError:
            cfg_gpus = []
        granted = b.get("gpus")
        wanted = st.outstanding(req, cfg_gpus)
        if not isinstance(granted, list) or not granted or not set(map(str, granted)) <= set(wanted):
            return "a grant must name GPUs out of the request's outstanding %s, not %r" % (wanted, granted)
        if not req.get("partial") and sorted(map(str, granted)) != sorted(wanted):
            return "request %s did not allow a partial grant: it needs %s" % (rid, wanted)
        for g in granted:
            rv = st.active_reservation(g, at)
            if rv and rv["request_id"] != rid and st.older(rv["request_id"], rid):
                return "GPU %s is reserved for the older request %s until %s" % (g, rv["request_id"], rv["until"])
            hold = st.agent_hold(g)
            if hold:
                return "GPU %s is held by allocation %s (not yet verified free); it cannot be granted again" % (
                    g, hold["allocation_id"])
            ls = st.live_host_leases(at, g)
            if ls:
                return "GPU %s is in host use (%s); it cannot be granted" % (
                    g, ", ".join("%s %s" % (l["lease_id"], l["purpose"]) for l in ls[:3]))
        exp, ns = b.get("expires"), b.get("next_start")
        if exp:
            if parse_iso(exp) <= at:
                return "the grant would already be expired"
            if ns and parse_iso(exp) > parse_iso(ns):
                return "the grant would outlive the next start"
        elif ns:
            return "a grant before a known next start must end before it"
        return ""
    if t == "reserve":
        if not req:
            return "no request %s" % rid
        if req["status"] not in ("acked", "partial") or req.get("partial"):
            return "only a waiting EXACT request reserves GPUs (%s is %s%s)" % (
                rid, req["status"], ", partial" if req.get("partial") else "")
        if parse_iso(req["valid_until"]) <= at:
            return "request %s went stale at %s" % (rid, req["valid_until"])
        if st.owner_pending():
            return "an owner start order is pending: no reservation (owner start preempts everything)"
        g = str(b.get("gpu"))
        try:
            cfg = config(base)
        except MailboxError:
            cfg = {}
        cfg_gpus = [str(x) for x in (cfg.get("gpus") or [])]
        if g not in st.outstanding(req, cfg_gpus):
            return "GPU %s is not one request %s still needs" % (g, rid)
        lim = int(cfg.get("reserve_s", RESERVE_S))
        if not b.get("until") or parse_iso(b["until"]) <= at or (parse_iso(b["until"]) - at).total_seconds() > lim + 1:
            return "a reservation must end after its own time and within reserve_s (%d s)" % lim
        if st.agent_hold(g):
            return "GPU %s is held by allocation %s" % (g, st.agent_hold(g)["allocation_id"])
        rv = st.active_reservation(g, at)
        if rv and rv["request_id"] == rid:
            return "GPU %s is already reserved for %s" % (g, rid)
        if rv and st.older(rv["request_id"], rid):
            return "GPU %s is reserved for the older request %s" % (g, rv["request_id"])
        if not st.may_reserve_again(rid, g, at):
            return "request %s's reservation on GPU %s lapsed; it is first again the next time GPU %s frees" % (rid, g, g)
        return ""
    if t == "host_acquire":
        lid = b.get("lease_id")
        if not lid or lid in st.host_leases or lid in st.released_lease_ids:
            return "host lease id %r is missing or used" % lid
        fp = _fresh_problem("lease", lid, ev, st)
        if fp:
            return "host lease id %r is missing or used: %s" % (lid, fp)
        try:
            cfg_gpus = [str(x) for x in (config(base).get("gpus") or [])]
        except MailboxError:
            cfg_gpus = []
        g = b.get("gpus")
        if not isinstance(g, list) or not g or not set(map(str, g)) <= set(cfg_gpus):
            return "a host lease must name GPUs out of %s, not %r" % (cfg_gpus, g)
        if b.get("kind") not in HOST_KINDS:
            return "host lease kind must be one of %s" % (HOST_KINDS,)
        if not b.get("holder_pid") and not b.get("until"):
            return "a host lease needs a holder process (holder_pid) or an end (until)"
        if b.get("until") and parse_iso(b["until"]) <= at:
            return "the host lease would already be over"
        for gg in g:
            a = st.agent_hold(gg)
            if a:
                return "GPU %s is granted to the agent (allocation %s, %s)%s" % (
                    gg, a["allocation_id"], a["status"],
                    "; an owner order is reclaiming it" if st.owner_pending() else "")
        return ""
    if t == "host_release":
        l = st.host_leases.get(b.get("lease_id"))
        if not l and b.get("lease_id") in st.released_lease_ids:
            return "host lease %s was already released" % b.get("lease_id")
        if not l:
            return "no host lease %s" % b.get("lease_id")
        if l["released_at"]:
            return "host lease %s was already released" % b.get("lease_id")
        return ""
    if t in ("no_window", "status_note"):
        k = b.get("key")
        if not k:
            return "a %s needs a dedupe key" % t
        return "duplicate %s %s" % (t, k) if k in st.notes else ""
    if t == "owner_start":
        k = b.get("key")
        if not k:
            return "owner_start needs a key"
        if k in st.owner_starts:
            return "owner start %s already recorded (deadline is never reset)" % k
        if b.get("deadline") != iso(at + _dt.timedelta(seconds=OWNER_GRACE_S)):
            return "owner_start deadline must be exactly 300 s after its own acceptance time"
        tg = [a["allocation_id"] for a in st.owner_targets()]
        want = tg[0] if tg else None
        if ev.get("allocation_id") != want or b.get("allocation_id") != want or list(b.get("allocation_ids") or []) != tg:
            return ("owner_start must name every allocation holding a GPU now (%s), not %r / %r" % (
                tg, ev.get("allocation_id"), b.get("allocation_ids")))
        if want and ev.get("to") != "agent":
            return "owner_start must be addressed to the agent while it holds %s" % ", ".join(tg)
        return ""
    if t in ("executor_start", "executor_stop"):
        if not isinstance(b.get("pid"), int) or b["pid"] <= 0:
            return "%s needs a positive pid" % t
        if t != "executor_start":
            ex = st.executor
            if not ex or ex["pid"] != b["pid"] or ex.get("created") != b.get("created") or ex.get("stopped_at"):
                return "%s for pid %s does not match the running executor record" % (t, b["pid"])
            if st.owner_pending_retryable():
                return ("an owner start is pending (%s): the retry executor may not stop"
                        % ", ".join(o["key"] for o in st.owner_pending_retryable()))
        return ""
    if t == "owner_start_dispatch":
        o = st.owner_starts.get(b.get("key"))
        if not o:
            return "no owner start %s" % b.get("key")
        if o["status"] != "pending":
            return "owner start %s is already %s" % (b.get("key"), o["status"])
        if not st.host_gpu_clear():
            return ("GPU clearance is not verified: allocation %s still holds the GPUs; the owner start "
                    "stays pending" % st.holding()[0]["allocation_id"])
        c = st.live_claim(b.get("key"), at)
        if c:
            return "owner start %s is already being dispatched (claim %s at %s)" % (b.get("key"), c["claim_id"], c["at"])
        if not b.get("claim_id"):
            return "a dispatch claim needs a claim_id"
        return ""
    if t == "owner_start_done":
        o = st.owner_starts.get(b.get("key"))
        if not o:
            return "no owner start %s" % b.get("key")
        if o["status"] != "pending":
            return "owner start %s is already %s" % (b.get("key"), o["status"])
        if not o.get("claim") or o["claim"]["claim_id"] != b.get("claim_id"):
            return "owner start %s has no dispatch claim %r: it cannot be closed without one" % (
                b.get("key"), b.get("claim_id"))
        if b.get("result") not in OWNER_RESULTS:
            return "owner_start_done result must be one of %s" % sorted(OWNER_RESULTS)
        return ""
    if t == "owner_start_attempt":                           # a failed dispatch; the order stays pending
        o = st.owner_starts.get(b.get("key"))
        if not o:
            return "no owner start %s" % b.get("key")
        if o["status"] != "pending":
            return "owner start %s is already %s" % (b.get("key"), o["status"])
        if not o.get("claim") or o["claim"]["claim_id"] != b.get("claim_id"):
            return ("owner start %s: claim %r is not its current dispatch claim; only the claim that dispatched "
                    "may record the attempt" % (b.get("key"), b.get("claim_id")))
        if not isinstance(b.get("error"), str) or not b["error"].strip():
            return "an owner_start_attempt needs the error text"
        if b.get("kind") not in OWNER_ATTEMPT_KINDS:
            return "owner_start_attempt kind must be one of %s" % (OWNER_ATTEMPT_KINDS,)
        return ""
    if t == "owner_start_cancel":                            # the owner's explicit cancel
        o = st.owner_starts.get(b.get("key"))
        if not o:
            return "no owner start %s" % b.get("key")
        if o["status"] != "pending":
            return "owner start %s is already %s" % (b.get("key"), o["status"])
        if b.get("by") != "owner":
            return "only the owner's own cancel closes an owner start (by must be \"owner\")"
        if not isinstance(b.get("words"), str) or not b["words"].strip():
            return "an owner_start_cancel needs the owner's cancel words"
        c = st.live_claim(b.get("key"), at)
        if c:
            return ("owner start %s is being dispatched right now (claim %s at %s); cancel after that dispatch "
                    "starts or records its attempt, or after its lease ends" % (b.get("key"), c["claim_id"], c["at"]))
        return ""
    if t == "receipt":
        m = st.message(b.get("event_id"))
        if not m:
            return "no message %s" % b.get("event_id")
        if m.get("to") != by:
            return "%s cannot sign a receipt for a message addressed to %s" % (by, m.get("to"))
        if b.get("kind") not in ("delivered", "read"):
            return "receipt kind must be delivered or read"
        if (st.receipts.get((m["event_id"], by)) or {}).get(b["kind"]):
            return "duplicate receipt"
        return ""
    # --- allocation events
    if not al:
        return "no allocation %s" % aid
    owner = (st.requests.get(al["request_id"]) or {}).get("by")
    if t == "warning":
        if al["warned"]:
            return "allocation %s was already warned" % aid
        return "" if al["status"] == "active" else "allocation %s is %s" % (aid, al["status"])
    if t == "schedule_change":
        if al["status"] != "active":
            return "allocation %s is %s" % (aid, al["status"])
        if not b.get("expires"):
            return "a schedule change must give the new end"
        if al["expires"] and parse_iso(b.get("expires")) >= parse_iso(al["expires"]):
            return "a schedule change may only shorten a grant, never extend it"
        return ""
    if t == "expire":
        if al["status"] != "active":
            return "allocation %s is %s" % (aid, al["status"])
        if not al["expires"]:
            return "allocation %s has no set end" % aid
        return "" if at >= parse_iso(al["expires"]) else "allocation %s has not reached its end" % aid
    if t in ("revoke", "preempt"):
        return "" if al["status"] == "active" else "allocation %s is %s" % (aid, al["status"])
    if t == "release":
        if owner != by:
            return "only the allocation's holder can release %s" % aid
        if al["released_at"]:
            return "allocation %s was already released" % aid
        if al["verified_free"]:
            return "allocation %s is already verified free" % aid
        return ""
    if t == "admit":
        if owner != by:
            return "only the allocation's holder can start work on %s" % aid
        if al["status"] != "active":
            return "allocation %s is %s, not active" % (aid, al["status"])
        if st.owner_pending():
            o = st.owner_pending()[0]
            return ("Orders from the GPU owner to start a job are pending (deadline %s): no new GPU work may start"
                    % fmt_time(o["deadline"]))
        need = b.get("need_s")
        if not isinstance(need, int) or need < 0:
            return "need_s must be a whole number of seconds >= 0"
        eff = st.effective_expires(aid)
        if eff is not None:
            left = (eff - at).total_seconds()
            if left <= 0 or left < need:
                return "only %s left on %s, %s needed" % (fmt_dur(max(0, left)), aid, fmt_dur(need))
        return ""
    if t == "register_pid":
        if owner != by:
            return "only the allocation's holder can register a process on %s" % aid
        if al["status"] != "active":
            return "allocation %s is %s, not active" % (aid, al["status"])
        if not isinstance(b.get("pid"), int) or b["pid"] <= 0:
            return "pid must be a positive whole number"
        return ""
    if t in ("release_verified", "release_unverified"):
        if al["verified_free"]:
            return "allocation %s is already verified free" % aid
        if al["status"] == "active":
            return "allocation %s is still active (not released, revoked or expired)" % aid
        if t == "release_unverified" and b.get("key") and b["key"] in st.notes:
            return "duplicate release_unverified %s" % b["key"]
        return ""
    return "unknown event type %r" % t


def apply(st, ev):
    t, at = ev["type"], ev["at"]
    rid, aid, b = ev.get("request_id"), ev.get("allocation_id"), ev.get("body") or {}
    if t == "request":
        st.requests[rid] = {"request_id": rid, "by": ev["by"], "status": "submitted",
                            "submitted_at": at, "minutes": b.get("minutes"), "gpus": b["gpus"],
                            "partial": bool(b.get("partial")),
                            "why": b["why"], "valid_until": b["valid_until"],
                            "content_hash": b.get("content_hash"), "allocation_id": None,
                            "acked_at": None, "ack_text": None, "event_id": ev["event_id"]}
        if _generated_seq("request", rid) is None:
            st.used_ids["request"].add(_id_digest("request", rid))     # caller-chosen: single-use for ever
    elif t == "cancel":
        st.requests[rid].update(status="cancelled", cancelled_at=at)
    elif t == "ack":
        st.requests[rid].update(status="acked", acked_at=at, ack_text=b.get("text"))
    elif t == "reject":
        st.requests[rid].update(status="rejected", rejected_at=at, reject_reason=b.get("reason"))
        if b.get("key"):
            st.notes.add(b["key"])
    elif t == "reserve":
        st.reservations.append({"gpu": str(b["gpu"]), "request_id": rid, "at": at, "until": b["until"]})
    elif t == "host_acquire":
        st.host_leases[b["lease_id"]] = {"lease_id": b["lease_id"], "gpus": [str(x) for x in b["gpus"]],
                                         "kind": b["kind"], "purpose": b.get("purpose") or "",
                                         "holder_pid": b.get("holder_pid"), "holder_created": b.get("holder_created"),
                                         "until": b.get("until"), "acquired_at": at, "released_at": None,
                                         "acquired_seq": ev.get("seq"), "acquisition_id": ev.get("event_id")}
        if _generated_seq("lease", b["lease_id"]) is None:
            st.used_ids["lease"].add(_id_digest("lease", b["lease_id"]))  # caller-chosen: single-use for ever
    elif t == "host_release":
        st.host_leases[b["lease_id"]]["released_at"] = at
    elif t == "grant":
        st.gen += 1
        st.allocs[aid] = {"allocation_id": aid, "request_id": rid, "gen": b["gen"],
                          "gpus": [str(x) for x in b["gpus"]],
                          "start": at, "expires": b["expires"], "next_start": b["next_start"],
                          "next_start_kind": b.get("next_start_kind"), "status": "active",
                          "verified_free": False, "released_at": None, "warned": False,
                          "pids": {}, "baseline_apps": b.get("baseline_apps") or [],
                          "baseline_gpus": b.get("baseline_gpus") or [], "admits": [],
                          "ended_at": None, "end_reason": None, "verified_at": None}
        if _generated_seq("alloc", aid) is None:
            st.used_ids["alloc"].add(_id_digest("alloc", aid))       # an id in an older format: single-use
        for g in b["gpus"]:
            st.last_grant_at[str(g)] = at
        rq = st.requests[rid]
        rq.setdefault("allocation_ids", []).append(aid)
        rq["granted_gpus"] = sorted(set(rq.get("granted_gpus") or []) | set(str(x) for x in b["gpus"]))
        left = [g for g in (b.get("requested_gpus") or []) if g not in rq["granted_gpus"]]
        rq.update(status="partial" if (left and rq.get("partial")) else "granted", allocation_id=aid)
        st.current = aid
    elif t in ("no_window", "status_note"):
        st.notes.add(b["key"])
    elif t == "warning":
        st.allocs[aid]["warned"] = True
    elif t == "schedule_change":
        st.allocs[aid].update(expires=b["expires"], next_start=b.get("next_start"))
    elif t == "expire":
        st.allocs[aid].update(status="expired", ended_at=at, end_reason="time is up")
    elif t in ("revoke", "preempt"):
        st.allocs[aid].update(status="revoked", ended_at=at, end_reason=b.get("reason") or t)
    elif t == "release":
        al = st.allocs[aid]
        al["released_at"] = at
        if al["status"] == "active":
            al.update(status="released", ended_at=at, end_reason="released by the agent")
    elif t == "register_pid":
        st.allocs[aid]["pids"][str(b["pid"])] = b.get("created")
    elif t == "admit":
        st.allocs[aid].setdefault("admits", []).append({"at": at, "need_s": b.get("need_s"),
                                                        "what": b.get("what")})
    elif t == "release_verified":
        st.allocs[aid].update(verified_free=True, verified_at=at)
    elif t == "release_unverified":
        if b.get("key"):
            st.notes.add(b["key"])
    elif t == "owner_start":
        st.owner_starts[b["key"]] = {"key": b["key"], "accepted_at": at, "deadline": b["deadline"],
                                     "words": b.get("words"), "message_id": b.get("message_id"),
                                     "allocation_id": b.get("allocation_id"), "series": b.get("series"),
                                     "allocation_ids": list(b.get("allocation_ids") or []), "owner": b.get("owner"),
                                     "status": "pending", "claim": None, "event_id": ev["event_id"]}
    elif t == "executor_start":
        st.executor = {"pid": b["pid"], "created": b.get("created"), "started_at": at,
                       "stopped_at": None, "stop_reason": None, "cmd": b.get("cmd")}
    elif t == "executor_stop":
        st.executor.update(stopped_at=at, stop_reason=b.get("reason"))
    elif t == "owner_start_dispatch":
        st.owner_starts[b["key"]]["claim"] = {"claim_id": b["claim_id"], "at": at,
                                              "lease_s": int(b.get("lease_s") or DISPATCH_LEASE_S),
                                              "by_pid": b.get("by_pid")}
    elif t == "owner_start_done":
        st.owner_starts[b["key"]].update(status=OWNER_RESULTS[b["result"]], done_at=at,
                                         outcome=b.get("outcome"), result=b["result"])
    elif t == "owner_start_attempt":
        o = st.owner_starts[b["key"]]
        att = {"at": at, "claim_id": b["claim_id"], "kind": b["kind"], "error": str(b["error"])[:600]}
        o["attempts"] = (list(o.get("attempts") or []) + [att])[-OWNER_ATTEMPTS_KEEP:]
        o.update(attempt_count=int(o.get("attempt_count") or 0) + 1, last_attempt_at=at,
                 last_error=att["error"], last_attempt_kind=b["kind"], claim=None)
    elif t == "owner_start_cancel":
        st.owner_starts[b["key"]].update(status="cancelled", done_at=at, result="cancelled",
                                         outcome="cancelled by the owner: %s" % str(b.get("words"))[:300],
                                         cancel_message_id=b.get("message_id"))
    elif t == "receipt":
        st.receipts.setdefault((b["event_id"], ev["by"]), {})[b["kind"]] = at
    if ev.get("to"):
        st.messages.append(ev)
    st.events.append(ev)


def fold(recs=None, base=None):
    recs = read_events(base) if recs is None else recs
    snap = getattr(recs, "snapshot", None)
    st = State.from_snapshot(snap) if snap else State()
    for r in recs:
        if r.problem:
            st.invalid.append((r.seq, r.problem))
            continue
        try:
            _retain(st, r.ev.get("at"))                      # retention is part of the fold
            why = problem_for(st, r.ev, base)
        except Exception as e:                               # noqa: BLE001  one bad event never stops the fold
            why = "rule check failed (%s: %s)" % (type(e).__name__, str(e)[:160])
        if why:
            r.ignored = why
            st.ignored.append((r.seq, why))
            continue
        try:
            apply(st, r.ev)
        except Exception as e:                               # noqa: BLE001
            r.ignored = "apply failed (%s: %s)" % (type(e).__name__, str(e)[:160])
            st.ignored.append((r.seq, r.ignored))
            continue
        r.applied = True
    return st


def load(base=None):
    return fold(base=base)


def append(by, typ, *, request_id=None, allocation_id=None, to=None, body=None, at=None,
           check=None, base=None, build=None, finish=None):
    """Append one signed event under the lock. `check(state)` may raise Refused. `build(state,
    at_iso)` (optional) returns a dict that may set "to", "allocation_id", "request_id" and
    extra "body" keys from the state read UNDER the lock, so an event that depends on the
    current state (owner_start) is built from exactly the state the rule book judges. `finish(state,
    ev)` (optional) may change the event once its seq and event id are set (the generated ids).
    The event is refused (never written) if problem_for() rejects it against the current state --
    the state with retention applied at the event's own time, exactly as fold() will judge it."""
    if by not in SIDES or typ not in ALLOWED[by]:
        raise Refused("%s may not write %r events" % (by, typ))
    _test_clock()                                           # refuses a test clock on the default mailbox
    with _Lock(base):
        recs = read_events(base)
        st = fold(recs, base)
        at_iso = iso(at or now())
        _retain(st, at_iso)                                  # the same retention step fold() applies to this event
        if check:
            check(st)
        snap = recs.snapshot
        prev_hash = hashlib.sha256(recs[-1].raw).hexdigest() if recs else (snap["anchor"] if snap else "")
        ev = {"protocol": PROTOCOL, "seq": (recs[-1].seq + 1) if recs else ((int(snap["seq"]) + 1) if snap else 1),
              "event_id": uuid.uuid4().hex, "type": typ, "by": by,
              "at": at_iso, "to": to, "request_id": request_id,
              "allocation_id": allocation_id, "body": body or {},
              "prev": prev_hash,
              "code": code_id()}
        if build:
            extra = build(st, ev["at"]) or {}
            for k in ("to", "allocation_id", "request_id"):
                if k in extra:
                    ev[k] = extra[k]
            ev["body"] = dict(ev["body"], **(extra.get("body") or {}))
        if finish:
            finish(st, ev)
        why = problem_for(st, ev, base)
        if why:
            raise Refused(why)
        ev["sig"] = _sign(ev, base)
        data = json.dumps(ev, sort_keys=True, indent=1, ensure_ascii=True).encode("ascii")
        _write_new(os.path.join(_p("events", base=base), "%08d.json" % ev["seq"]), data)
        if by == "host" and len(recs) + 1 > _compact_limit(base):
            # rolling snapshot: a host-side write keeps the live tail bounded, still under this
            # lock, so every reader loads one snapshot + at most compact_at event files. The
            # event above is already written; a failed compaction never undoes or fails it.
            try:
                _compact_locked(base, _compact_keep(base))
            except Exception:                                # noqa: BLE001
                pass
        return ev


def compact(base=None, keep_tail=COMPACT_KEEP):
    """Bounded fold: under the lock, fold the events up to all but the newest `keep_tail`, write
    that state as a host-signed snapshot (snapshots/snap-<seq>.json, anchored to the hash of the
    last event it covers), then MOVE the covered event files to archive/ (never deleted; `verify
    --full` replays them). Returns {"seq", "archived", "kept"} or None when there is nothing to do."""
    with _Lock(base):
        return _compact_locked(base, keep_tail)


def _compact_limit(base=None):
    try:
        return int(config(base).get("compact_at", COMPACT_AT))
    except (MailboxError, ValueError, TypeError):
        return COMPACT_AT


def _compact_keep(base=None):
    try:
        return int(config(base).get("compact_keep", COMPACT_KEEP))
    except (MailboxError, ValueError, TypeError):
        return COMPACT_KEEP


def history(base=None):
    """Every applied event ever written, in order (archive/ + events/, full replay). State.events
    from load() holds only the events after the newest snapshot."""
    return fold(read_events(base, full=True), base).events


def _archive_snapshots(base=None, keep=SNAPSHOT_KEEP):
    """MOVE all but the newest `keep` snapshots to archive/snapshots/ (never deleted)."""
    names = _snapshot_names(base)[keep:]
    if not names:
        return 0
    src_d, dst_d = _p("snapshots", base=base), _p("archive", "snapshots", base=base)
    os.makedirs(dst_d, exist_ok=True)
    moved = 0
    for n in names:
        try:
            os.rename(os.path.join(src_d, n), os.path.join(dst_d, n))
            moved += 1
        except OSError:                                      # held open by a reader: next time
            pass
    return moved


def _compact_locked(base=None, keep_tail=COMPACT_KEEP):
    """compact() with the mailbox lock already held by the caller."""
    prev_snap = latest_snapshot(base)
    if prev_snap:
        _archive_upto(int(prev_snap["seq"]), base)        # files a reader held open last time
    recs = read_events(base)
    if len(recs) <= keep_tail:
        return None
    cut = len(recs) - keep_tail
    head = _Recs(recs[:cut])
    head.snapshot = recs.snapshot
    st = fold(head, base)
    last = head[-1]
    snap = st.to_snapshot()                                  # exactly the fold state (retention is in the fold)
    snap.update(protocol=PROTOCOL, seq=last.seq, anchor=hashlib.sha256(last.raw).hexdigest(),
                created_at=iso(now()), code=code_id())
    snap["sig"] = hmac.new(_key("host", base), _snap_canonical(snap), hashlib.sha256).hexdigest()
    sd = _p("snapshots", base=base)
    os.makedirs(sd, exist_ok=True)
    _write_new(os.path.join(sd, "snap-%08d.json" % last.seq),
               json.dumps(snap, ensure_ascii=True).encode("ascii"))     # insertion order kept (sig is over the sorted canonical form)
    n, deferred = _archive_upto(last.seq, base)
    _archive_snapshots(base)
    return {"seq": last.seq, "archived": n, "kept": len(recs) - cut, "deferred": deferred}


def _archive_upto(seq, base=None):
    """Move every event file with seq <= `seq` (all covered by a snapshot) from events/ to archive/.
    Never deletes. On Windows a file a reader has open cannot be renamed (WinError 32): it is
    retried briefly and otherwise left in events/ -- readers skip files the snapshot covers -- and
    moved by the next compaction. Returns (moved, deferred)."""
    ad = _p("archive", base=base)
    os.makedirs(ad, exist_ok=True)
    ed = _p("events", base=base)
    moved = deferred = 0
    for nme in sorted(x for x in os.listdir(ed) if x.endswith(".json") and x[:-5].isdigit() and int(x[:-5]) <= seq):
        src, dst = os.path.join(ed, nme), os.path.join(ad, nme)
        for attempt in range(10):
            try:
                os.rename(src, dst)                           # moved, never deleted
                moved += 1
                break
            except PermissionError:
                time.sleep(0.02)
            except FileNotFoundError:
                break
        else:
            deferred += 1
    return moved, deferred


def maybe_compact(base=None):
    """Compact when the live event files exceed config compact_at (default COMPACT_AT)."""
    try:
        cfg = config(base)
    except MailboxError:
        return None
    lim = int(cfg.get("compact_at", COMPACT_AT))
    d = _p("events", base=base)
    try:
        cnt = sum(1 for n in os.listdir(d) if n.endswith(".json"))
    except OSError:
        return None
    if cnt <= lim:
        return None
    return compact(base, keep_tail=int(cfg.get("compact_keep", COMPACT_KEEP)))


# ------------------------------------------------------------------ GPU telemetry and processes
def _int_or_none(text):
    """'301' -> 301; '[N/A]', '', 'N/A', '[Not Supported]', garbage -> None (UNKNOWN, never 0)."""
    t = str(text if text is not None else "").strip()
    if t.lower().endswith("mib"):
        t = t[:-3].strip()
    if t.endswith("%"):
        t = t[:-1].strip()
    try:
        v = float(t)
    except ValueError:
        return None
    if v != v or v < 0:                                      # NaN or negative = unknown
        return None
    return int(v)


def parse_compute_apps(text, uuid_to_index=None):
    """nvidia-smi --query-compute-apps=pid,gpu_uuid,process_name,used_memory --format=csv,noheader,nounits
    (the older shape pid,process_name,used_memory is still read, without GPU identity).
    Returns (apps, problems); each app is {pid, name, used_mb, gpu_uuid, gpu}. used_mb is None
    when nvidia-smi does not know it ('[N/A]' on WDDM for every process) -- never read as 0 MB.
    gpu is the nvidia-smi index the process runs on (via uuid_to_index), None when unknown. A line
    whose pid cannot be read, or whose GPU uuid maps to no GPU, is a problem."""
    apps, problems = [], []
    u2i = uuid_to_index or {}
    for line in (text or "").splitlines():
        if not line.strip():
            continue
        parts = [x.strip() for x in line.split(",")]
        if len(parts) < 3 or not parts[0].isdigit():
            problems.append("unreadable compute-apps line %r" % line[:120])
            continue
        uuid_ = None
        if len(parts) >= 4 and parts[1].upper().startswith("GPU-"):
            uuid_ = parts[1]
            name = ",".join(parts[2:-1])
        else:
            name = ",".join(parts[1:-1])
        gpu = None
        if uuid_:
            gpu = u2i.get(uuid_)
            if gpu is None and u2i:
                problems.append("compute process %s is on GPU %s, which the per-GPU query does not list" % (parts[0], uuid_))
        apps.append({"pid": int(parts[0]), "name": name, "used_mb": _int_or_none(parts[-1]),
                     "gpu_uuid": uuid_, "gpu": gpu})
    return apps, problems


def parse_gpu_query(text):
    """nvidia-smi --query-gpu=index,uuid,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits
    (the older shape without uuid is still read). Returns (gpus, problems). Any value
    that is not a number ('[N/A]', '[Not Supported]') is a problem: that GPU is UNRESOLVED."""
    gpus, problems = [], []
    for line in (text or "").splitlines():
        if not line.strip():
            continue
        parts = [x.strip() for x in line.split(",")]
        if len(parts) >= 5 and parts[1].upper().startswith("GPU-"):
            uuid_ = parts[1]
            parts = [parts[0]] + parts[2:]
        else:
            uuid_ = None
        if len(parts) < 4 or not parts[0].isdigit():
            problems.append("unreadable GPU line %r" % line[:120])
            continue
        rec = {"index": parts[0], "uuid": uuid_, "memory_used_mb": _int_or_none(parts[1]),
               "memory_total_mb": _int_or_none(parts[2]), "util_pct": _int_or_none(parts[3])}
        for k, raw in (("memory_used_mb", parts[1]), ("util_pct", parts[3])):
            if rec[k] is None:
                problems.append("GPU %s %s unknown (%r)" % (parts[0], k, raw))
        gpus.append(rec)
    if not gpus and not problems:
        problems.append("the per-GPU query returned no GPU")
    return gpus, problems


def _smi(args, timeout):
    return subprocess.run(["nvidia-smi"] + args, capture_output=True, text=True, timeout=timeout,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def gpu_probe(timeout=15):
    """{'available', 'apps': [{'pid','name','used_mb'|None}], 'gpus': [{'index','memory_used_mb',
    'memory_total_mb','util_pct'}], 'source', 'why'}.
    Two read-only nvidia-smi queries: the compute processes (who is on the GPU; per-process
    memory is [N/A] under WDDM, kept as None = unknown) and the per-GPU numbers (the
    reliable occupancy check). 'available' is True only when both ran AND every per-GPU line
    parsed; anything unreadable is reported in 'why' and is never read as free.
    GPU_TIME_PROBE_FILE (tests) replaces nvidia-smi with a JSON file of the same shape; a probe
    without per-GPU numbers is unresolved."""
    f = os.environ.get("GPU_TIME_PROBE_FILE")
    if f:
        try:
            with open(f, encoding="utf-8") as fh:
                d = json.load(fh)
            return {"available": bool(d.get("available")), "apps": list(d.get("apps") or []),
                    "gpus": list(d.get("gpus") or []), "source": "file:%s" % f, "why": d.get("why", "")}
        except Exception as e:                               # noqa: BLE001
            return {"available": False, "apps": [], "gpus": [], "source": "file", "why": "probe file: %s" % e}
    out = {"available": False, "apps": [], "gpus": [], "source": "nvidia-smi", "why": ""}
    try:
        r = _smi(["--query-compute-apps=pid,gpu_uuid,process_name,used_memory", "--format=csv,noheader,nounits"], timeout)
        g = _smi(["--query-gpu=index,uuid,memory.used,memory.total,utilization.gpu", "--format=csv,noheader,nounits"], timeout)
    except Exception as e:                                   # noqa: BLE001
        out["why"] = "%s: %s" % (type(e).__name__, e)
        return out
    for name, res in (("compute-apps", r), ("per-GPU", g)):
        if res.returncode != 0:
            out["why"] = "%s query exit %s: %s" % (name, res.returncode, (res.stderr or res.stdout or "").strip()[:200])
            return out
    gpus, p2 = parse_gpu_query(g.stdout)
    apps, p1 = parse_compute_apps(r.stdout, {x["uuid"]: x["index"] for x in gpus if x.get("uuid")})
    out.update(apps=apps, gpus=gpus)
    problems = p1 + p2
    if problems:
        out["why"] = "; ".join(problems[:6])
        return out
    out["available"] = True
    return out


def _cfg_int(cfg, key, default):
    try:
        return int(cfg.get(key, default))
    except (TypeError, ValueError):
        return default


def wanted_gpus(gpus, cfg):
    """A request's GPU list (["all"] or indexes) as the configured index strings."""
    allg = [str(x) for x in (cfg.get("gpus") or ["0", "1"])]
    return allg if not gpus or list(gpus) == ["all"] else [str(x) for x in gpus]


def app_gpu(a):
    """The nvidia-smi index (string) a compute process runs on, or None when not identified."""
    g = a.get("gpu")
    return None if g is None else str(g)


def app_on(a, gpus):
    """True if process `a` may be on one of `gpus`: its identified GPU is among them, or its GPU
    is not identified (conservative: an unidentified process counts as on every GPU)."""
    g = app_gpu(a)
    return g is None or g in [str(x) for x in gpus]


def occupancy(probe, gpus=None, cfg=None):
    """Is the hardware free for a grant? -> {'state': 'free'|'occupied'|'unresolved', 'why', 'gpus'}.
    The reliable check is the per-GPU query: every wanted GPU must be present with
    a readable memory.used and utilization; it is occupied at memory.used >= resident_block_mb
    or utilization >= busy_util_pct. A compute process whose own memory IS known and is at or
    over resident_block_mb also makes it occupied. A compute process whose memory is unknown
    ([N/A], every process on WDDM) is never counted as 0 MB: it is listed, and the per-GPU
    numbers (which include it) decide. Telemetry unavailable or any wanted GPU unreadable =
    UNRESOLVED, which grants nothing."""
    cfg = cfg if cfg is not None else {}
    block = _cfg_int(cfg, "resident_block_mb", RESIDENT_BLOCK_MB)
    busy = _cfg_int(cfg, "busy_util_pct", BUSY_UTIL_PCT)
    want = wanted_gpus(gpus, cfg)
    pr = probe or {}
    if not pr.get("available"):
        return {"state": "unresolved", "gpus": want,
                "why": "GPU telemetry unavailable (%s)" % (pr.get("why") or "no probe")}
    by_idx = {str(x.get("index")): x for x in (pr.get("gpus") or [])}
    busy_list, unknown = [], []
    for i in want:
        g = by_idx.get(i)
        if g is None:
            unknown.append("GPU %s missing from the per-GPU telemetry" % i)
            continue
        mem, util = g.get("memory_used_mb"), g.get("util_pct")
        if not isinstance(mem, int) or isinstance(mem, bool) or mem < 0:
            unknown.append("GPU %s memory.used unknown (%r)" % (i, mem))
            continue
        if not isinstance(util, int) or isinstance(util, bool) or util < 0:
            unknown.append("GPU %s utilization unknown (%r)" % (i, util))
            continue
        if mem >= block:
            busy_list.append("GPU %s holds %d MB (>= %d MB)" % (i, mem, block))
        if util >= busy:
            busy_list.append("GPU %s is %d%% busy (>= %d%%)" % (i, util, busy))
    if unknown:
        return {"state": "unresolved", "gpus": want, "why": "; ".join(unknown)}
    mine = [a for a in pr.get("apps") or [] if app_on(a, want)]
    for a in mine:
        mb = a.get("used_mb")
        if isinstance(mb, int) and not isinstance(mb, bool) and mb >= block:
            busy_list.append("%s pid %s holds %d MB on GPU %s" % (a.get("name"), a.get("pid"), mb,
                                                                a.get("gpu") if a.get("gpu") is not None else "unknown"))
    unk_apps = [a for a in mine if not (isinstance(a.get("used_mb"), int) and a.get("used_mb") >= 0)]
    note = ""
    if unk_apps:
        note = " (%d compute process(es) with unknown own memory: %s -- judged by the per-GPU memory)" % (
            len(unk_apps), ", ".join("%s pid %s" % (a.get("name"), a.get("pid")) for a in unk_apps[:6]))
    if busy_list:
        return {"state": "occupied", "gpus": want, "why": "; ".join(busy_list) + note}
    return {"state": "free", "gpus": want, "why": "per-GPU memory and utilization under %d MB / %d%%%s" % (block, busy, note)}


def proc_created(pid):
    """Creation time (Windows FILETIME int) of a RUNNING pid, else None. Read-only query."""
    if os.name != "nt":
        try:
            with open("/proc/%d/stat" % pid) as f:
                return int(f.read().split(")")[-1].split()[19])
        except Exception:                                    # noqa: BLE001
            return None
    import ctypes
    from ctypes import wintypes
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.OpenProcess.restype = wintypes.HANDLE
    h = k32.OpenProcess(0x1000, False, int(pid))            # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return None
    try:
        code = wintypes.DWORD()
        if not k32.GetExitCodeProcess(h, ctypes.byref(code)) or code.value != 259:   # STILL_ACTIVE
            return None
        c, e, kk, u = (wintypes.FILETIME() for _ in range(4))
        if not k32.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(e), ctypes.byref(kk), ctypes.byref(u)):
            return None
        return (c.dwHighDateTime << 32) | c.dwLowDateTime
    finally:
        k32.CloseHandle(h)


def same_process(pid, created):
    """True only if `pid` is running AND is the very process registered (same creation time),
    so a reused pid number is never mistaken for the registered job."""
    now_created = proc_created(int(pid))
    return now_created is not None and created is not None and int(now_created) == int(created)


def terminate_exact(pid, created):
    """End ONE registered process tree, only after proving it is the registered process.
    Never by image name. Returns (ended: bool, detail)."""
    if not same_process(pid, created):
        return True, "pid %s is not running as the registered process (already gone or reused)" % pid
    try:
        r = subprocess.run(["taskkill", "/PID", str(int(pid)), "/T", "/F"], capture_output=True, text=True,
                           timeout=30, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        detail = (r.stdout or r.stderr or "").strip()[:200]
    except Exception as e:                                   # noqa: BLE001
        detail = "%s: %s" % (type(e).__name__, e)
    for _ in range(20):
        if not same_process(pid, created):
            return True, "ended pid %s (%s)" % (pid, detail)
        time.sleep(0.25)
    return False, "pid %s still running after taskkill (%s)" % (pid, detail)


def verify_release(st, aid, probe=None, base=None):
    """(verified: bool, why). Free means ALL of: every process registered on the allocation is
    gone; telemetry is available (both nvidia-smi queries readable); no compute process that
    appeared during the allocation (not in the grant-time baseline) is still on the GPU; and
    every granted GPU's memory.used is readable and back under resident_block_mb or within
    release_margin_mb of its grant-time baseline. Unavailable or unreadable telemetry is NOT
    free; an unknown per-process memory value is never read as 0."""
    al = st.allocs.get(aid)
    if not al:
        return False, "no allocation %s" % aid
    alive = [p for p, c in al["pids"].items() if same_process(int(p), c)]
    if alive:
        return False, "registered process(es) still running: %s" % ", ".join(alive)
    probe = probe if probe is not None else gpu_probe()
    if not probe.get("available"):
        return False, "GPU telemetry unavailable (%s) -- not treated as free" % (probe.get("why") or "?")
    base_pids = {int(x.get("pid")) for x in al["baseline_apps"]}
    reg = {int(p) for p in al["pids"]}
    newcomers = [x for x in probe.get("apps") or [] if int(x["pid"]) not in base_pids
                 and (int(x["pid"]) in reg or app_on(x, al["gpus"]))]
    held = [x for x in newcomers if int(x["pid"]) in reg] or newcomers
    if held:
        return False, "GPU still used by process(es) that were not there at grant time: %s" % ", ".join(
            "%s pid %s on GPU %s %s" % (x.get("name"), x.get("pid"),
                                        app_gpu(x) if app_gpu(x) is not None else "unknown",
                                        ("%s MB" % x["used_mb"]) if isinstance(x.get("used_mb"), int) else "memory unknown")
            for x in held[:6])
    try:
        cfg = config(base)
    except MailboxError:
        cfg = {}
    block = _cfg_int(cfg, "resident_block_mb", RESIDENT_BLOCK_MB)
    margin = _cfg_int(cfg, "release_margin_mb", RELEASE_MARGIN_MB)
    by_idx = {str(x.get("index")): x for x in probe.get("gpus") or []}
    base_gpu = {str(x.get("index")): x.get("memory_used_mb") for x in al.get("baseline_gpus") or []}
    over = []
    for i in wanted_gpus(al.get("gpus"), cfg):
        g = by_idx.get(i)
        mem = g.get("memory_used_mb") if g else None
        if not isinstance(mem, int) or isinstance(mem, bool) or mem < 0:
            return False, "GPU %s memory.used unknown (%s) -- release not verified" % (
                i, "missing from telemetry" if g is None else repr(mem))
        b0 = base_gpu.get(i)
        if mem >= block and not (isinstance(b0, int) and mem <= b0 + margin):
            over.append("GPU %s holds %d MB (grant-time %s MB, limit %d MB or baseline + %d MB)" % (
                i, mem, b0 if isinstance(b0, int) else "unknown", block, margin))
    if over:
        return False, "GPU memory not back to its grant-time level: %s" % "; ".join(over)
    return True, ("no registered process left, telemetry available, no GPU process newer than the grant, "
                  "GPU memory back under the limit")


# ------------------------------------------------------------------ agent side
def _content_hash(by, minutes, gpus, why):
    return hashlib.sha256(json.dumps([by, minutes, sorted(gpus), why.strip()], sort_keys=True)
                          .encode("utf-8")).hexdigest()


def new_request_id():
    return "rq-%s-%s" % (now().strftime("%Y%m%d"), uuid.uuid4().hex[:8])


def request(minutes=None, why="", gpus=None, request_id=None, valid_hours=DEFAULT_VALID_H,
            by="agent", base=None, partial=None):
    """Submit (or re-deliver) a request. Same id + same content = the same logical request."""
    gpus = list(gpus or ["all"])
    rid = request_id or NEW_ID              # a generated id carries its event's seq (append's finish hook)
    ch = _content_hash(by, minutes, gpus, why or "")
    st = load(base)
    old = st.requests.get(rid) if request_id else None
    if old:
        if old.get("content_hash") == ch and old["by"] == by:
            return {"duplicate": True, "request_id": rid, "status": old["status"]}
        raise Refused("request id %s already exists with different content" % rid)
    at = now()
    if partial is None:
        partial = gpus == ["all"]          # "all" = any free subset; an explicit list = all of them
    body = {"minutes": minutes, "gpus": gpus, "why": why, "content_hash": ch, "partial": bool(partial),
            "valid_until": iso(at + _dt.timedelta(hours=valid_hours)),
            "text": "GPU request %s: %s, %s, because: %s" % (
                rid, ("%d min" % minutes) if minutes else "as long as allowed",
                "all GPUs" if gpus == ["all"] else "GPU " + ",".join(gpus), why)}

    def dup_check(s):
        o = s.requests.get(rid)
        if o and o.get("content_hash") == ch:
            raise _Dup(rid, o["status"])
    try:
        ev = append(by, "request", request_id=rid, to="host", body=body, at=at, check=dup_check if request_id else None,
                    base=base, finish=None if request_id else _id_finisher("request"))
    except _Dup as d:
        return {"duplicate": True, "request_id": d.rid, "status": d.status}
    return {"duplicate": False, "request_id": ev["request_id"], "status": "submitted"}


class _Dup(Exception):
    def __init__(self, rid, status):
        super().__init__(rid)
        self.rid, self.status = rid, status


def cancel(request_id, by="agent", base=None):
    st = load(base)
    r = st.requests.get(request_id)
    if r and r["status"] == "cancelled" and r["by"] == by:
        return {"duplicate": True, "request_id": request_id}
    append(by, "cancel", request_id=request_id, to="host",
           body={"text": "Request %s cancelled by the agent." % request_id}, base=base)
    return {"duplicate": False, "request_id": request_id}


def grant_view(st, aid, at=None):
    """Everything the holder needs about one allocation, computed from the state."""
    al = st.allocs.get(aid)
    if not al:
        return None
    at = parse_iso(at or now())
    eff = st.effective_expires(aid)
    od = st.owner_deadline()
    rem = (eff - at).total_seconds() if eff else None
    usable = al["status"] == "active" and (rem is None or rem > 0)
    return {"allocation_id": aid, "request_id": al["request_id"], "status": al["status"],
            "usable": usable, "remaining_s": None if rem is None else max(0, int(rem)), "start": al["start"],
            "expires": al["expires"], "effective_expires": iso(eff) if eff else None, "next_start": al["next_start"],
            "gpus": al["gpus"], "verified_free": al["verified_free"], "end_reason": al["end_reason"],
            "owner_deadline": iso(od) if od else None, "owner_pending": bool(od),
            "expires_local": fmt_time(eff) if eff else "no set end (no next host start known)",
            "next_start_local": fmt_time(al["next_start"]) if al["next_start"] else "none known"}


def check_grant(aid, need_minutes=0, base=None, purpose="new"):
    """(ok, why): ok only for the CURRENT allocation, active, with enough time left before the
    EFFECTIVE end (the grant's end, or a pending owner deadline if sooner).
    purpose="new" (the default, and the CLI): may NEW GPU work start? Refused while an owner
    start order is pending -- whatever its length, new work is conflicting work then.
    purpose="continue": may work that was already admitted keep running? Yes until the
    effective end (the owner's deadline); the run wrapper polls this to stop its job in time."""
    if purpose not in ("new", "continue"):
        raise MailboxError("purpose must be new or continue")
    st = load(base)
    v = grant_view(st, aid)
    if not v:
        return False, "no allocation %s" % aid
    if v["status"] != "active" and not v["owner_pending"]:
        return False, "allocation %s is %s (%s); do not use its GPUs" % (aid, v["status"], v["end_reason"] or "ended")
    if v["status"] == "active" and not v["usable"] and v["owner_pending"]:
        return False, "the owner's deadline %s has passed on %s; stop and release now" % (
            fmt_time(v["owner_deadline"]), aid)
    if not v["usable"]:
        return False, "allocation %s is %s (%s); do not use the GPUs" % (aid, v["status"], v["end_reason"] or "ended")
    if purpose == "new" and v["owner_pending"]:
        return False, ("Orders from the GPU owner to start a job are pending: start no new GPU work on %s; finish or "
                       "checkpoint and release by %s" % (aid, fmt_time(v["owner_deadline"])))
    need = int(need_minutes or 0) * 60
    if v["remaining_s"] is None:
        return True, "%s on GPU %s has no set end (no next host start known); release when done" % (
            aid, ",".join(v["gpus"]))
    if v["remaining_s"] < need:
        return False, "only %s left on %s (ends %s), %d min needed" % (
            fmt_dur(v["remaining_s"]), aid, v["expires_local"], need_minutes)
    return True, "%s left on %s (GPU %s); stop by %s (next host job %s)" % (
        fmt_dur(v["remaining_s"]), aid, ",".join(v["gpus"]), v["expires_local"], v["next_start_local"])


def admit(aid, need_minutes=0, what="", by="agent", base=None):
    """Atomic admission of ONE new GPU job: a signed `admit` event the rule book accepts only for
    the holder's current active allocation, with no owner start pending and at least
    need_minutes left before the effective end -- decided under the mailbox lock, so an owner
    order recorded first always wins. Raises Refused otherwise. Start the job only after this."""
    return append(by, "admit", allocation_id=aid,
                  body={"need_s": int(need_minutes or 0) * 60, "what": str(what)[:200]}, base=base)


def register_pid(aid, pid, by="agent", base=None):
    created = proc_created(int(pid))
    if created is None:
        raise Refused("pid %s is not running" % pid)
    append(by, "register_pid", allocation_id=aid, body={"pid": int(pid), "created": created}, base=base)
    return created


def release(aid, note="", by="agent", base=None):
    st = load(base)
    al = st.allocs.get(aid)
    if al and al["released_at"] and (st.requests.get(al["request_id"]) or {}).get("by") == by:
        return {"duplicate": True, "allocation_id": aid}
    append(by, "release", allocation_id=aid, to="host",
           body={"note": note, "text": "Allocation %s released by the agent%s." % (
               aid, (": " + note) if note else "")}, base=base)
    return {"duplicate": False, "allocation_id": aid}


def receipt(event_id, kind, side, base=None):
    try:
        append(side, "receipt", body={"event_id": event_id, "kind": kind}, base=base)
        return True
    except Refused as e:
        if "duplicate receipt" in str(e):
            return False
        raise


def render(m):
    b = m.get("body") or {}
    head = "[%s] %s %s" % (m["seq"], m["type"].upper(), fmt_when(m["at"]))
    ids = " ".join(x for x in ("request=%s" % m["request_id"] if m.get("request_id") else "",
                               "allocation=%s" % m["allocation_id"] if m.get("allocation_id") else "",
                               "event=%s" % m["event_id"][:12]) if x)
    return "%s %s\n    %s" % (head, ids, b.get("text") or json.dumps(b)[:400])


# ------------------------------------------------------------------ host side senders
# The host system calls these so its replies travel through this
# same module. The host supplies the facts; the wording and the rules live here.
def send_ack(request_id, host_text, free_text, idle, base=None):
    if idle:
        text = ("Got your GPU request %s. This is a place in line, not permission to use the GPUs "
                "yet. %s I am checking the GPUs now; a \"you're clear\" message with your time "
                "follows if they are free." % (request_id, host_text))
    else:
        text = " ".join(x for x in (
            "Got your GPU request %s. This is a place in line, not permission: do not use the GPUs yet." % request_id,
            host_text, free_text,
            "When the host job is done I will send \"You're clear\" with how long you have before the next "
            "host job starts.") if x)
    return append("host", "ack", request_id=request_id, to="agent",
                  body={"text": text, "host": host_text, "expected_free": free_text,
                        "idle": bool(idle), "permission": False}, base=base)


def send_grant(request_id, next_start, next_start_kind, allowance_s, minutes=None,
               baseline_apps=None, facts_text="", code_ids=None, base=None, at=None, baseline_gpus=None,
               gpus=None, check=None):
    """Grant `gpus` (default: everything the request asked for) when a usable window exists before
    the next start. `next_start` None = no next start known: the grant then has no invented end
    (it lasts until released or reclaimed). Returns the event, or None after a no_window note.
    `check(state)` (optional) runs UNDER the mailbox lock just before the grant is judged and
    written (append's check); raising Refused there writes nothing. The host side re-reads its own
    preconditions (busy state, next start) in it."""
    at = parse_iso(at or now())
    st = load(base)
    req = st.requests.get(request_id)
    if not req:
        raise Refused("no request %s" % request_id)
    cfg = config(base)
    cfg_gpus = [str(x) for x in (cfg.get("gpus") or [])]
    outstanding = st.outstanding(req, cfg_gpus)
    granted = [str(x) for x in (gpus or outstanding)]
    ns = parse_iso(next_start) if next_start else None
    expires = (ns - _dt.timedelta(seconds=allowance_s)) if ns else None
    if minutes or req.get("minutes"):
        mexp = at + _dt.timedelta(minutes=int(minutes or req["minutes"]))
        expires = min(expires, mexp) if expires else mexp
    usable = (expires - at).total_seconds() if expires else None
    if usable is not None and usable < int(cfg.get("min_usable_s", MIN_USABLE_S)):
        key = "nowin:%s:%s" % (request_id, iso(ns) if ns else iso(expires))
        if key in st.notes:
            return None
        text = ("No usable GPU window for %s right now: the next host job starts %s (%s), which leaves "
                "%s after the %s handoff allowance. You stay in line for after that job." % (
                    request_id, fmt_when(ns, at) if ns else "?", next_start_kind, fmt_dur(max(0, usable)),
                    fmt_dur(allowance_s)))
        append("host", "no_window", request_id=request_id, to="agent",
               body={"key": key, "text": text, "next_start": iso(ns) if ns else None, "usable_s": int(max(0, usable))},
               base=base, at=at)
        return None
    aid = NEW_ID           # append's finish hook writes al-<minute>-s<seq>-<hex4> everywhere this appears
    rel_cmd = 'python "%s" release --allocation %s' % (_THIS_FILE, aid)
    gtxt = "GPU %s" % ",".join(granted)
    wanted = wanted_gpus(req["gpus"], cfg)
    left = [g for g in outstanding if g not in granted]
    part = bool(left) or sorted(granted) != sorted(wanted)
    ptxt = (" (you asked for GPU %s; this grant covers %s; GPU %s %s -- it is granted to you as a separate "
            "allocation the moment it is free)" % (",".join(wanted), gtxt, ",".join(left),
                                                    "is" if len(left) == 1 else "are")) if left else \
        ((" (the rest of request %s, which already holds GPU %s)" % (request_id, ",".join(req.get("granted_gpus") or [])))
         if req.get("granted_gpus") else "")
    if ns:
        left_to_start = (ns - at).total_seconds()
        text = ("You're clear. You have %s until the next host job starts (%s, %s). Your GPU time is "
                "allocation %s on %s for request %s%s: use the GPUs until %s, then stop and release; the %s "
                "before the start is the handoff allowance. Release early with: %s . On a warning or an "
                "owner order: stop starting new work, checkpoint, finish, and release before the deadline "
                "it gives.%s" % (fmt_dur(left_to_start), fmt_when(ns, at), next_start_kind, aid, gtxt, request_id,
                                 ptxt, fmt_when(expires, at), fmt_dur(allowance_s), rel_cmd,
                                 (" " + facts_text) if facts_text else ""))
    else:
        text = ("You're clear on %s. No next host start is known, so I am not giving your time an end I would "
                "have to invent%s: allocation %s for request %s lasts until you release it, the host "
                "needs the GPUs (then it is preempted at once), or an owner or scheduled start reclaims it (an owner start "
                "gives you 5 minutes' notice). Release with: %s .%s"
                % (gtxt, (" beyond your requested %d min (ends %s)" % (int(minutes or req["minutes"]), fmt_when(expires, at)))
                   if expires else "", aid, request_id, rel_cmd, (" " + facts_text) if facts_text else ""))
    body = {"gen": st.gen + 1, "gpus": granted, "requested_gpus": wanted, "partial": part,
            "expires": iso(expires) if expires else None, "next_start": iso(ns) if ns else None,
            "next_start_kind": next_start_kind if ns else "no next start known", "allowance_s": int(allowance_s),
            "remaining_s": int(usable) if usable is not None else None,
            "timezone": "%s (times stored as UTC ISO)" % _tz_name(),
            "start": iso(at), "start_local": fmt_time(at), "expires_local": fmt_time(expires) if expires else None,
            "next_start_local": fmt_time(ns) if ns else None, "early_release": rel_cmd,
            "preemption": "On a warning or owner_start message: admit no new GPU work, checkpoint, "
                          "finish, release before the stated deadline.",
            "baseline_apps": baseline_apps or [], "baseline_gpus": baseline_gpus or [],
            "facts": facts_text, "code_ids": code_ids or {},
            "text": text}
    return append("host", "grant", request_id=request_id, allocation_id=aid, to="agent",
                  body=body, base=base, at=at, finish=_id_finisher("alloc"), check=check)


def send_note(key, text, request_id=None, to="agent", base=None, at=None, **extra):
    try:
        return append("host", "status_note", request_id=request_id, to=to,
                      body=dict(extra, key=key, text=text), base=base, at=at)
    except Refused as e:
        if "duplicate status_note" in str(e):
            return None
        raise


def send_alloc_event(typ, aid, text, base=None, at=None, **extra):
    return append("host", typ, allocation_id=aid, to="agent", body=dict(extra, text=text),
                  base=base, at=at)


def send_owner_start(key, words, message_id, base=None, at=None, series=None, owner=None):
    """Durably record the owner's start order. Deadline = 300 s after THIS event's own time;
    a duplicate order (same key) returns the first record, so the countdown never resets.
    The target allocation, the addressee and the warning text are built UNDER the mailbox lock
    from the state the rule book checks: a grant that lands just before the order
    is the allocation the warning names; a grant after it is refused (owner priority)."""
    st = load(base)
    if key in st.owner_starts:
        return st.owner_starts[key], False

    def check(s):
        if key in s.owner_starts:
            raise _Dup(key, "exists")

    def build(s, at_iso):
        tg = s.owner_targets()
        deadline = parse_iso(at_iso) + _dt.timedelta(seconds=OWNER_GRACE_S)
        ids = [a["allocation_id"] for a in tg]
        if tg:
            aid = ids[0]
            parts = ["%s (GPU %s)" % (a["allocation_id"], ",".join(a["gpus"])) for a in tg]
            text = ("Orders from the GPU owner to start a job -- you have 5 minutes to finish up. Allocation%s %s: "
                    "stop starting new GPU work now, checkpoint, and release by %s (deadline %s). "
                    "Release with: %s" % ("s" if len(tg) > 1 else "", ", ".join(parts), fmt_time(deadline), iso(deadline),
                                          " ; ".join('python "%s" release --allocation %s' % (_THIS_FILE, x) for x in ids)))
        else:
            aid = None
            text = ("Orders from the GPU owner to start a job. You hold no GPU allocation, so nothing to stop; your "
                    "request(s) stay in line for after that job.")
        return {"allocation_id": aid,
                "to": "agent" if (tg or s.waiting(at_iso)) else None,
                "body": {"deadline": iso(deadline), "allocation_id": aid, "allocation_ids": ids, "text": text}}
    try:
        ev = append("host", "owner_start", body={"key": key, "words": words, "message_id": message_id,
                                                 "series": series, "owner": owner},
                    base=base, at=at, check=check, build=build)
    except _Dup:
        return load(base).owner_starts[key], False
    return load(base).owner_starts[key], ev is not None


def reserve_gpu(request_id, gpu, base=None, at=None, check=None):
    """host side: hold a free `gpu` for the OLDEST waiting exact multi-GPU request that cannot be
    fully granted yet (strict age order). The rule book refuses it for a partial request, while an
    owner order is pending, when an older request already reserved it, or right after this
    request's reservation on it lapsed. Lapses after reserve_s (default 600 s). `check(state)`
    (optional) runs under the mailbox lock before the reservation is judged and written."""
    at = parse_iso(at or now())
    try:
        lim = int(config(base).get("reserve_s", RESERVE_S))
    except MailboxError:
        lim = RESERVE_S
    until = at + _dt.timedelta(seconds=lim)
    return append("host", "reserve", request_id=request_id, to="agent",
                  body={"gpu": str(gpu), "until": iso(until),
                        "text": "GPU %s is held for your request %s (it needs more GPUs that are still busy) until %s; "
                                "no younger request can take it meanwhile. If the rest is not free by then, the hold "
                                "lapses and you stay first in line." % (gpu, request_id, fmt_time(until))},
                  base=base, at=at, check=check)


def claim_dispatch(key, base=None, at=None, lease_s=DISPATCH_LEASE_S, exclusive=False):
    """Claim the right to dispatch the owner's pending start. The rule book grants it only while
    every allocation is verified free and no other claim is inside its lease. Returns the
    claim id; raises Refused (with the reason) otherwise. exclusive=True also refuses, under
    the mailbox lock, while ANY other owner start holds a live claim (one order at the launcher at a
    time); the default False adds no such check."""
    cid = uuid.uuid4().hex[:16]

    def _one_at_a_time(s):
        when = at or now()
        for k, o in s.owner_starts.items():
            if k != key and o.get("status") == "pending":
                c = s.live_claim(k, when)
                if c:
                    raise Refused("owner start %s is being dispatched right now (claim %s at %s); one owner "
                                  "order at the launcher at a time, %s waits for it" % (k, c["claim_id"], c["at"], key))
    check = _one_at_a_time if exclusive else None
    append("host", "owner_start_dispatch", body={"key": key, "claim_id": cid, "lease_s": int(lease_s),
                                                 "by_pid": os.getpid()}, base=base, at=at, check=check)
    return cid


def record_owner_attempt(key, claim_id, error, kind="dispatch_failed", base=None, at=None):
    """Record ONE failed dispatch of the pending owner start `key` and release its claim
    `claim_id`. The order stays PENDING (only a verified start or the owner's cancel closes it), so the next
    dispatch claims again. Refused unless `claim_id` is the order's current claim. Returns the event."""
    return append("host", "owner_start_attempt", body={"key": key, "claim_id": claim_id, "kind": kind,
                                                       "error": str(error or "")[:600] or "(no error text)",
                                                       "by_pid": os.getpid()}, base=base, at=at)


def cancel_owner_start(key, words, message_id=None, base=None, at=None):
    """The owner's explicit cancel of the pending owner start `key` (their words, and the message id
    when known). Refused while a dispatch claim is inside its lease, or when the order is not pending."""
    return append("host", "owner_start_cancel", body={"key": key, "by": "owner", "words": str(words or "")[:300],
                                                      "message_id": message_id}, base=base, at=at)


def finish_owner_start(key, claim_id, result, outcome, base=None, at=None):
    """Close the owner start after its dispatch: result started | already_started (a verified start). Needs
    the claim (so it can never be closed over an unverified release).
    Only started / already_started close an order; a failed dispatch is record_owner_attempt (the
    order stays pending). gate_refused / dispatch_failed are REFUSED for EVERY key, route orders
    ("gw-") included. They stay legal in the rule book only for history (events already written fold as before).
    So no caller loaded against this file can close an owner start on a failure -- its claim lapses and the
    order is retried. Refused raised, nothing written."""
    if result in ("gate_refused", "dispatch_failed"):
        raise Refused("owner start %s: a failed dispatch (%s) never closes an owner start (every key incl. "
                      "\"%s\" route orders); it stays pending -- record_owner_attempt records the failure, only a "
                      "verified start or the owner's cancel closes it" % (key, result, ROUTE_KEY_PREFIX))
    return append("host", "owner_start_done", body={"key": key, "claim_id": claim_id, "result": result,
                                                    "outcome": str(outcome)[:600]}, base=base, at=at)


def executor_live(st, at=None):
    """The running retry executor record if its process is alive (same pid AND creation time)
    and it is not stopped, else None. Liveness is read from the process table, so a dead
    executor that never wrote executor_stop is not mistaken for a running one."""
    ex = st.executor
    if not ex or ex.get("stopped_at"):
        return None
    if not same_process(ex["pid"], ex.get("created")):
        return None
    return ex


def register_executor(cmd="", base=None):
    """Record THIS process as the one owner-start retry executor. Refused (Refused raised) if
    another live executor is recorded -- decided under the mailbox lock, so two launchers can
    never both run. Returns the record."""
    pid = os.getpid()
    created = proc_created(pid)

    def check(s):
        ex = executor_live(s)
        if ex and not (ex["pid"] == pid and ex.get("created") == created):
            raise Refused("retry executor pid %s (started %s) is already running" % (ex["pid"], ex["started_at"]))
    append("host", "executor_start", body={"pid": pid, "created": created, "cmd": str(cmd)[:300]},
           base=base, check=check)
    return load(base).executor


def executor_event(typ, reason="", base=None):
    """executor_stop for THIS process's record (liveness itself is read from the process table).
    The stop is ONE locked append: the rule book refuses it (Refused) while any owner start is
    pending, and the build hook records the final states it saw under that same lock."""
    pid = os.getpid()

    def build(s, at_iso):
        return {"body": {"final": [(k, o["status"]) for k, o in s.owner_starts.items()][-10:]}}
    return append("host", typ, body={"pid": pid, "created": proc_created(pid), "reason": str(reason)[:300]},
                  base=base, build=build)


def claim_current(key, claim_id, live=False, base=None, at=None):
    """True if `claim_id` is the CURRENT dispatch claim of the still-pending owner start `key`
    (and, with live=True, still inside its lease). Used to validate a claim handed down to a
    dispatcher (--claim-id) so every close path reuses it instead of claiming again."""
    if not claim_id:
        return False
    st = load(base)
    o = st.owner_starts.get(key)
    if not o or o["status"] != "pending" or not o.get("claim") or o["claim"]["claim_id"] != claim_id:
        return False
    return bool(st.live_claim(key, at or now())) if live else True


# ------------------------------------------------------------------ host-side GPU API
def _resolve_gpus(gpus, base=None):
    cfg = config(base)
    allg = [str(x) for x in (cfg.get("gpus") or ["0", "1"])]
    if gpus in (None, "all") or list(gpus) == ["all"]:
        return allg
    return [str(x) for x in gpus]


def host_acquire(gpus, purpose, kind="active", holder_pid=None, until=None, lease_id=None, base=None, at=None):
    """The host declares ACTIVE use of, or RESERVES imminent use of, specific GPUs (nvidia-smi
    indexes; "all" = every configured GPU, e.g. one job that spans all cards).
    Refused (Refused raised, nothing written) if any of them is granted to the agent -- the
    caller must then wait (host_wait_acquire) or use another GPU (host_acquire_any). holder_pid
    (default: this process) makes the lease end when that process ends; `until` (ISO) makes it end
    at that time. Returns the lease record (lease_id, gpus, kind, ...)."""
    gl = _resolve_gpus(gpus, base)
    if holder_pid is None and not until:
        holder_pid = os.getpid()
    created = proc_created(int(holder_pid)) if holder_pid else None
    if holder_pid and created is None:
        raise Refused("holder pid %s is not running" % holder_pid)
    lid = lease_id or NEW_ID              # a generated id is cl-s<seq>-<hex6> (single-use by construction)
    ev = append("host", "host_acquire", body={"lease_id": lid, "gpus": gl, "kind": kind, "purpose": str(purpose)[:200],
                                              "holder_pid": int(holder_pid) if holder_pid else None,
                                              "holder_created": created, "until": iso(until) if until else None},
                base=base, at=at, finish=None if lease_id else _id_finisher("lease"))
    return load(base).host_leases[ev["body"]["lease_id"]]


def host_acquire_any(candidates, purpose, n=1, kind="active", holder_pid=None, until=None, base=None):
    """For round-robin users (several worker lanes): atomically take
    `n` GPUs out of `candidates` that the agent does not hold, chosen UNDER the mailbox lock.
    Returns the lease (its "gpus" are the chosen ones); Refused if fewer than n are available."""
    cands = _resolve_gpus(candidates, base)
    if holder_pid is None and not until:
        holder_pid = os.getpid()
    created = proc_created(int(holder_pid)) if holder_pid else None
    if holder_pid and created is None:
        raise Refused("holder pid %s is not running" % holder_pid)
    def build(st, at_iso):
        free = [g for g in cands if not st.agent_hold(g)]
        if len(free) < n:
            raise Refused("only %d of GPU %s free of agent grants (%d needed)" % (len(free), ",".join(cands), n))
        return {"body": {"gpus": free[:n]}}
    ev = append("host", "host_acquire", body={"lease_id": NEW_ID, "gpus": [], "kind": kind, "purpose": str(purpose)[:200],
                                              "holder_pid": int(holder_pid) if holder_pid else None,
                                              "holder_created": created, "until": iso(until) if until else None},
                base=base, build=build, finish=_id_finisher("lease"))
    return load(base).host_leases[ev["body"]["lease_id"]]


def host_release(lease_id, base=None):
    """End a host lease. Idempotent (a second release returns {"duplicate": True}); a release
    names its own lease id, so an old release can never end a newer lease. that holds for
    ever, through retention: a lease id names exactly one acquisition (a generated id carries its
    acquisition's seq; a caller-chosen id is refused once used, on the snapshot path and in a full
    replay alike), so a delayed release of a retired lease is an idempotent no-op, never the end
    of a later acquisition."""
    st = load(base)
    l = st.host_leases.get(lease_id)
    if (l and l["released_at"]) or lease_id in st.released_lease_ids:
        return {"duplicate": True, "lease_id": lease_id}
    if not l:
        # unknown: never acquired, or released/expired more than RETAIN_S ago and left out of the
        # snapshot. Either way it holds nothing, so there is nothing to end: an idempotent no-op,
        # nothing written (the rule book would refuse a release of an unknown lease anyway).
        return {"duplicate": True, "unknown": True, "lease_id": lease_id}
    append("host", "host_release", body={"lease_id": lease_id}, base=base)
    return {"duplicate": False, "lease_id": lease_id}


def host_check(gpus=None, base=None):
    """Read-only: {gpu: owner} for the requested GPUs, where owner is None (free of agent),
    {"agent": allocation_id} or {"host": [lease ids]}. Not a reservation -- use host_acquire."""
    st = load(base)
    return {g: st.gpu_owner(g) for g in _resolve_gpus(gpus, base)}


def host_wait_acquire(gpus, purpose, timeout_s=None, poll_s=5.0, base=None, **kw):
    """host_acquire, retried every poll_s (clock time) while a GPU is granted out, until it
    succeeds or timeout_s passes (then the last Refused is raised). Grants end before the next scheduled start, and an owner or
    scheduled start reclaims them; a night job or script that must not wait passes timeout_s."""
    t0 = time.monotonic()
    while True:
        try:
            return host_acquire(gpus, purpose, base=base, **kw)
        except Refused:
            if timeout_s is not None and time.monotonic() - t0 >= timeout_s / (_test_clock()[2] if _test_clock() else 1.0):
                raise
            clock_sleep(poll_s)


def reclaim(aid, base=None):
    """Scoped reclamation: end exactly the processes registered on `aid`, after proving each is
    the registered process. Returns [(pid, ended, detail)]."""
    st = load(base)
    al = st.allocs.get(aid)
    out = []
    for p, c in (al or {}).get("pids", {}).items():
        ended, detail = terminate_exact(int(p), c)
        out.append((int(p), ended, detail))
    return out


# ------------------------------------------------------------------ CLI
def _cfg_or_empty():
    try:
        return config()
    except MailboxError:
        return {}


def _print_status(st, side, as_json=False):
    at = now()
    view = {"mailbox": root(), "now": iso(at), "now_local": fmt_time(at),
            "admission_open": st.admission_open(), "host_gpu_clear": st.host_gpu_clear(),
            "active_allocations": [a["allocation_id"] for a in st.active_allocs()],
            "reservations": {g: st.active_reservation(g, at) for g in wanted_gpus(["all"], _cfg_or_empty())},
            "admission_closed_why": st.admission_closed_why(), "current_allocation": st.current,
            "requests": sorted(st.requests.values(), key=State.age_key)[-10:],
            "allocations": [grant_view(st, a["allocation_id"], at) for a in sorted(st.allocs.values(), key=_grant_order)[-5:]],
            "owner_starts": sorted(st.owner_starts.values(), key=lambda o: (str(o.get("accepted_at") or ""), str(o.get("key"))))[-5:],
            "executor": st.executor, "executor_alive": bool(executor_live(st)),
            "gpu_owners": {g: st.gpu_owner(g, at) for g in wanted_gpus(["all"], _cfg_or_empty())},
            "host_leases_live": st.live_host_leases(at),
            "unread": len(st.unread(side)) if side else None,
            "invalid_events": st.invalid[-10:], "ignored_events": st.ignored[-10:]}
    if as_json:
        say(json.dumps(view, indent=1, default=str))
        return
    say("GPU-TIME STATUS at %s (mailbox %s)" % (fmt_time(at), root()))
    say("admission %s; current allocation %s" % ("OPEN" if view["admission_open"] else "CLOSED (%s)" % view["admission_closed_why"],
                                                 st.current or "none"))
    for r in view["requests"]:
        line = "  request %s: %s (asked %s, %s)" % (r["request_id"], r["status"], fmt_when(r["submitted_at"], at),
                                                   ("%d min" % r["minutes"]) if r["minutes"] else "as long as allowed")
        if r["status"] in ("submitted", "acked", "partial") and parse_iso(r["valid_until"]) <= at:
            line += " STALE since %s" % fmt_when(r["valid_until"], at)
        say(line)
    for v in view["allocations"]:
        say("  allocation %s (request %s): %s%s, ends %s, next host job %s, verified free %s" % (
            v["allocation_id"], v["request_id"], v["status"],
            (", %s left" % fmt_dur(v["remaining_s"])) if v["usable"] else "",
            v["expires_local"], v["next_start_local"], v["verified_free"]))
    for g, rv in view["reservations"].items():
        if rv:
            say("  GPU %s: RESERVED for the older request %s until %s" % (g, rv["request_id"], fmt_time(rv["until"])))
    for g, o in view["gpu_owners"].items():
        say("  GPU %s: %s" % (g, "free of agent and host leases" if not o else
                              ("granted to the agent (%s)" % o["agent"]) if "agent" in o else
                              ("in host use (%s)" % ", ".join(o["host"]))))
    if st.executor:
        say("  owner-start retry executor pid %s: %s" % (st.executor["pid"], "running" if view["executor_alive"] else
            "stopped (%s)" % (st.executor.get("stop_reason") or "process gone")))
    for o in view["owner_starts"]:
        say("  owner start %s: %s (deadline %s)%s%s" % (o["key"], o["status"], fmt_time(o["deadline"]),
                                                        (" -- %s" % o["outcome"]) if o.get("outcome") else "",
                                                        (" -- %s failed dispatch attempt(s), last at %s: %s" % (
                                                            o.get("attempt_count"), fmt_time(o.get("last_attempt_at")),
                                                            str(o.get("last_error") or "")[:160]))
                                                        if o.get("attempt_count") else ""))
    if side:
        say("unread for %s: %d" % (side, view["unread"]))
    if st.invalid:
        say("INVALID events ignored: %s" % st.invalid[-5:])


def watch(side, seconds, interval=10.0, base=None, rearm=None):
    """Exit the moment a message addressed to `side` has not been delivered yet; mark it
    delivered (a receipt signed by `side`), print it, and print the re-arm line."""
    rearm = rearm or 'python "%s" watch --side %s --seconds %d' % (_THIS_FILE, side, seconds)
    say("WATCH[GPU-%s] ARMED at %s -- every %gs, up to %ds" % (side.upper(), fmt_time(now()), interval, seconds))
    started = time.monotonic()
    while True:
        new = load(base).undelivered(side)
        if new:
            for m in new:
                receipt(m["event_id"], "delivered", side, base)
            say("=" * 64)
            say("*** GPU TIME MESSAGE FOR %s -- ACT ON THIS at %s" % (side.upper(), time.strftime("%I:%M:%S %p")))
            for m in new:
                say(render(m))
            say("NEXT: read and mark them: python \"%s\" inbox --side %s --mark-read" % (_THIS_FILE, side))
            say("=" * 64)
            say("RE-ARM WITH:")
            say("  " + rearm)
            return 0
        if time.monotonic() - started >= seconds:
            break
        time.sleep(interval)
    say("WATCH[GPU-%s] window elapsed with nothing to report." % side.upper())
    say("RE-ARM WITH:")
    say("  " + rearm)
    return 0


def _run_wrapped(aid, need_minutes, cmd, base=None):
    ok, why = check_grant(aid, need_minutes, base)
    if not ok:
        raise Refused(why)
    admit(aid, need_minutes, what=" ".join(cmd)[:200], base=base)      # atomic; raises Refused
    say("GRANT OK: " + why)
    child = subprocess.Popen(cmd)
    try:
        created = register_pid(aid, child.pid, base=base)
    except Exception:
        c = proc_created(child.pid)
        if c is not None:
            terminate_exact(child.pid, c)                    # the tree this wrapper just started
        else:
            child.terminate()
        raise
    say("RUNNING pid %s on %s" % (child.pid, aid))
    while True:
        rc = child.poll()
        if rc is not None:
            say("FINISHED pid %s exit %s. Release when your GPU work is done: python \"%s\" release --allocation %s"
                % (child.pid, rc, _THIS_FILE, aid))
            return rc
        ok, why = check_grant(aid, 0, base, purpose="continue")
        if not ok:
            say("GRANT ENDED (%s): stopping pid %s and its child processes, the job this wrapper started"
                % (why, child.pid))
            # The whole tree: on Windows the Python executable can be a launcher whose real interpreter is
            # its child, so ending only the direct child can leave the GPU job running.
            _ended, detail = terminate_exact(child.pid, created)
            say("  " + detail)
            try:
                child.wait(timeout=20)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=20)
            say("STOPPED pid %s. Now release: python \"%s\" release --allocation %s" % (child.pid, _THIS_FILE, aid))
            return EXIT_REFUSED
        time.sleep(5)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    p = sub.add_parser("request")
    p.add_argument("--minutes", type=int, default=None)
    p.add_argument("--why", required=True)
    p.add_argument("--gpus", default="all", help='"all" (default) or a comma list such as 0,1')
    p.add_argument("--request-id", default=None)
    p.add_argument("--valid-hours", type=float, default=DEFAULT_VALID_H)
    pg = p.add_mutually_exclusive_group()
    pg.add_argument("--partial", dest="partial", action="store_true", default=None,
                    help="accept any free subset of the GPUs asked for (default for --gpus all)")
    pg.add_argument("--exact", dest="partial", action="store_false",
                    help="only all of the GPUs asked for (default for an explicit list)")
    p = sub.add_parser("cancel")
    p.add_argument("--request-id", required=True)
    p = sub.add_parser("check-grant")
    p.add_argument("--allocation", required=True)
    p.add_argument("--need-minutes", type=int, default=0)
    p = sub.add_parser("run")
    p.add_argument("--allocation", required=True)
    p.add_argument("--need-minutes", type=int, default=0)
    p.add_argument("command", nargs=argparse.REMAINDER)
    p = sub.add_parser("register-pid")
    p.add_argument("--allocation", required=True)
    p.add_argument("--pid", type=int, required=True)
    p = sub.add_parser("release")
    p.add_argument("--allocation", required=True)
    p.add_argument("--note", default="")
    p = sub.add_parser("status")
    p.add_argument("--side", choices=SIDES, default="agent")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("inbox")
    p.add_argument("--side", choices=SIDES, required=True)
    p.add_argument("--mark-read", action="store_true")
    p.add_argument("--all", action="store_true")
    p = sub.add_parser("watch")
    p.add_argument("--side", choices=SIDES, required=True)
    p.add_argument("--seconds", type=int, default=3600)
    p.add_argument("--interval", type=float, default=10.0)
    p = sub.add_parser("verify")
    p.add_argument("--full", action="store_true", help="replay every event ever written (archive + events), no snapshot")
    p = sub.add_parser("compact", help="host side: snapshot the fold and move old events to archive/ (never deleted)")
    p.add_argument("--keep", type=int, default=COMPACT_KEEP)
    sub.add_parser("probe")
    p = sub.add_parser("host-acquire", help="host side: declare use of / reserve GPUs (see the docstring)")
    p.add_argument("--gpus", required=True, help='"all" or a comma list of nvidia-smi indexes, e.g. 0 or 0,1')
    p.add_argument("--purpose", required=True)
    p.add_argument("--kind", choices=HOST_KINDS, default="active")
    p.add_argument("--holder-pid", type=int, default=None, help="the process whose life bounds the lease")
    p.add_argument("--until", default=None, help="ISO time the lease ends (a reservation)")
    p.add_argument("--any", type=int, default=None, help="take this many of --gpus that are not granted out")
    p = sub.add_parser("host-release")
    p.add_argument("--lease", required=True)
    p = sub.add_parser("host-check")
    p.add_argument("--gpus", default="all")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "init":
            made = init()
            say("MAILBOX %s ready; created: %s" % (root(), ", ".join(made) or "nothing (already there)"))
            say("key fingerprints: host %s, agent %s (the keys themselves are never printed)"
                % (key_fingerprint("host"), key_fingerprint("agent")))
            return 0
        if a.cmd == "request":
            gpus = ["all"] if a.gpus.strip() == "all" else [g.strip() for g in a.gpus.split(",") if g.strip()]
            r = request(a.minutes, a.why, gpus, a.request_id, a.valid_hours, partial=a.partial)
            say("%s request %s (status %s). Wait for the host side's ack and then its \"you're clear\" "
                "grant before touching the GPUs." % ("DUPLICATE (same logical request):" if r["duplicate"] else "SUBMITTED",
                                                     r["request_id"], r["status"]))
            return 0
        if a.cmd == "cancel":
            r = cancel(a.request_id)
            say("%s %s" % ("ALREADY CANCELLED" if r["duplicate"] else "CANCELLED", a.request_id))
            return 0
        if a.cmd == "check-grant":
            ok, why = check_grant(a.allocation, a.need_minutes)
            say(("GO: " if ok else "NO-GO: ") + why)
            return 0 if ok else EXIT_REFUSED
        if a.cmd == "run":
            cmd = a.command[1:] if a.command[:1] == ["--"] else a.command
            if not cmd:
                raise MailboxError("run needs a command after --")
            return _run_wrapped(a.allocation, a.need_minutes, cmd)
        if a.cmd == "register-pid":
            c = register_pid(a.allocation, a.pid)
            say("REGISTERED pid %s on %s (process created %s)" % (a.pid, a.allocation, c))
            return 0
        if a.cmd == "release":
            r = release(a.allocation, a.note)
            say("%s %s. The host side verifies the GPUs are free and confirms." % (
                "ALREADY RELEASED" if r["duplicate"] else "RELEASED", a.allocation))
            return 0
        if a.cmd == "status":
            _print_status(load(), a.side, a.json)
            return 0
        if a.cmd == "inbox":
            st = load()
            msgs = [m for m in st.messages if m.get("to") == a.side] if a.all else st.unread(a.side)
            if not msgs:
                say("no %smessages for %s" % ("" if a.all else "unread ", a.side))
            for m in msgs:
                say(render(m))
                if a.mark_read and not (st.receipts.get((m["event_id"], a.side)) or {}).get("read"):
                    receipt(m["event_id"], "read", a.side)
            if a.mark_read and msgs:
                say("marked %d message(s) read for %s" % (len(msgs), a.side))
            return 0
        if a.cmd == "watch":
            return watch(a.side, a.seconds, a.interval)
        if a.cmd == "compact":
            r = compact(keep_tail=a.keep)
            say("COMPACTED: %s" % (r or "nothing to do"))
            return 0
        if a.cmd == "verify":
            recs = read_events(full=a.full)
            st = fold(recs)
            say("events %d, invalid %d, ignored %d" % (len(recs), len(st.invalid), len(st.ignored)))
            for s, why in st.invalid:
                say("  INVALID %08d: %s" % (s, why))
            for s, why in st.ignored:
                say("  IGNORED %08d: %s" % (s, why))
            return EXIT_VERIFY if st.invalid else 0
        if a.cmd in ("host-acquire", "host-check"):
            gl = "all" if a.gpus.strip() == "all" else [g.strip() for g in a.gpus.split(",") if g.strip()]
            if a.cmd == "host-check":
                say(json.dumps(host_check(gl), indent=1))
                return 0
            if a.holder_pid is None and not a.until:
                raise MailboxError("host-acquire from the command line needs --holder-pid (the process doing the GPU "
                                   "work) or --until; this short-lived command's own pid would end the lease at once")
            if a.any:
                l = host_acquire_any(gl, a.purpose, n=a.any, kind=a.kind, holder_pid=a.holder_pid, until=a.until)
            else:
                l = host_acquire(gl, a.purpose, kind=a.kind, holder_pid=a.holder_pid, until=a.until)
            say("HOST LEASE %s on GPU %s (%s, %s)" % (l["lease_id"], ",".join(l["gpus"]), l["kind"], l["purpose"]))
            return 0
        if a.cmd == "host-release":
            r = host_release(a.lease)
            say("%s %s" % ("ALREADY RELEASED" if r["duplicate"] else "RELEASED", a.lease))
            return 0
        if a.cmd == "probe":
            pr = gpu_probe()
            say(json.dumps(pr, indent=1))
            return 0 if pr["available"] else EXIT_QUERY
    except MailboxError as e:
        say(("REFUSED: " if isinstance(e, Refused) else "ERROR: ") + str(e))
        return e.code
    return EXIT_USAGE


if __name__ == "__main__":
    raise SystemExit(main())
