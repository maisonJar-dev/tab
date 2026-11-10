# tests

## Purpose
pytest suite for the pure logic in `src/tab/core/`.

## Contents
- `test_timer.py`: Pomodoro state machine, today's counters across midnight, ratings, the all-time
  reset (and that it keeps the break cycle), the duration session (focus, finish, kept separate
  by default, or linked: one clock in work phases, resting in breaks, completing as one session
  from either side; toggling it pauses both), completing a work session early, both Resets (alone or linked), skipping a rating, clock formatting, and how a phase splits into dial laps. Uses a fake clock and a fake date, so no real waiting.
- `test_config.py`: settings validation and JSON save/load (older files gain new settings at their
  defaults), using pytest's `tmp_path`.
- `test_progress.py`: timer progress save/load, including that atomic writes leave no temp file.
- `test_stopwatch.py`: start/pause accumulation and reset-then-continue (used to skip the splash intro).
- `test_knot_animation.py`: the Duration knot: the solid tube has no gaps and everything fits the
  drawing area at every orientation, running dots vary in size, rotations are right-handed and
  flow loops, pausing solidifies and freezes the dots, and the paused fidget physics: drags turn
  the front the way the pointer moves, flicks coast to a stop, holding still or grabbing stops
  it, and starting the timer cancels a coast.
- `test_cube_to_word_animation.py`: the splash timeline: starts above the window, lands on the ground,
  no jump when the cube breaks apart, ends exactly on the word.

## How it connects
Imports the installed `tab` package (`pip install -e ".[dev]"`). Run with `pytest`.

## Conventions
- Test `core/` directly; UI tests aren't worth it until the UI stabilises.
- Inject time through `monotonic_clock_seconds` (and the day through `local_date`) instead of sleeping; animations take time as an argument.
- Compare geometry with on-screen tolerances, and treat line segments as undirected and unordered.
- Write the failing test first. Check a new test can fail by breaking the code on purpose (mutation check).
