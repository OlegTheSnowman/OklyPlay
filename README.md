# OklyPlay

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)
![Tests](https://github.com/OlegTheSnowman/OklyPlay/actions/workflows/tests.yml/badge.svg)

OklyPlay is a soundboard for streamers that you can run entirely from the keyboard with a screen reader.

I'm blind, and every soundboard I tried was a wall of custom-drawn buttons with no labels and no keyboard path through them. NVDA had nothing to read. So I wrote my own. It uses native Windows controls, so NVDA, JAWS and Narrator see a normal app, and it speaks the things you would otherwise have to look for: which bus you switched to, the new volume, the next track in a playlist.

It also has to look decent to the sighted people watching the stream, so there is a header with the project name, a colour per bus, and a speaker icon next to whatever is playing.

## How it works

Sounds live on buses, which are just groups with their own volume. A layered bus lets sounds stack, which is what you want for effects. An exclusive bus fades out whatever was playing when a new sound starts, which suits music. Exclusive buses crossfade into each other, and a bus can duck the others while it plays, so music drops under an alert and comes back up after.

To get sounds in, open the Sound Manager with Alt+S, import a whole folder (or paste files you copied in Explorer), and sort them onto buses with Ctrl+1 to Ctrl+9.

Any sound can have its own hotkey, and so can a bus. A bus hotkey plays one random or next sound, or starts a playlist that shuffles or loops through the whole bus until you stop it. I use that for background music. OklyPlay refuses a hotkey that is already taken by another sound, another bus, or one of its own shortcuts. Hotkeys work while the OklyPlay window has focus; they are not global.

Each sound can also keep a few presets, called scenarios: different volume, fades, speed, pitch, looping, or another bus. Alt+1 to Alt+9 plays the selected sound with scenario 1 to 9.

A project is a folder with a `project.json` and a `sounds` folder. You can export it as a zip, move it to another computer, and import it there.

Every message the app shows opens with its text in a read-only field that has focus, so you can read it line by line or copy it, then Tab to the buttons. Help > Check for Updates looks for a new release on GitHub, and the exe can update itself.

[features.md](features.md) describes every feature in detail.

## Keyboard shortcuts

| Action | Shortcut |
|--------|----------|
| Play the selected sound | Space or Enter |
| Play it with scenario 1 to 9 | Alt+1 to Alt+9 |
| Stop the current bus | Escape |
| Stop everything | Alt+Escape |
| Switch to bus 1 to 9 | Ctrl+1 to Ctrl+9 |
| Bus volume up or down | Ctrl+Up, Ctrl+Down |
| Master volume up or down | Ctrl+Shift+Up, Ctrl+Shift+Down |
| Add a sound | Ctrl+I |
| Edit the selected sound | F2 |
| Remove the selected sound | Delete |
| Set its hotkey | Alt+K |
| Edit its scenarios | Ctrl+E |
| Sound Manager | Alt+S |
| Manage buses | Ctrl+B |
| New, open, save project | Ctrl+N, Ctrl+O, Ctrl+S |
| Project Manager | Ctrl+M |

Inside the Sound Manager, Ctrl+1 to Ctrl+9 moves the selected sound to that bus, Ctrl+U takes it off its bus, Ctrl+I imports files, and Ctrl+V pastes files copied in Explorer. Preferences, where you pick the output device, is in the File menu.

## Getting it

Download `OklyPlay.exe` from [Releases](https://github.com/OlegTheSnowman/OklyPlay/releases) and run it. There is no installer. Newer versions can be installed from inside the app with Help > Check for Updates.

To run it from source you need Python 3.11 or newer:

```bash
git clone https://github.com/OlegTheSnowman/OklyPlay.git
cd OklyPlay
pip install -r requirements.txt
python src/soundboard.py
```

To build the exe yourself, run `build_portable.bat`. It installs PyInstaller and writes `dist/OklyPlay.exe`. Releases are built this way and uploaded with `gh release create`.

## Code layout

```
src/soundboard.py          entry point
src/ui_main.py             main window: buses, sounds, menus, status bar, updates
src/ui_dialogs.py          the dialogs and the message box
src/branding.py            colours, logo and list icons, all drawn in code
src/audio_engine.py        the mixer: channels, fades, crossfades, ducking, pitch
src/project_manager.py     loading, saving, importing and exporting projects
src/updater.py             checks GitHub releases and swaps in the new exe
src/accessible_speech.py   speaks through the running screen reader
tools/make_icon.py         writes assets/oklyplay.ico from the logo drawing
```

## Tests

```bash
pip install pytest
python -m pytest
```

The tests in `tests/test_soundboard.py` cover the audio engine (resampling, speed, pitch, fades, crossfades, ducking), projects (saving, loading, import and export, including bad zips), hotkey rules, playlists, the updater and the dialogs. One group checks that every dialog control has an accessible name, so a control that loses its label fails the build. They run on GitHub for every push and pull request to `master`.

The tests open real windows. On my own machine I run them on a separate hidden Windows desktop so they don't pop up while I work.

## License

MIT, see [LICENSE](LICENSE).

If something breaks, open an issue. If you use a screen reader and something in OklyPlay is hard to reach or read, that is a bug too, so please tell me.
