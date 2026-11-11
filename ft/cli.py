"""Command line: start/stop focus sessions, see today's totals, or run the daemon.

    python3 -m ft.cli daemon
    python3 -m ft.cli start TOC
    python3 -m ft.cli stop
    python3 -m ft.cli status
    python3 -m ft.cli today
"""

import argparse
import time

from . import store
from .classify import load_rules


def fmt(seconds: float) -> str:
    h, rem = divmod(int(seconds), 3600)
    m = rem // 60
    return f"{h}h {m:02d}m" if h else f"{m}m"


def main():
    p = argparse.ArgumentParser(prog="ft")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("daemon", help="run the window tracker in the foreground")
    s = sub.add_parser("start", help="start a focus session for a subject")
    s.add_argument("subject")
    sub.add_parser("stop", help="stop the current focus session")
    sub.add_parser("status", help="show the current session")
    sub.add_parser("today", help="show today's totals")
    sub.add_parser("login", help="log in to Supabase for cross-device sync")
    sub.add_parser("sync", help="upload unsynced rows now")
    args = p.parse_args()

    if args.cmd == "daemon":
        from .daemon import run
        run()
        return
    if args.cmd == "login":
        from .sync import interactive_login
        interactive_login()
        return

    conn = store.connect()
    if args.cmd == "sync":
        from .sync import SyncError, sync_once
        try:
            s, a = sync_once(conn)
            print(f"Synced {s} sessions and {a} activity rows.")
        except SyncError as e:
            print(f"Sync failed: {e}")
        return
    settings, _ = load_rules()
    device = settings.get("device", "laptop")

    if args.cmd == "start":
        store.start_session(conn, args.subject, device)
        print(f"Focus session started: {args.subject}")
    elif args.cmd == "stop":
        session = store.current_session(conn)
        if store.stop_session(conn):
            elapsed = time.time() - session["started_at"]
            print(f"Stopped {session['subject']} after {fmt(elapsed)}")
        else:
            print("No session is running.")
    elif args.cmd == "status":
        session = store.current_session(conn)
        if session:
            print(f"Running: {session['subject']} for {fmt(time.time() - session['started_at'])}")
        else:
            print("No session running.")
    elif args.cmd == "today":
        rows = store.today_summary(conn)
        if not rows:
            print("Nothing recorded today.")
            return
        for r in rows:
            label = r["subject"] or "(no subject)"
            print(f"{r['category']:<12} {label:<24} {fmt(r['seconds'])}")
        sessions = store.today_sessions(conn)
        print(f"\nFocus sessions today: {len(sessions)}")


if __name__ == "__main__":
    main()
