# assets

## Purpose
Image and sound files the app ships with.

## Contents
- `tab_icon.svg`: the app icon, a bone-white capital T shaped like two brush strokes (round loaded
  start, uneven edges, tapering end) merged into one solid letter with a soft grey outline, stem
  centred on the crossbar, turned 90° clockwise so its top points right. Generated with a fixed seed.
- `background.svg`: the "Hard Work is the Goal" graffiti wall behind the main screen (2560x1600,
  cover-scaled). Painted by `widgets/background.py`; not shown on the launch page.
- `ding_ding.wav`: the two-note bell (E6 then C6) played when a timer phase ends. Synthesised sine
  partials with an exponential decay, mono 44.1 kHz.

## How it connects
`app.py` exposes `APP_ICON_PATH`; `__main__.py` sets it as the application's window icon.
`widgets/background.py` loads `background.svg` by path.
`views/timer_view.py` loads `ding_ding.wav` by path.
Packaged automatically with `src/tab` by hatchling.

## Conventions
- Prefer SVG for images so they stay sharp at every size and can be edited as text.
- Colours from the palette in `styles/theme.qss` (black, bone, tan, the greys) or shades of them.
