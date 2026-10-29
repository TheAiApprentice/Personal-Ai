"""Tests for gpu_time.py. Every test uses its own temp-dir mailbox (GPU_TIME_ROOT), never the default
one. No GPU, no nvidia-smi and no network are touched: telemetry is passed in as plain dicts.

Run:  python -m pytest tools/gpu_mailbox
"""
import datetime as dt
import hashlib
import hmac
import importlib.util
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "gpu_time.py"


def _load():
    spec = importlib.util.spec_from_file_location("gpu_time_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gt = _load()


@pytest.fixture()
def box(tmp_path, monkeypatch):
    """A fresh initialised mailbox in a temp dir; returns its path."""
    monkeypatch.setenv("GPU_TIME_ROOT", str(tmp_path))
    monkeypatch.delenv("GPU_TIME_CLOCK_ORIGIN", raising=False)
    gt.init()
    return tmp_path


def cli(box, *args):
    env = dict(os.environ, GPU_TIME_ROOT=str(box))
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=env, timeout=60)


FREE_PROBE = {"available": True, "apps": [],
              "gpus": [{"index": "0", "memory_used_mb": 300, "memory_total_mb": 24000, "util_pct": 1},
                       {"index": "1", "memory_used_mb": 200, "memory_total_mb": 24000, "util_pct": 0}]}


def granted(minutes=30, gpus=("0",), **kw):
    """request -> host ack -> host grant. Returns (request_id, allocation_id)."""
    r = gt.request(minutes=minutes, why="train a small model", gpus=list(gpus))
    rid = r["request_id"]
    gt.send_ack(rid, "The host is idle.", "", True)
    ev = gt.send_grant(rid, None, "none", 120, minutes=None, **kw)
    assert ev is not None
    return rid, ev["allocation_id"]


def forge(box, by, typ, signing_side, body, to=None, request_id=None, allocation_id=None, sign=True):
    """Write a hand-made event file as the next link of the chain (what an attacker with file access could try)."""
    last = gt.read_events()[-1]
    ev = {"protocol": gt.PROTOCOL, "seq": last.seq + 1, "event_id": uuid.uuid4().hex, "type": typ, "by": by,
          "at": gt.iso(gt.now()), "to": to, "request_id": request_id, "allocation_id": allocation_id,
          "body": body, "prev": hashlib.sha256(last.raw).hexdigest(), "code": "forged"}
    ev["sig"] = (hmac.new(gt._key(signing_side), gt._canonical(ev), hashlib.sha256).hexdigest()
                 if sign else "0" * 64)
    path = Path(box) / "events" / ("%08d.json" % ev["seq"])
    path.write_text(json.dumps(ev, sort_keys=True, indent=1), encoding="utf-8")
    return ev


# ------------------------------------------------------------------ the happy path

def test_init_creates_keys_config_and_lock(box):
    assert (box / "config.json").is_file() and (box / "lock").is_file()
    assert (box / "keys" / "host.key").is_file() and (box / "keys" / "agent.key").is_file()
    assert gt.init() == []                       # a second init rewrites nothing
    assert json.loads((box / "config.json").read_text())["gpus"] == ["0", "1"]


def test_request_ack_grant_check_release_flow(box):
    r = gt.request(minutes=30, why="train a small model", gpus=["0"])
    assert r == {"duplicate": False, "request_id": r["request_id"], "status": "submitted"}
    rid = r["request_id"]
    assert gt.load().requests[rid]["status"] == "submitted"

    gt.send_ack(rid, "The host is idle.", "", True)
    assert gt.load().requests[rid]["status"] == "acked"

    ev = gt.send_grant(rid, None, "none", 120, baseline_apps=[], baseline_gpus=FREE_PROBE["gpus"])
    aid = ev["allocation_id"]
    st = gt.load()
    assert st.allocs[aid]["status"] == "active" and st.allocs[aid]["gpus"] == ["0"]
    assert st.requests[rid]["status"] == "granted"

    ok, why = gt.check_grant(aid, need_minutes=10)
    assert ok, why
    ok, why = gt.check_grant(aid, need_minutes=120)          # asked for more than the grant has left
    assert not ok and "left" in why

    # the agent got a grant message addressed to it; reading it adds a receipt, nothing is removed
    msgs = gt.load().unread("agent")
    assert any(m["type"] == "grant" for m in msgs)
    assert gt.receipt(msgs[0]["event_id"], "read", "agent") is True
    assert gt.receipt(msgs[0]["event_id"], "read", "agent") is False     # duplicate receipt is a no-op

    assert gt.release(aid) == {"duplicate": False, "allocation_id": aid}
    assert gt.release(aid) == {"duplicate": True, "allocation_id": aid}
    ok, why = gt.check_grant(aid)
    assert not ok and "released" in why

    # the host verifies the GPUs are free and confirms
    verified, why = gt.verify_release(gt.load(), aid, probe=FREE_PROBE)
    assert verified, why
    gt.send_alloc_event("release_verified", aid, "GPUs are free again.")
    assert gt.load().allocs[aid]["verified_free"] is True
    assert gt.verify_release(gt.load(), "al-missing", probe=FREE_PROBE)[0] is False


