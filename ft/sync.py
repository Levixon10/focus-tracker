"""Uploads unsynced local rows to Supabase (plain REST, standard library only).

Config lives at ~/.config/focus-tracker/config.json (chmod 600), written by `ft login`:
    {"url": "https://xyz.supabase.co", "anon_key": "...", "refresh_token": "..."}
Only the refresh token is stored, never the password.
"""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from getpass import getpass
from pathlib import Path

from . import store

CONFIG_PATH = Path(os.environ.get("FT_CONFIG", Path.home() / ".config/focus-tracker/config.json"))
BATCH = 500


class SyncError(Exception):
    pass


def load_config():
    if not CONFIG_PATH.exists():
        raise SyncError("not logged in. Run: python3 -m ft.cli login")
    return json.loads(CONFIG_PATH.read_text())


def save_config(cfg):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))
    os.chmod(CONFIG_PATH, 0o600)


def _request(method, url, key, body=None, token=None, extra_headers=None):
    headers = {"apikey": key, "Content-Type": "application/json"}
    headers["Authorization"] = f"Bearer {token or key}"
    headers.update(extra_headers or {})
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raise SyncError(f"{method} {url} -> {e.code}: {e.read().decode()[:300]}") from e
    except urllib.error.URLError as e:
        raise SyncError(f"network error: {e.reason}") from e


def login(email: str, password: str, url: str, anon_key: str):
    data = _request(
        "POST", f"{url}/auth/v1/token?grant_type=password", anon_key,
        body={"email": email, "password": password},
    )
    save_config({"url": url, "anon_key": anon_key, "refresh_token": data["refresh_token"]})


def access_token(cfg):
    """Exchange the stored refresh token for a fresh access token and rotate it."""
    data = _request(
        "POST", f"{cfg['url']}/auth/v1/token?grant_type=refresh_token", cfg["anon_key"],
        body={"refresh_token": cfg["refresh_token"]},
    )
    cfg["refresh_token"] = data["refresh_token"]
    save_config(cfg)
    return data["access_token"]


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def sync_once(conn) -> tuple[int, int]:
    """Push unsynced sessions and activity. Returns (sessions_sent, activity_sent)."""
    cfg = load_config()
    token = access_token(cfg)
    base, key = cfg["url"], cfg["anon_key"]
    upsert = {"Prefer": "resolution=merge-duplicates,return=minimal"}

    sessions = conn.execute("select * from sessions where synced = 0").fetchall()
    if sessions:
        rows = [{
            "subject": s["subject"],
            "started_at": _iso(s["started_at"]),
            "ended_at": _iso(s["ended_at"]) if s["ended_at"] else None,
            "device": s["device"],
        } for s in sessions]
        _request("POST", f"{base}/rest/v1/sessions?on_conflict=user_id,device,started_at",
                 key, body=rows, token=token, extra_headers=upsert)
        with conn:
            conn.executemany("update sessions set synced = 1 where id = ?",
                             [(s["id"],) for s in sessions])

    activity = conn.execute("select * from activity where synced = 0").fetchall()
    sent = 0
    for i in range(0, len(activity), BATCH):
        chunk = activity[i:i + BATCH]
        rows = [{
            "minute": _iso(a["minute"]),
            "device": a["device"],
            "category": a["category"],
            "subject": a["subject"],
            "app": a["app"],
            "title": a["title"],
            "seconds": a["seconds"],
        } for a in chunk]
        _request("POST",
                 f"{base}/rest/v1/activity?on_conflict=user_id,minute,device,category,subject,app",
                 key, body=rows, token=token, extra_headers=upsert)
        with conn:
            conn.executemany(
                "update activity set synced = 1 where minute = ? and device = ? and category = ? and subject = ? and app = ?",
                [(a["minute"], a["device"], a["category"], a["subject"], a["app"]) for a in chunk],
            )
        sent += len(chunk)

    pull_sessions(conn, cfg, token)
    return len(sessions), sent


def _parse_iso(s):
    return datetime.fromisoformat(s).timestamp() if s else None


def pull_sessions(conn, cfg, token):
    """Bring phone sessions (last 2 days) into the local DB so the laptop daemon
    can attribute time and nudge during them. Runs after the push, so local
    rows are already synced and the remote copy wins."""
    since = _iso(time.time() - 2 * 86400)
    rows = _request(
        "GET",
        f"{cfg['url']}/rest/v1/sessions?device=neq.laptop&started_at=gte.{urllib.parse.quote(since)}&select=subject,started_at,ended_at,device",
        cfg["anon_key"], token=token,
    ) or []
    with conn:
        for r in rows:
            conn.execute(
                """insert into sessions(subject, started_at, ended_at, device, synced)
                   values (?, ?, ?, ?, 1)
                   on conflict(device, started_at)
                   do update set subject = excluded.subject, ended_at = excluded.ended_at, synced = 1""",
                (r["subject"], _parse_iso(r["started_at"]), _parse_iso(r["ended_at"]), r["device"]),
            )


def interactive_login():
    url = input("Supabase project URL (https://xyz.supabase.co): ").strip().rstrip("/")
    anon_key = input("Supabase anon key: ").strip()
    email = input("Email: ").strip()
    password = getpass("Password: ")
    login(email, password, url, anon_key)
    print("Logged in. Refresh token saved.")
