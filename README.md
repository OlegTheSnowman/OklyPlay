# OklyPlay Soundboard

OklyPlay is a screenreader-accessible soundboard designed for streamers and keyboard-only users. It allows you to load, organize, and play sound clips with custom hotkeys, audio buses, and playback scenarios.

Built with **wxPython**, **sounddevice**, **soundfile**, **numpy**, and **accessible_output2** for native screenreader speech support.

---

## Features

- **Fully Accessible**: All interface controls are custom-labeled for screenreaders (NVDA, JAWS, Narrator). Spoken announcements are triggered on navigation and major actions.
- **Multi-Bus Mixer**: Group sounds into separate audio buses.
  - *Layered Mode*: Play multiple sounds at the same time.
  - *Exclusive Mode*: Playing a sound automatically stops any other sound playing on that same bus.
- **Custom Hotkeys**: Trigger sounds instantly at any time using system-wide hotkeys. Supports key combinations like `Ctrl`, `Shift`, `Alt`, and functional keys (e.g., `F1`-`F12`, `Space`, `Enter`).
- **Scenarios**: Create different playback configurations (overrides) for the same sound. Control:
  - Individual sound volume overrides
  - Linear fade-in and fade-out duration (in milliseconds)
  - Playback speed (resampling multiplier from `0.5x` to `2.0x`)
  - Audio looping
  - Alternative bus routing
- **Output Device Control**: Choose your audio interface and adjust master or individual bus volumes.
- **Portable Projects**: Save, load, and package your projects (along with your audio files) into zip archives to share them.

---

## Keyboard Shortcuts

OklyPlay is designed for rapid keyboard control. Here is a quick reference:

| Action | Shortcut |
|--------|----------|
| **Play Selected Sound** | `Space` |
| **Stop Selected Sound** | `Delete` |
| **Stop Current Bus** | `Ctrl + Shift + S` |
| **Stop All Sounds** | `Escape` |
| **Switch Active Bus** | `Ctrl + 1` through `Ctrl + 9` |
| **Adjust Master Volume** | `Ctrl + Up Arrow` / `Ctrl + Down Arrow` |
| **Adjust Selected Bus Volume** | `Shift + Up Arrow` / `Shift + Down Arrow` |
| **Project Manager** | `Ctrl + P` |
| **Manage Buses** | `Ctrl + B` |
| **Preferences / Device Setup** | `Ctrl + Alt + P` |
| **Help & Shortcuts Dialog** | `Ctrl + H` |

---

## Getting Started

### Using the Portable Version (Windows)
1. Go to the [Releases](https://github.com/OlegTheSnowman/OklyPlay/releases) page.
2. Download `OklyPlay.exe` from the latest release.
3. Run the executable. No installation is required.

### Running from Source
To run OklyPlay from source, you will need Python installed (Python 3.11 recommended).

1. Clone this repository.
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python src/soundboard.py
   ```

---

## Building the Executable

If you want to compile the standalone executable locally:
1. Ensure PyInstaller is installed:
   ```bash
   pip install pyinstaller
   ```
2. Double-click or run `build_portable.bat` in the root folder.
3. The built executable will be located under `dist/OklyPlay.exe`.
