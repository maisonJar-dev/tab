# tab
My personal tracker and study helper: a Pomodoro timer desktop app built with Python and PySide6.

## Install as an app

Requires Python 3.11+. [pipx](https://pipx.pypa.io) installs `tab` into its own environment and
puts the `tab` command on your PATH. It installs a snapshot: after pulling changes, update with
`pipx install --force .` from the repo.

**All platforms**

```sh
python3.11 -m pip install --user pipx    # Windows: py -3.11 -m pip install --user pipx
python3.11 -m pipx ensurepath            # once; then open a new terminal
pipx install --python python3.11 .       # from the repo root
tab
```

**Linux (GNOME, KDE, ...): app grid and dock icon**

```sh
mkdir -p ~/.local/share/icons/hicolor/scalable/apps ~/.local/share/applications
cp src/tab/assets/tab_icon.svg ~/.local/share/icons/hicolor/scalable/apps/tab.svg
cat > ~/.local/share/applications/tab.desktop <<EOF
[Desktop Entry]
Type=Application
Name=Tab
Comment=Pomodoro timer and study helper
Exec=$HOME/.local/bin/tab
Icon=tab
Terminal=false
Categories=Utility;
StartupWMClass=tab
EOF
```

`StartupWMClass=tab` matches the app id set in `__main__.py`, so the running window groups under
this icon.

**Windows:** `tab` is a GUI script, so it opens without a console window. For the Start menu,
create a shortcut to `%USERPROFILE%\.local\bin\tab.exe` in
`%APPDATA%\Microsoft\Windows\Start Menu\Programs`.

**macOS:** run `tab` from a terminal. A Dock/Launchpad app needs a `.app` bundle, which this
project doesn't build yet.

Press **Space** or **Enter** on the splash screen to reach the main window.

## Develop

```sh
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"   # editable: runs your working copy, unlike the pipx install
pytest             # run tests
ruff check .       # lint
ruff format .      # format
git config core.hooksPath .githooks   # once per clone: enables the README-per-directory check
```

Architecture overview: [`src/README.md`](src/README.md). Agent and contributor rules: [`CLAUDE.md`](CLAUDE.md).
