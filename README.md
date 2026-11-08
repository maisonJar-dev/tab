# tab
My personal tracker and study helper: a Pomodoro timer desktop app built with Python and PySide6.

## Install and run

Requires Python 3.11+.

```sh
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
tab
```

Press **Enter** on the splash screen to reach the main window.

## Develop

```sh
pytest             # run tests
ruff check .       # lint
ruff format .      # format
git config core.hooksPath .githooks   # once per clone: enables the README-per-directory check
```

Architecture overview: [`src/README.md`](src/README.md). Agent and contributor rules: [`CLAUDE.md`](CLAUDE.md).
