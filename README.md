# OklyPlay

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)
![Build](https://github.com/OlegTheSnowman/OklyPlay/actions/workflows/release.yml/badge.svg)

A soundboard for streamers, built to be fully usable with just a keyboard and a screen reader.

Most soundboards on the market are unusable if you're blind. Custom-drawn buttons and grids, no labels, no real keyboard navigation, nothing a screen reader can make sense of. I couldn't find one that worked, so I built one. NVDA, JAWS, and Windows Narrator support was the starting point here, not something bolted on afterward.

Built with wxPython, sounddevice, soundfile, numpy, and accessible_output2.

---

## What it does

Every control is labeled and every action announces itself, so there are no mystery icons or unlabeled buttons to hunt for.

Sounds live on buses, which is really just a fancy word for groups. A layered bus stacks sounds on top of each other, which suits sound effects. An exclusive bus cuts off whatever else is playing on it, which suits music. Mix and match however you like.

The Sound Manager (`Alt+S`) is where you bulk-import a folder of clips and then sort them onto buses at your own pace, using `Ctrl+1` through `Ctrl+9`.

You can bind any sound, or a whole bus, to a system-wide hotkey. Conflict detection stops you from accidentally clobbering an existing bind. Point a hotkey at a bus and it will shuffle or sequence through everything on it, looping until you tell it to stop, which is handy for background music you don't want to babysit.

Each sound can have several saved presets, called scenarios: volume, fade in and out, speed, loop, an alternate bus. Switch between them instead of re-editing the same clip every time you want it to sound slightly different.

Exclusive buses crossfade into each other, and looping playlists crossfade track to track, so nothing cuts in or out abruptly.

A project is just a folder, config plus audio files, so you can zip it up and hand it to someone else or move it between machines without anything breaking.

For the full rundown of every feature, see [features.md](features.md).

---

## Keyboard shortcuts

| Action | Shortcut |
|--------|----------|
| Play selected sound | `Space` |
| Stop selected sound | `Delete` |
| Stop current bus | `Escape` |
| Stop all sounds | `Alt + Escape` |
| Switch active bus | `Ctrl + 1` through `Ctrl + 9` |
| Adjust bus volume | `Ctrl + Up` / `Ctrl + Down` |
| Adjust master volume | `Ctrl + Shift + Up` / `Ctrl + Shift + Down` |
| Sound Manager | `Alt + S` |
| Import sounds (in Manager) | `Ctrl + I` |
| Assign to bus N (in Manager) | `Ctrl + 1` through `Ctrl + 9` |
| Unassign bus (in Manager) | `Ctrl + U` |
| Quick hotkey assign | `Alt + K` |
| Edit sound | `F2` |
| Project Manager | `Ctrl + M` |
| Manage buses | `Ctrl + B` |
| Preferences / device setup | `Ctrl + Alt + P` |
| Help & shortcuts dialog | `Ctrl + H` |

---

## Getting started

### Portable build (Windows, no install)

1. Grab the latest `OklyPlay.exe` from [Releases](https://github.com/OlegTheSnowman/OklyPlay/releases).
2. Run it. No installer, no setup wizard.

### Running from source

Needs Python 3.11+.

```bash
git clone https://github.com/OlegTheSnowman/OklyPlay.git
cd OklyPlay
pip install -r requirements.txt
python src/soundboard.py
```

### Building the executable yourself

```bash
pip install pyinstaller
build_portable.bat
```

The result lands in `dist/OklyPlay.exe`. Every tagged release (`v*`) also builds and publishes automatically through GitHub Actions.

---

## How it's put together

```
src/soundboard.py          entry point, creates the wx.App and main window
src/ui_main.py              main window: bus list, sound list, menu, status bar
src/ui_dialogs.py           every modal dialog (projects, prefs, sound/bus editing)
src/audio_engine.py         the mixer itself: buses, channels, fades, device output
src/project_manager.py      load/save/import/export of project files
src/accessible_speech.py    thin wrapper for screen reader announcements
```

A project is just a folder: `project.json` for all the config, plus a `sounds/` directory holding the actual audio files. That's the whole portability story. Zip the folder, send it, done.

---

## Running the tests

```bash
pip install pytest
python -m pytest
```

---

## License

MIT, see [LICENSE](LICENSE).

If you hit a bug, open an issue. If you're blind or low-vision and something in here doesn't play nice with your screen reader, that counts as a bug too, so tell me.