def test_cli_flow_end_to_end(box):
    assert cli(box, "check-grant", "--allocation", "al-nope").returncode == 3      # nothing granted yet
    p = cli(box, "request", "--why", "demo job", "--minutes", "20", "--gpus", "0")
    assert p.returncode == 0 and "SUBMITTED" in p.stdout, p.stdout + p.stderr
    rid = gt.load().requests and next(iter(gt.load().requests))
    gt.send_ack(rid, "Idle.", "", True)
    aid = gt.send_grant(rid, None, "none", 120)["allocation_id"]
    p = cli(box, "check-grant", "--allocation", aid, "--need-minutes", "5")
    assert p.returncode == 0 and p.stdout.startswith("GO:"), p.stdout
    p = cli(box, "check-grant", "--allocation", aid, "--need-minutes", "999")
    assert p.returncode == 3 and p.stdout.startswith("NO-GO:")
    assert cli(box, "release", "--allocation", aid).returncode == 0
    assert "NO-GO" in cli(box, "check-grant", "--allocation", aid).stdout
    assert cli(box, "verify").returncode == 0
    assert cli(box, "status", "--json").returncode == 0


def test_admit_records_a_signed_event_and_refuses_too_long_jobs(box):
    rid, aid = granted(minutes=30)
    ev = gt.admit(aid, need_minutes=10, what="demo")
    assert ev["type"] == "admit" and ev["by"] == "agent"
    with pytest.raises(gt.Refused, match="left on"):
        gt.admit(aid, need_minutes=60)


def test_duplicate_request_is_idempotent_but_changed_content_is_refused(box):
    a = gt.request(minutes=15, why="same job", gpus=["0"], request_id="my-request-1")
    b = gt.request(minutes=15, why="same job", gpus=["0"], request_id="my-request-1")
    assert a["duplicate"] is False and b["duplicate"] is True
    with pytest.raises(gt.Refused, match="different content"):
        gt.request(minutes=16, why="same job", gpus=["0"], request_id="my-request-1")
    assert gt.cancel("my-request-1") == {"duplicate": False, "request_id": "my-request-1"}
    assert gt.cancel("my-request-1")["duplicate"] is True


# ------------------------------------------------------------------ minutes bounds

@pytest.mark.parametrize("minutes", [0, -5, 1441, 99999])
def test_minutes_out_of_range_is_refused(box, minutes):
    with pytest.raises(gt.Refused, match="minutes must be a whole number from 1 to 1440"):
        gt.request(minutes=minutes, why="too long or too short", gpus=["0"])
    assert gt.load().requests == {}


@pytest.mark.parametrize("minutes", [1, 1440])
def test_minutes_edges_are_accepted(box, minutes):
    assert gt.request(minutes=minutes, why="edge", gpus=["0"])["status"] == "submitted"


def test_minutes_bounds_on_the_command_line(box):
    p = cli(box, "request", "--why", "x", "--minutes", "0")
    assert p.returncode == 3 and "REFUSED" in p.stdout
    p = cli(box, "request", "--why", "x", "--minutes", "1441")
    assert p.returncode == 3
    assert cli(box, "request", "--why", "x", "--minutes", "1440").returncode == 0


def test_other_request_fields_are_checked(box):
    with pytest.raises(gt.Refused, match="gpus must be"):
        gt.request(minutes=10, why="x", gpus=["7"])
    with pytest.raises(gt.Refused, match="why must be 1-500"):
        gt.request(minutes=10, why="   ", gpus=["0"])
    with pytest.raises(gt.Refused, match="why must be 1-500"):
        gt.request(minutes=10, why="x" * 501, gpus=["0"])


