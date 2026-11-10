# assets

## Purpose
Image, sound and text files the app ships with.

## Contents
- `tab_icon.svg`: the app icon, a bone-white capital T shaped like two brush strokes (round loaded
  start, uneven edges, tapering end) merged into one solid letter with a soft grey outline, stem
  centred on the crossbar, turned 90° clockwise so its top points right. Generated with a fixed seed.
- `background.svg`: the "Hard Work is the Goal" graffiti wall behind the main screen (2560x1600,
  cover-scaled). Painted by `widgets/background.py`; not shown on the launch page.
- `swoosh_snap.wav`: played when a timer phase ends, echoing the splash (the cube drops, then locks
  into "tab"): a rising swoosh (noise through a band-pass sweeping 300 Hz to 3.5 kHz) ending in a
  snap (a short crack, a 95 Hz thump and a faint 2.6 kHz tick). Synthesised, mono 44.1 kHz, 0.87 s.
- `splash_intro.wav`: the splash soundtrack (5.7 s), timed to the constants in
  `core/cube_to_word_animation.py`: a low rumble as the cube falls, heavy impacts at each landing, a
  turbine whir that rises with the spin, a boom and 12 steel-bar clangs at the burst, a bolt-like
  clunk as each edge lands in the word, then an anvil clank. Deliberately deeper than the phase-end
  sound and never reuses its snap. Synthesised and saturated (tanh) so the low end carries on
  laptop speakers; mono 44.1 kHz. **Regenerate it if those animation timings change.**

- `trefoil_knot.md`: the ~5 minute read behind the Duration view's "i" button: what a mathematical
  knot is, tricolourability as a proof, handedness, the formulas the animation uses, Kelvin's
  vortex atoms, knot counts, uses in DNA, physics and computing, and open problems. Written as
  general-audience maths (no references to the app). Rendered as Markdown by Qt.

- `pomodoro_technique.md`: the ~5 minute read behind the Timer view's "i": where the technique
  came from, how it works, why (procrastination, the vigilance decrement, learning during
  breaks), what the evidence does and doesn't show, the planning fallacy, and variations.
  General-audience, no references to the app.

## How it connects
`app.py` exposes `APP_ICON_PATH`; `__main__.py` sets it as the application's window icon.
`widgets/background.py` loads `background.svg` by path.
`views/timer_view.py` loads `swoosh_snap.wav` by path.
`views/duration_view.py` loads `trefoil_knot.md` and `views/timer_view.py` loads
`pomodoro_technique.md` by path; `widgets/info_article.py` renders them.
`screens/splash.py` loads `splash_intro.wav` by path.
Packaged automatically with `src/tab` by hatchling.

## Conventions
- Prefer SVG for images so they stay sharp at every size and can be edited as text.
- Long-form text lives here as Markdown, not as strings in Python, so it can be edited as prose.
  Stick to what Qt's Markdown renders: headings, paragraphs, bold/italic, lists, block quotes.
- Colours from the palette in `styles/theme.qss` (black, bone, tan, the greys) or shades of them.
