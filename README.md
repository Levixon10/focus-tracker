# focus-tracker

Laptop side of the focus tracker. Samples the focused Hyprland window, classifies it
(subject / project / distraction / neutral) using `rules.toml`, and stores time locally in SQLite.

## Usage

    cd ~/projects/focus-tracker
    python3 -m ft.cli start TOC      # start a focus session
    python3 -m ft.cli status
    python3 -m ft.cli stop
    python3 -m ft.cli today

## Cross-device sync (Supabase)

1. In Supabase, create a project, then SQL Editor -> paste `supabase/schema.sql` -> Run.
2. Create your login: Authentication -> Users -> Add user (email + password).
3. On the laptop: `python3 -m ft.cli login` (asks for project URL, anon key, email, password).
   Only a refresh token is stored, in `~/.config/focus-tracker/config.json` (chmod 600).
4. `python3 -m ft.cli sync` to test. The daemon also syncs every 60 seconds.

Sync is two-way: laptop activity and sessions go up, and phone sessions from the last 2 days come down,
so the laptop attributes time and nudges during phone sessions too.

## Phone app

`docs/` is the installable web app, published with GitHub Pages.
Open it on Android Chrome, then menu -> "Install app". Log in with the same Supabase URL, anon key, email and password.

Phone nudge: while a session runs on the phone, the app checks the laptop's distraction time in the last 4 minutes
and alerts you (in-app banner, notification if allowed, vibration). It only runs while the app is open or in the foreground.

Run the tracker in the background (not enabled yet):

    cp focus-tracker.service ~/.config/systemd/user/
    systemctl --user daemon-reload
    systemctl --user enable --now focus-tracker

Database: `~/.local/share/focus-tracker/local.db` (override with `FT_DB`).

## Editing rules

`rules.toml`: first matching rule wins. Put distraction rules first, then specific subjects, then broad ones.
Test a change with `python3 -c` calling `ft.classify.classify`, or watch the daemon output.

## Not done yet

- Idle or screen-lock detection: while the screen is locked, the last window still counts.
- Automatic phone app-usage tracking (needs a native Android app; the web app is timers only).
- Weekly targets per subject.