# ------------------------------------------------------------------ who may write what

def test_agent_cannot_write_host_only_events(box):
    r = gt.request(minutes=10, why="x", gpus=["0"])
    for typ in ("grant", "ack", "owner_start", "revoke", "release_verified"):
        with pytest.raises(gt.Refused, match="may not write"):
            gt.append("agent", typ, request_id=r["request_id"])
    with pytest.raises(gt.Refused):
        gt.append("host", "request", request_id="rq-x", body={})        # and the host cannot request


def test_unacknowledged_request_cannot_be_granted(box):
    r = gt.request(minutes=30, why="x", gpus=["0"])
    with pytest.raises(gt.Refused, match="only an acknowledged, waiting request can be granted"):
        gt.send_grant(r["request_id"], None, "none", 120)


# ------------------------------------------------------------------ signatures and the append-only log

def test_events_are_signed_chained_and_verify_clean(box):
    granted()
    recs = gt.read_events(full=True)
    assert [r.seq for r in recs] == [1, 2, 3]
    assert all(not r.problem for r in recs)
    assert recs[1].ev["prev"] == hashlib.sha256(recs[0].raw).hexdigest()
    ev = recs[0].ev
    assert ev["sig"] == hmac.new(gt._key("agent"), gt._canonical(ev), hashlib.sha256).hexdigest()
    assert cli(box, "verify", "--full").returncode == 0


def test_an_existing_event_file_can_never_be_overwritten(box):
    granted()
    first = box / "events" / "00000001.json"
    before = first.read_bytes()
    with pytest.raises(FileExistsError):
        gt._write_new(str(first), b"{}")
    assert first.read_bytes() == before
    # nothing in the mailbox is ever removed by normal use
    names = sorted(p.name for p in (box / "events").iterdir())
    gt.release(next(iter(gt.load().allocs)))
    assert sorted(p.name for p in (box / "events").iterdir())[:len(names)] == names


def test_tampering_with_an_event_is_detected(box):
    rid, aid = granted()
    path = box / "events" / "00000001.json"
    ev = json.loads(path.read_text(encoding="utf-8"))
    ev["body"]["why"] = "something else entirely"
    path.write_text(json.dumps(ev, sort_keys=True, indent=1), encoding="utf-8")
    st = gt.fold(gt.read_events(full=True))
    problems = dict(st.invalid)
    assert problems[1] == "bad signature"
    assert "chain link" in problems[2]                  # everything after a broken link is distrusted
    assert rid not in st.requests                       # the tampered request never made it into the state
    p = cli(box, "verify", "--full")
    assert p.returncode == 4 and "INVALID 00000001: bad signature" in p.stdout


def test_event_signed_with_the_wrong_key_is_ignored(box):
    rid, _ = granted()
    # the agent signs an event that claims to be from the host: the host's key is what is checked
    forge(box, "host", "status_note", "agent", {"key": "k1", "text": "hello"}, to="agent")
    st = gt.fold(gt.read_events(full=True))
    assert any("bad signature" in why for _, why in st.invalid)
    assert "k1" not in st.notes


# ------------------------------------------------------------------ forged and stale grants

def test_forged_grant_with_a_bad_signature_is_ignored(box):
    r = gt.request(minutes=30, why="x", gpus=["0"])
    rid = r["request_id"]
    gt.send_ack(rid, "Idle.", "", True)
    fake = "al-forged-s9-abcd"
    forge(box, "host", "grant", "host", {"gen": 1, "gpus": ["0"], "expires": gt.iso(gt.now() + dt.timedelta(hours=1)),
                                         "next_start": None}, to="agent", request_id=rid, allocation_id=fake,
          sign=False)
    st = gt.load()
    assert fake not in st.allocs and st.requests[rid]["status"] == "acked"
    assert any(why == "bad signature" for _, why in st.invalid)
    ok, why = gt.check_grant(fake)
    assert not ok and "no allocation" in why


def test_grant_signed_by_the_agent_is_ignored(box):
    r = gt.request(minutes=30, why="x", gpus=["0"])
    rid = r["request_id"]
    gt.send_ack(rid, "Idle.", "", True)
    fake = "al-self-granted-1"
    forge(box, "agent", "grant", "agent", {"gen": 1, "gpus": ["0"], "expires": None, "next_start": None},
          to="agent", request_id=rid, allocation_id=fake)
    st = gt.load()
    assert fake not in st.allocs
    assert any("agent may not write 'grant' events" in why for _, why in st.invalid)
    assert gt.check_grant(fake)[0] is False


