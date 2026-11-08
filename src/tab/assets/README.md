# assets

## Purpose
Image files the app ships with.

## Contents
- `tab_icon.svg`: the app icon, a black-and-white graffiti "T". Built in layers (block shadow,
  outline, fill, shine, sparkle) from one shared letter shape in `<defs>`.
- `background.svg`: the "Hard Work is the Goal" graffiti wall behind the main screen (2560x1600,
  cover-scaled). Painted by `widgets/background.py`; not shown on the launch page.

## How it connects
`app.py` exposes `APP_ICON_PATH`; `__main__.py` sets it as the application's window icon.
`widgets/background.py` loads `background.svg` by path.
Packaged automatically with `src/tab` by hatchling.

## Conventions
- Prefer SVG so assets stay sharp at every size and can be edited as text.
- Black, white and the palette in `styles/theme.qss` only.
