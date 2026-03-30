# Auto Typer

A fullscreen-style auto-typing tool with realistic typo simulation and presets.

## Features

- Global F6 hotkey trigger (rebindable from UI)
- Typing speed (WPM), typo chance, correction delay, startup delay controls
- Enhanced typo engine with:
  - Neighbor key typos
  - Double character typos
  - Missed space typos with correction
  - Wrong capitalization typos
  - Transposed character typos
- Typing profiles:
  - Hunt & Peck
  - Casual
  - Fast Typist
  - Programmer
- Save/load/delete presets in `presets/` JSON files
- Real-time progress bar
- Paste from clipboard button
- Minimize-to-system-tray with pystray menu: Show / Start / Stop / Quit
- Light/dark theme toggle with persisted `config.json`

## Install

```bash
pip install -r requirements.txt
```

## Usage

1. Run in command line:
   `python auto_typer.py`
2. Enter or paste text
3. Adjust sliders and profile
4. Press Start or global hotkey (default F6)
5. Switch to target window before typing begins
6. Stop via GUI button or hotkey

## Build

```bash
pip install pyinstaller
pyinstaller --onefile --noconsole auto_typer.py
```

## Notes

- Run the app as administrator if global keyboard hooks require privilege.
- Presets are stored in `presets/` and theme/hotkey in `config.json`.

![Screenshot](screenshot-placeholder.png)