def test_stale_generation_grant_is_refused(box):
    r = gt.request(minutes=30, why="x", gpus=["0"])
    rid = r["request_id"]
    gt.send_ack(rid, "Idle.", "", True)
    body = {"gen": 5, "gpus": ["0"], "expires": gt.iso(gt.now() + dt.timedelta(hours=1)), "next_start": None}
    with pytest.raises(gt.Refused, match="stale grant: generation 5, expected 1"):
        gt.append("host", "grant", request_id=rid, allocation_id="al-x-1", to="agent", body=body)
    assert gt.load().allocs == {}


def test_grant_for_a_request_that_went_stale_is_refused(box):
    r = gt.request(minutes=30, why="x", gpus=["0"], valid_hours=1)
    rid = r["request_id"]
    gt.send_ack(rid, "Idle.", "", True)
    later = gt.now() + dt.timedelta(hours=2)
    with pytest.raises(gt.Refused, match="went stale"):
        gt.send_grant(rid, None, "none", 120, at=later)
    assert gt.load().allocs == {}


def test_cancelled_request_cannot_be_granted(box):
    r = gt.request(minutes=30, why="x", gpus=["0"])
    rid = r["request_id"]
    gt.send_ack(rid, "Idle.", "", True)
    gt.cancel(rid)
    with pytest.raises(gt.Refused, match="cancelled"):
        gt.send_grant(rid, None, "none", 120)


def test_a_request_cannot_be_granted_twice(box):
    rid, aid = granted()
    with pytest.raises(gt.Refused, match="only an acknowledged, waiting request"):
        gt.send_grant(rid, None, "none", 120)
    assert list(gt.load().allocs) == [aid]


def test_window_shorter_than_the_minimum_is_not_granted(box):
    r = gt.request(minutes=5, why="short", gpus=["0"])
    rid = r["request_id"]
    gt.send_ack(rid, "Idle.", "", True)
    # a window shorter than min_usable_s (10 minutes) is not granted at all: the host records a note instead
    assert gt.send_grant(rid, None, "none", 120) is None
    notes = [m for m in gt.load().messages if m["type"] == "no_window"]
    assert notes and "No usable GPU window" in notes[0]["body"]["text"]
    assert gt.load().allocs == {} and gt.load().requests[rid]["status"] == "acked"


def test_check_grant_refuses_a_grant_whose_time_is_over(box):
    r = gt.request(minutes=30, why="x", gpus=["0"])
    rid = r["request_id"]
    gt.send_ack(rid, "Idle.", "", True)
    past = gt.now() - dt.timedelta(hours=2)
    aid = gt.send_grant(rid, None, "none", 120, at=past)["allocation_id"]     # a 30-minute grant from 2 hours ago
    ok, why = gt.check_grant(aid)
    assert not ok and "do not use the GPUs" in why


def test_schedule_change_can_only_shorten(box):
    rid, aid = granted(minutes=60)
    exp = gt.load().allocs[aid]["expires"]
    longer = gt.iso(gt.parse_iso(exp) + dt.timedelta(hours=1))
    with pytest.raises(gt.Refused, match="only shorten"):
        gt.append("host", "schedule_change", allocation_id=aid, to="agent", body={"expires": longer})
    shorter = gt.iso(gt.parse_iso(exp) - dt.timedelta(minutes=20))
    gt.append("host", "schedule_change", allocation_id=aid, to="agent", body={"expires": shorter})
    assert gt.load().allocs[aid]["expires"] == shorter


# ------------------------------------------------------------------ GPU ownership and the owner order

def test_a_gpu_that_is_held_cannot_be_granted_again(box):
    granted(gpus=("0",))
    r2 = gt.request(minutes=30, why="second", gpus=["0"])
    gt.send_ack(r2["request_id"], "Idle.", "", True)
    with pytest.raises(gt.Refused, match="held by allocation"):
        gt.send_grant(r2["request_id"], None, "none", 120)
    # a different GPU is fine at the same time
    r3 = gt.request(minutes=30, why="third", gpus=["1"])
    gt.send_ack(r3["request_id"], "Idle.", "", True)
    assert gt.send_grant(r3["request_id"], None, "none", 120)["body"]["gpus"] == ["1"]


