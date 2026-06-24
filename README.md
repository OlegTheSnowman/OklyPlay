# OklyPlay Soundboard

OklyPlay is a screenreader-accessible soundboard designed for streamers and keyboard-only users. It allows you to load, organize, and play sound clips with custom hotkeys, audio buses, and playback scenarios.

Built with **wxPython**, **sounddevice**, **soundfile**, **numpy**, and **accessible_output2** for native screenreader speech support.

---

## Features

- **Fully Accessible**: All interface controls are custom-labeled for screenreaders (NVDA, JAWS, Narrator). Spoken announcements are triggered on navigation and major actions.
- **Multi-Bus Mixer**: Group sounds into separate audio buses.
  - *Layered Mode*: Play multiple sounds at the same time.
  - *Exclusive Mode*: Playing a sound automatically stops any other sound playing on that same bus.
- **Sound Manager (`Alt+S`)**: A dedicated view for managing all project sounds at once.
  - Import multiple audio files in bulk — sounds start unassigned, so you can organise them at your own pace.
  - Press `Ctrl+1`–`Ctrl+9` to instantly move the selected sound to the matching bus.
  - `Ctrl+U` clears a bus assignment; `F2` edits; `Delete` removes.
- **Custom Hotkeys**: Trigger sounds instantly at any time using system-wide hotkeys. Supports key combinations like `Ctrl`, `Shift`, `Alt`, and functional keys (e.g., `F1`–`F12`, `Space`, `Enter`).
  - **Quick Hotkey (`Alt+K`)**: Assign or change a sound's hotkey on the fly without opening the full editor.
- **Bus Loop Playback**: Assign a hotkey to an entire bus to shuffle and loop all its sounds continuously — perfect for background music or ambient playlists.
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
| **Stop Current Bus** | `Escape` |
| **Stop All Sounds** | `Alt + Escape` |
| **Switch Active Bus** | `Ctrl + 1` through `Ctrl + 9` |
| **Adjust Bus Volume** | `Ctrl + Up Arrow` / `Ctrl + Down Arrow` |
| **Adjust Master Volume** | `Ctrl + Shift + Up Arrow` / `Ctrl + Shift + Down Arrow` |
| **Sound Manager** | `Alt + S` |
| **Import Sounds (in Manager)** | `Ctrl + I` |
| **Assign to Bus N (in Manager)** | `Ctrl + 1` through `Ctrl + 9` |
| **Unassign Bus (in Manager)** | `Ctrl + U` |
| **Quick Hotkey** | `Alt + K` |
| **Edit Sound** | `F2` |
| **Project Manager** | `Ctrl + M` |
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
