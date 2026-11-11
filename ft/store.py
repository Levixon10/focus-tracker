"""Local SQLite store. Every row has a `synced` flag so a later upload step can push
only new or changed rows to Supabase."""

import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path

DB_PATH = Path(os.environ.get("FT_DB", Path.home() / ".local/share/focus-tracker/local.db"))

SCHEMA = """
create table if not exists sessions (
    id          integer primary key autoincrement,
    subject     text    not null,
    started_at  real    not null,
    ended_at    real,
    device      text    not null,
    synced      integer not null default 0
);
create table if not exists activity (
    minute    integer not null,         -- unix time truncated to the minute
    device    text    not null,
    category  text    not null,         -- distraction | subject | project | neutral
    subject   text    not null default '',
    app       text    not null,
    title     text    not null default '',
    seconds   real    not null default 0,
    synced    integer not null default 0,
    primary key (minute, device, category, subject, app)
);
"""


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def current_session(conn):
    return conn.execute(
        "select * from sessions where ended_at is null order by started_at desc limit 1"
    ).fetchone()


def start_session(conn, subject: str, device: str):
    now = time.time()
    with conn:
        conn.execute("update sessions set ended_at=?, synced=0 where ended_at is null", (now,))
        conn.execute(
            "insert into sessions(subject, started_at, device) values (?, ?, ?)",
            (subject, now, device),
        )


def stop_session(conn):
    now = time.time()
    with conn:
        cur = conn.execute(
            "update sessions set ended_at=?, synced=0 where ended_at is null", (now,)
        )
    return cur.rowcount > 0


def add_activity(conn, when, device, category, subject, app, title, seconds):
    minute = int(when // 60) * 60
    with conn:
        conn.execute(
            """insert into activity(minute, device, category, subject, app, title, seconds, synced)
               values (?, ?, ?, ?, ?, ?, ?, 0)
               on conflict(minute, device, category, subject, app)
               do update set seconds = seconds + excluded.seconds,
                             title = excluded.title, synced = 0""",
            (minute, device, category, subject, app, title[:200], seconds),
        )


def today_summary(conn):
    """Seconds per (category, subject) since local midnight."""
    midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    return conn.execute(
        """select category, subject, sum(seconds) as seconds
           from activity where minute >= ?
           group by category, subject order by seconds desc""",
        (midnight,),
    ).fetchall()


def today_sessions(conn):
    midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    return conn.execute(
        "select * from sessions where started_at >= ? order by started_at", (midnight,)
    ).fetchall()
