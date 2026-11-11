"""Background loop: samples the focused window, records time, and nudges on long distraction."""

import subprocess
import time

from . import store
from .classify import active_window, classify, load_rules


def nudge(subject: str, minutes: int):
    where = f" during {subject}" if subject else ""
    subprocess.run([
        "notify-send", "-u", "normal", "Focus check",
        f"{minutes} min on distractions{where}. Back to work?",
    ])


def run(device_override: str | None = None):
    settings, rules = load_rules()
    poll = float(settings.get("poll_seconds", 5))
    nudge_after = float(settings.get("distraction_nudge_seconds", 180))
    device = device_override or settings.get("device", "laptop")

    conn = store.connect()
    print(f"[ft] running on '{device}', polling every {poll}s, {len(rules)} rules", flush=True)

    last = time.time()
    distraction_streak = 0.0
    nudged = False
    last_label = None

    while True:
        time.sleep(poll)
        now = time.time()
        # Cap elapsed so a suspended laptop does not add hours in one tick.
        elapsed = min(now - last, poll * 2)
        last = now

        session = store.current_session(conn)
        session_subject = session["subject"] if session else ""

        win = active_window()
        if win is None:
            distraction_streak, nudged = 0.0, False
            continue

        category, subject, rule = classify(win, rules, session_subject)
        store.add_activity(conn, now, device, category, subject, win["class"], win["title"], elapsed)

        label = f"{category}:{subject}:{rule}"
        if label != last_label:
            print(f"[ft] {time.strftime('%H:%M:%S')} {category:<11} {subject or '-':<22} {rule}", flush=True)
            last_label = label

        if category == "distraction" and session:
            distraction_streak += elapsed
            if distraction_streak >= nudge_after and not nudged:
                nudge(session_subject, int(distraction_streak // 60))
                nudged = True
        else:
            distraction_streak, nudged = 0.0, False
