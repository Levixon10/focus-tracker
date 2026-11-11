"""Turns a window (class + title) into (category, subject, rule name) using rules.toml."""

import json
import re
import subprocess
import tomllib
from pathlib import Path

RULES_PATH = Path(__file__).resolve().parent.parent / "rules.toml"


def load_rules(path: Path = RULES_PATH):
    data = tomllib.loads(path.read_text())
    rules = []
    for r in data.get("rules", []):
        rules.append({
            "name": r["name"],
            "category": r["category"],
            "subject": r.get("subject", ""),
            "class": re.compile(r["class"]) if r.get("class") else None,
            "title": re.compile(r["title"]) if r.get("title") else None,
        })
    return data.get("settings", {}), rules


def active_window():
    """Return {'class', 'title'} for the focused window, or None."""
    try:
        out = subprocess.run(
            ["hyprctl", "activewindow", "-j"],
            capture_output=True, text=True, timeout=2,
        ).stdout
        info = json.loads(out or "{}")
    except (subprocess.SubprocessError, json.JSONDecodeError):
        return None
    if not info or not info.get("class"):
        return None
    return {"class": info.get("class", ""), "title": info.get("title", "")}


def classify(win, rules, session_subject: str = ""):
    """First matching rule wins. Returns (category, subject, rule_name)."""
    cls = win.get("class", "")
    title = win.get("title", "")
    for r in rules:
        if r["class"] is None and r["title"] is None:
            continue
        if r["class"] and not r["class"].search(cls):
            continue
        if r["title"] and not r["title"].search(title):
            continue
        cat = r["category"]
        if cat == "distraction":
            subj = session_subject  # distractions are attributed to the running session, if any
        elif cat in ("subject", "project"):
            subj = r["subject"] or session_subject
        else:
            subj = session_subject
        return cat, subj or "", r["name"]
    return "neutral", session_subject or "", "unmatched"
