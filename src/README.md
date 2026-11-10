# src

## Purpose
Holds the `tab` Python package: a PySide6 desktop Pomodoro timer and study helper.
Uses the `src/` layout so tests run against the installed package, not stray files in the repo root.

## Contents
- `tab/__main__.py`: entry point (`tab` console script and `python -m tab`). Builds the `QApplication`, loads the theme and settings.
  Single instance per progress file: a second launch brings the running window forward and exits
  (a `QLocalServer` named after a hash of the progress file path).
- `tab/app.py`: `TabApplicationWindow`, the top-level window. Switches screens with a `QStackedWidget`,
  restores timer progress on launch, autosaves it every 5 s and on close.
- `tab/screens/`: full-window screens.
  - `splash.py`: plays the cube-to-"tab" intro with its soundtrack, then continues on its own 3 s
    later (Tab/Space/Enter continue at once and cut the sound). Only clock, painting and keys; the geometry is in `core/cube_to_word_animation.py`.
  - `main.py`: views fill the window over the wall; Tab opens the switcher; Ctrl+Tab / Ctrl+Shift+Tab
    move keyboard focus through the open view's controls; Space starts/pauses the open Timer or
    Duration view (unless a focused control takes it); Profile button in the bottom-left corner;
    Ctrl+S opens the Shortcuts page and Ctrl+P opens Profile; the same key pressed on that page
    returns to the page you came from.
- `tab/widgets/`: reusable UI pieces.
  - `tab_switcher.py`: the Tab-key overlay: a centred horizontal row of views over the undimmed
    window. ←/→, Ctrl+Tab / Ctrl+Shift+Tab, or scroll moves the highlight; Enter or a left click
    anywhere chooses it (a click on a tile chooses that tile); Esc, Tab or a right click closes.
  - `themed_icon_button.py`: icon-only button whose line icon takes theme colours (switcher tiles,
    Profile corner button, timer controls).
  - `background.py`: `WallBackground`, the graffiti wall behind the main screen (SVG cover-scaled,
    faded by a translucent coat of wall colour, cached per size).
  - `view_icons.py`: view and control icons, drawn as QPainter lines on a 24x24 grid. The Duration
    icon is the view's own trefoil drawn as a knot diagram (gaps where a strand passes under).
  - `chronograph_dial.py`: QPainter 3-6-9 dial. Centre hand = phase minutes (accent arc = phase length;
    phases over an hour add one ring outside the face per lap still to come),
    3 = seconds, 6 = sessions toward the long break, 9 = focus-hours totaliser (12 h per turn).
  - `rotary_picker.py`: drum-style scroll/drag picker (Up/Down too, if the caller gives it focus);
    used for choosing the phase and, as hours:minutes drum pairs, for the durations in Settings.
  - `theme_colors.py`: helpers that let QPainter widgets take their colours from `theme.qss`.
  - `duration_knot.py`: the Duration view's trefoil: dots of varying size flowing along it while
    the duration runs and the knot tumbles in 3D, swelling into one solid tube when paused. Each
    dot is shaded exactly by depth (far to near), so the tube has no visible bands. While paused
    it's a fidget toy: drag to turn it any way, flick to set it coasting; drags are ignored
    while the timer runs. Redraws at
    ~30 fps only while something moves; once solid or hidden it stops its frame timer.
  - `session_rating_row.py`: "Rate that session's impact" with the 1/2/3/5/8 chips and a small ×
    at the prompt's top left to skip; used by the Timer and Duration views.
  - `info_article.py`: the "i" button and the dialog it opens, a scrollable Markdown short read
    from `assets/` with baby blue headings; used beside the Timer and Duration clocks.
  - `callout_card.py`: the rounded cards (with title and label/value rows) that Settings and Profile
    are built from, so both pages share one look.
- `tab/views/`: one widget per view: `workspace.py`, `timer_view.py`, `duration_view.py`, `settings.py` (in the switcher), `profile.py` (corner button) and `shortcuts.py` (Ctrl+S or Settings).
  - `duration_view.py`: open-ended focus session (knot icon): the knot over a count-up clock,
    with Start, Pause and Reset in a row and a full-width Finish ✓ beneath (as on the Timer);
    Reset zeroes it without a session, Finish asks for the session's impact rating. An "i"
    beside the clock (in line with Finish's outer edge) opens a short read on the trefoil
    (`assets/trefoil_knot.md`).
  - `profile.py`: callout cards: today's focus time and sessions; all-time focus, sessions and
    Impact Score (average session rating, out of 8), a grey "Since:" date under all-time focus,
    and a red reset that asks you to type "hard work is the goal"; the dial's focus hours (with
    the totaliser reset). Duration sessions count towards all of these too.
  - `shortcuts.py`: every key binding and knot gesture as callout cards in two columns, keys drawn
    as keycaps. The list is written out by hand: a new key binding must be added here too.
  - `settings.py`: stacked callout cards (Pomodoro, Short break, Long break, General: phase
    labels; Intro sound, which silences the splash soundtrack from the next launch; and
    Notifications, which stops the phase-end notification at once, keeping the pause, swoosh
    and hold; Link work and duration, which shares one clock between work phases and the
    duration), then a Shortcuts title card with a square ⌘ button beside it that opens the
    Shortcuts page. Duration
    drums stay collapsed to the picked value and expand on hover or keyboard focus.
  - `timer_view.py` has a full-width ✓ under Start/Pause/Reset that completes the work session
    early (enabled once a work phase has started), and an "i" beside the countdown opens a short
    read on the Pomodoro Technique (`assets/pomodoro_technique.md`). It shows the session rating
    buttons during
    the break after a work session, and
    also owns phase-end alerts: the timer pauses, a desktop notification names the next phase
    (sent over D-Bus with jeepney on Linux at normal urgency, so GNOME shows a banner; else a
    system-tray icon; else an in-window toast) and the swoosh snap plays, then after a 3 s hold
    the view moves to that phase, stopped until the user presses Start.
