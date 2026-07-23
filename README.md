# OklyPlay

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)
![Build](https://github.com/OlegTheSnowman/OklyPlay/actions/workflows/release.yml/badge.svg)

A soundboard for streamers, built to be fully usable with just a keyboard and a screen reader.

Most soundboards on the market are unusable for blind streamers — custom-drawn buttons and grids with no labels, no keyboard navigation, nothing a screen reader can make sense of. I couldn't find one that worked, so I built one. It's designed around NVDA, JAWS, and Windows Narrator from the ground up, not as an afterthought bolted on later.

Built with **wxPython**, **sounddevice**, **soundfile**, **numpy**, and **accessible_output2**.

---

## What it does

- **Fully accessible** — every control is labeled, every action announces itself. No mystery icons, no unlabeled buttons.
- **Multi-bus mixer** — group your sounds into buses. Layered buses stack sounds on top of each other (good for SFX); exclusive buses cut off whatever else is playing (good for music).
- **Sound Manager (`Alt+S`)** — bulk-import a folder of clips, then sort them onto buses at your own pace with `Ctrl+1`–`Ctrl+9`.
- **Hotkeys everywhere** — bind any sound or any whole bus to a system-wide hotkey, with conflict detection so you don't clobber an existing bind by accident.
- **Bus loop playback** — point a hotkey at a bus and it'll shuffle or sequence through everything on it, looping until you stop it. Handy for background music you don't want to babysit.
- **Scenarios** — save multiple presets per sound (volume, fade in/out, speed, loop, alternate bus) and switch between them instead of re-editing the same clip every time.
- **Crossfading** — exclusive buses crossfade into each other, and looping playlists crossfade track-to-track, so nothing cuts in or out abruptly.
- **Portable projects** — a project is just a folder (config + audio files). Zip it up and hand it to someone else, or move it between machines.

For the full rundown of every feature, see [features.md](features.md).

---

## Keyboard shortcuts

| Action | Shortcut |
|--------|----------|
| Play selected sound | `Space` |
| Stop selected sound | `Delete` |
| Stop current bus | `Escape` |
| Stop all sounds | `Alt + Escape` |
| Switch active bus | `Ctrl + 1` – `Ctrl + 9` |
| Adjust bus volume | `Ctrl + Up` / `Ctrl + Down` |
| Adjust master volume | `Ctrl + Shift + Up` / `Ctrl + Shift + Down` |
| Sound Manager | `Alt + S` |
| Import sounds (in Manager) | `Ctrl + I` |
| Assign to bus N (in Manager) | `Ctrl + 1` – `Ctrl + 9` |
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
2. Run it. That's it — no installer, no setup wizard.

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

The result lands in `dist/OklyPlay.exe`. Every tagged release (`v*`) also builds and publishes automatically via GitHub Actions.

---

## How it's put together

```
src/soundboard.py          entry point — creates the wx.App and main window
src/ui_main.py              main window: bus list, sound list, menu, status bar
src/ui_dialogs.py           every modal dialog (projects, prefs, sound/bus editing)
src/audio_engine.py         the mixer itself — buses, channels, fades, device output
src/project_manager.py      load/save/import/export of project files
src/accessible_speech.py    thin wrapper for screen reader announcements
```

A project is just a folder: `project.json` for all the config, plus a `sounds/` directory holding the actual audio files. That's the whole portability story — zip the folder, send it, done.

---

## Running the tests

```bash
pip install pytest
python -m pytest
```

---

## License

MIT — see [LICENSE](LICENSE).

If you hit a bug, open an issue. If you're blind or low-vision and something in here doesn't work well with your screen reader, that's a bug too — please tell me.
