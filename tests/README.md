# tests

## Purpose
pytest suite for the pure logic in `src/tab/core/`.

## Contents
- `test_timer.py`: Pomodoro state machine. Uses a fake clock, so no real waiting.
- `test_config.py`: settings validation and JSON save/load, using pytest's `tmp_path`.
- `test_progress.py`: timer progress save/load, including that atomic writes leave no temp file.
- `test_stopwatch.py`: start/pause accumulation and reset-then-continue (used to skip the splash intro).
- `test_cube_to_word_animation.py`: the splash timeline: starts above the window, lands on the ground,
  no jump when the cube breaks apart, ends exactly on the word.

## How it connects
Imports the installed `tab` package (`pip install -e ".[dev]"`). Run with `pytest`.

## Conventions
- Test `core/` directly; UI tests aren't worth it until the UI stabilises.
- Inject time through `monotonic_clock_seconds` instead of sleeping; animations take time as an argument.
- Compare geometry with on-screen tolerances, and treat line segments as undirected and unordered.
- Write the failing test first. Check a new test can fail by breaking the code on purpose (mutation check).