- `tab/core/`: pure Python logic with **no Qt imports**.
  - `timer.py`: Pomodoro state machine and `TimerProgressSnapshot` (the restorable state), including
    today's focus time and sessions (start over when the local date changes), all-time focus, and
    session ratings (1/2/3/5/8, given during the break after a work session). The long-break cycle
    has its own counter, so resetting all-time stats doesn't move it; the reset restarts the
    all-time "since" date. Also owns the open-ended duration session: a count-up that counts as
    focus while it runs and as a completed session (not toward the long break) when finished.
    With "Link work and duration" on (off by default), a WORK phase and the duration share one
    clock: starting or pausing either does both; starting the duration in a break returns to a
    fresh WORK phase; the duration rests during breaks; and completing a session from either
    side (phase runs out, Timer ✓, Duration ✓) counts one session, moves on to the break and
    zeroes the duration; either Reset resets both during a work phase. Off, starting one pauses
    the other and each resets and completes on its own.
    Toggling the setting pauses both clocks. Focus counts once either way. A pending rating
    can be rated or skipped.
  - `stopwatch.py`: start/pause/reset timing on an injectable monotonic clock (timer and splash).
  - `cube_to_word_animation.py`: the splash intro as pure maths: time in, line segments out.
  - `knot_animation.py`: the Duration knot as pure maths: dots resampled at equal 3D arc length
    along a trefoil, turned by a 3x3 orientation matrix and projected. `KnotAnimationState`
    advances flow, wobble, solidity and the auto-spin (about an axis tilted 40° off the line of
    sight) by elapsed time, and owns the paused fidget physics: trackball drag, flick, coast.
  - `config.py` / `progress.py`: load and save settings and timer progress.
  - `json_storage.py`: shared pydantic ⇄ JSON helpers; writes are atomic (temp file + rename).
- `tab/styles/theme.qss`: the only place styling lives.
- `tab/assets/`: shipped images and sounds; `tab_icon.svg` is the app icon (graffiti "T").

## How it connects
Dependencies point one way: `__main__` → `app` → `screens` → `views`/`widgets` → `core`.
`core` never imports from the UI, so it stays testable without a display and the UI can be swapped
(e.g. a different dial design) without touching timer logic.

One `PomodoroSettings` instance is shared by `SettingsView` (edits and saves it) and `PomodoroTimer`
(reads durations from it on every query), so edits apply immediately with no signal wiring.

## Conventions
- No inline `setStyleSheet` calls. Give the widget an `objectName` and style it as `#object_name` in `theme.qss`.
- Tabbable controls: give an interactive widget `setFocusPolicy(Qt.FocusPolicy.TabFocus)` so Ctrl+Tab
  reaches it but a click doesn't leave it focused, and show focus in tan (`:focus` in `theme.qss`, or
  in `paintEvent` for QPainter widgets, as `RotaryPicker` does).
- Colours used in QPainter code are exposed as Qt properties (camelCase, e.g. `accentColor`) and set in
  `theme.qss` with `qproperty-accentColor: #hex;`. The dial raises if any are missing.
- Adding a view to the switcher = add a view in `views/`, an icon in `view_icons.py`, and one entry
  in `MainScreen`'s `switcher_entries_with_views`.
- Adding a keyboard shortcut = one `MainScreen._add_shortcut("Ctrl+X", action)` call (it closes an
  open switcher first unless `closes_open_tab_switcher=False`), plus a row in `views/shortcuts.py`.
- Files on disk (invalid files raise on startup rather than silently falling back to defaults):
  - Settings: `$XDG_CONFIG_HOME/tab/settings.json` (default `~/.config/tab/settings.json`).
  - Timer progress: `$XDG_STATE_HOME/tab/progress.json` (default `~/.local/state/tab/progress.json`).
- The timer always restores paused. `TimerPhase` values are stable ids on disk; never rename them,
  and keep display labels in the UI.
