# src

## Purpose
Holds the `tab` Python package: a PySide6 desktop Pomodoro timer and study helper.
Uses the `src/` layout so tests run against the installed package, not stray files in the repo root.

## Contents
- `tab/__main__.py`: entry point (`tab` console script and `python -m tab`). Builds the `QApplication`, loads the theme and settings.
- `tab/app.py`: `TabApplicationWindow`, the top-level window. Switches screens with a `QStackedWidget`,
  restores timer progress on launch, autosaves it every 5 s and on close.
- `tab/screens/`: full-window screens.
  - `splash.py`: plays the cube-to-"tab" intro, then continues on its own 3 s later
    (Tab/Space/Enter continue at once). Only clock, painting and keys; the geometry is in `core/cube_to_word_animation.py`.
  - `main.py`: views fill the window over the wall; Tab opens the switcher; Profile button in the bottom-left corner.
- `tab/widgets/`: reusable UI pieces.
  - `tab_switcher.py`: the Tab-key overlay: a centred horizontal row of views over the undimmed
    window. ←/→ or scroll moves the highlight; Enter or a left click anywhere chooses it (a click on
    a tile chooses that tile); Esc, Tab or a right click closes.
  - `themed_icon_button.py`: icon-only button whose line icon takes theme colours (switcher tiles,
    Profile corner button, timer controls).
  - `background.py`: `WallBackground`, the graffiti wall behind the main screen (SVG cover-scaled,
    faded by a translucent coat of wall colour, cached per size).
  - `view_icons.py`: view and control icons, drawn as QPainter lines on a 24x24 grid.
  - `chronograph_dial.py`: QPainter 3-6-9 dial. Centre hand = phase minutes (accent arc = phase length),
    3 = seconds, 6 = sessions toward the long break, 9 = focus-hours totaliser (12 h per turn).
  - `rotary_picker.py`: drum-style scroll/drag picker; used for choosing the phase.
  - `theme_colors.py`: helpers that let QPainter widgets take their colours from `theme.qss`.
- `tab/views/`: one widget per view: `workspace.py`, `timer_view.py`, `settings.py` (in the switcher) and `profile.py` (corner button).
- `tab/core/`: pure Python logic with **no Qt imports**.
  - `timer.py`: Pomodoro state machine and `TimerProgressSnapshot` (the restorable state).
  - `stopwatch.py`: start/pause/reset timing on an injectable monotonic clock (timer and splash).
  - `cube_to_word_animation.py`: the splash intro as pure maths: time in, line segments out.
  - `config.py` / `progress.py`: load and save settings and timer progress.
  - `json_storage.py`: shared pydantic ⇄ JSON helpers; writes are atomic (temp file + rename).
- `tab/styles/theme.qss`: the only place styling lives.
- `tab/assets/`: shipped images; `tab_icon.svg` is the app icon (graffiti "T").

## How it connects
Dependencies point one way: `__main__` → `app` → `screens` → `views`/`widgets` → `core`.
`core` never imports from the UI, so it stays testable without a display and the UI can be swapped
(e.g. a different dial design) without touching timer logic.

One `PomodoroSettings` instance is shared by `SettingsView` (edits and saves it) and `PomodoroTimer`
(reads durations from it on every query), so edits apply immediately with no signal wiring.

## Conventions
- No inline `setStyleSheet` calls. Give the widget an `objectName` and style it as `#object_name` in `theme.qss`.
- Colours used in QPainter code are exposed as Qt properties (camelCase, e.g. `accentColor`) and set in
  `theme.qss` with `qproperty-accentColor: #hex;`. The dial raises if any are missing.
- Adding a view to the switcher = add a view in `views/`, an icon in `view_icons.py`, and one entry
  in `MainScreen`'s `switcher_entries_with_views`.
- Files on disk (invalid files raise on startup rather than silently falling back to defaults):
  - Settings: `$XDG_CONFIG_HOME/tab/settings.json` (default `~/.config/tab/settings.json`).
  - Timer progress: `$XDG_STATE_HOME/tab/progress.json` (default `~/.local/state/tab/progress.json`).
- The timer always restores paused. `TimerPhase` values are stable ids on disk; never rename them,
  and keep display labels in the UI.
