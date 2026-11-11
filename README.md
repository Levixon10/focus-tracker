# focus-tracker

Laptop side of the focus tracker. Samples the focused Hyprland window, classifies it
(subject / project / distraction / neutral) using `rules.toml`, and stores time locally in SQLite.

## Usage

    cd ~/projects/focus-tracker
    python3 -m ft.cli start TOC      # start a focus session
    python3 -m ft.cli status
    python3 -m ft.cli stop
    python3 -m ft.cli today

Run the tracker in the background (not enabled yet):

    cp focus-tracker.service ~/.config/systemd/user/
    systemctl --user daemon-reload
    systemctl --user enable --now focus-tracker

Database: `~/.local/share/focus-tracker/local.db` (override with `FT_DB`).

## Editing rules

`rules.toml`: first matching rule wins. Put distraction rules first, then specific subjects, then broad ones.
Test a change with `python3 -c` calling `ft.classify.classify`, or watch the daemon output.

## Not done yet

- Supabase sync (needs a project URL and anon key). Rows carry a `synced` flag for this.
- Idle or screen-lock detection: while the screen is locked, the last window still counts.
- Phone dashboard.