def test_host_use_of_a_gpu_blocks_a_grant_and_the_agent_blocks_a_lease(box):
    lease = gt.host_acquire(["0"], "host job", until=gt.now() + dt.timedelta(hours=1))
    assert gt.host_check(["0", "1"]) == {"0": {"host": [lease["lease_id"]]}, "1": None}
    r = gt.request(minutes=30, why="x", gpus=["0"])
    gt.send_ack(r["request_id"], "Busy.", "", False)
    with pytest.raises(gt.Refused, match="in host use"):
        gt.send_grant(r["request_id"], None, "none", 120)
    assert gt.host_release(lease["lease_id"]) == {"duplicate": False, "lease_id": lease["lease_id"]}
    assert gt.host_release(lease["lease_id"])["duplicate"] is True
    aid = gt.send_grant(r["request_id"], None, "none", 120)["allocation_id"]
    with pytest.raises(gt.Refused, match="is granted to the agent"):
        gt.host_acquire(["0"], "host job 2", until=gt.now() + dt.timedelta(hours=1))
    assert aid


def test_owner_start_closes_admission_and_blocks_new_work(box):
    rid, aid = granted(minutes=60)
    order, new = gt.send_owner_start("order-1", "start the job now", "msg-1")
    assert new is True and order["status"] == "pending"
    again, new2 = gt.send_owner_start("order-1", "start the job now", "msg-1")
    assert new2 is False and again["deadline"] == order["deadline"]          # the countdown never resets
    ok, why = gt.check_grant(aid, 1)
    assert not ok and "GPU owner" in why
    with pytest.raises(gt.Refused, match="no new GPU work may start"):
        gt.admit(aid, 1)
    r2 = gt.request(minutes=30, why="late", gpus=["1"])
    gt.send_ack(r2["request_id"], "Idle.", "", True)
    with pytest.raises(gt.Refused, match="admission is closed"):
        gt.send_grant(r2["request_id"], None, "none", 120)
    # the agent releases, the host verifies, then the dispatch claim is allowed
    gt.release(aid)
    with pytest.raises(gt.Refused, match="GPU clearance is not verified"):
        gt.claim_dispatch("order-1")
    gt.send_alloc_event("release_verified", aid, "free")
    claim = gt.claim_dispatch("order-1")
    gt.finish_owner_start("order-1", claim, "started", "job started")
    assert gt.load().owner_starts["order-1"]["status"] == "done"


# ------------------------------------------------------------------ telemetry helpers (pure functions)

def test_occupancy_free_occupied_unresolved():
    assert gt.occupancy(FREE_PROBE, ["0"])["state"] == "free"
    busy = {"available": True, "apps": [], "gpus": [{"index": "0", "memory_used_mb": 9000, "util_pct": 5}]}
    assert gt.occupancy(busy, ["0"])["state"] == "occupied"
    assert gt.occupancy({"available": False, "why": "no nvidia-smi"}, ["0"])["state"] == "unresolved"
    unknown = {"available": True, "apps": [], "gpus": [{"index": "0", "memory_used_mb": None, "util_pct": 5}]}
    assert gt.occupancy(unknown, ["0"])["state"] == "unresolved"       # never read as 0 MB


def test_unknown_or_unavailable_telemetry_never_verifies_a_release(box):
    rid, aid = granted()
    gt.release(aid)
    assert gt.verify_release(gt.load(), aid, probe={"available": False, "why": "down"})[0] is False
    still_used = {"available": True, "apps": [], "gpus": [{"index": "0", "memory_used_mb": 20000, "util_pct": 80}]}
    assert gt.verify_release(gt.load(), aid, probe=still_used)[0] is False


def test_parse_helpers_never_read_unknown_as_zero():
    assert gt._int_or_none("[N/A]") is None and gt._int_or_none("301 MiB") == 301
    apps, problems = gt.parse_compute_apps("1234, GPU-abc, worker.exe, [N/A]\n", {"GPU-abc": "0"})
    assert apps[0]["used_mb"] is None and apps[0]["gpu"] == "0" and problems == []
    gpus, problems = gt.parse_gpu_query("0, GPU-abc, 300, 24000, 1\n")
    assert gpus[0]["memory_used_mb"] == 300 and problems == []
    assert gt.parse_gpu_query("0, GPU-abc, [N/A], 24000, 1\n")[1]
