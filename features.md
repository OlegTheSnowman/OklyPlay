# OklyPlay — Detailed Features Documentation

OklyPlay is a powerful, screenreader-accessible soundboard application built for live streamers, podcasters, and content creators. It provides advanced mixing, preset customization, automated looping playlists, symmetric crossfades, and full screenreader accessibility.

---

## 1. Multi-Bus Mixing & Playback Modes
OklyPlay uses a multi-bus audio architecture that lets you route sounds through different sub-channels (buses) to control their volumes and playback rules collectively.

- **Playback Modes**:
  - **Layered Mode (SFX)**: Sounds played on a layered bus overlap and play concurrently. Ideal for sound effects, stingers, or overlapping ambient effects.
  - **Exclusive Mode (Music/Ambient)**: Sounds played on an exclusive bus cut off other sounds playing on exclusive channels. Excellent for background music, where only one soundtrack should play at any given time.
- **Volume Controls**:
  - **Master Volume**: Scales the overall application volume (0% to 100%) dynamically.
  - **Per-Bus Volume**: Each bus has its own volume multiplier, allowing you to easily quiet down music while keeping sound effects loud.

---

## 2. Configurable Sound Scenarios
A sound doesn't just play back at a static volume. You can configure multiple preset "scenarios" (variations) for each audio file in your project.

- **Volume Scale**: Scale individual sound playback volume relative to the bus.
- **Speed Adjustment**: Modify playback speed from `0.1x` to `3.0x`. High-quality linear resampling is performed vectorially in real-time, adjusting pitch and duration accordingly.
- **Loop Toggle**: Mark a sound scenario to loop indefinitely when triggered until manually stopped.
- **Fade Ramps**: Configure linear **Fade-in** and **Fade-out** durations (in milliseconds) to avoid harsh audio starts or cuts.
- **Alternate Bus Routing**: Route a sound scenario temporarily to a different bus than its default parent. For example, play a music track routed through the SFX bus for a specific scenario effect.

---

## 3. The Sound Manager (`Alt+S`)
A central command center for importing and organizing project audio files, designed with rapid keyboard navigation and accessibility in mind.

- **Bulk Import**: Select and import dozens of files at once. Newly imported sounds default to an unassigned bus state.
- **Quick Keyboard Assignments**:
  - `Ctrl+1` through `Ctrl+9`: Instantly assign the selected sound to the corresponding bus (e.g. `Ctrl+1` maps to the first bus).
  - `Ctrl+U`: Clears the sound's bus assignment (marks it as unassigned).
  - `F2`: Opens the full Sound Edit dialog.
  - `Delete`: Instantly removes the sound from the project.
  - `Ctrl+I`: Triggers the import file dialog.
- **Clipboard Integration (`Ctrl+V`)**: Copy audio files from Windows Explorer (or utility clipboards) and press `Ctrl+V` inside the manager to instantly paste and import them into the project.

---

## 4. Keybinds & Quick Binding Dialog (`Alt+K`)
OklyPlay supports global and local hotkeys, allowing you to trigger sounds and playlists while playing games or streaming.

- **Sound Hotkeys**: Assign a specific keyboard key combination (e.g., `Ctrl+Alt+F12`) to trigger a sound scenario.
- **Quick Hotkey Binding (`Alt+K`)**: Select any sound in the main list and press `Alt+K` to open a quick keybinder. Press the desired key combination, hit `Tab` and `Enter` to save, and the sound is mapped immediately with conflict checking.
- **Conflict Detection**: The system verifies that a hotkey is not already assigned to another sound or bus, preventing accidental double-triggers.

---

## 5. Bus Hotkeys & Configurable Activation Actions
Buses themselves can be bound to hotkeys. Pressing a bus hotkey triggers automated playback of all sounds on that bus, with four customizable behaviors:

- **Loop (Shuffle)**: Shuffles all sounds on the bus and loops through them continuously. Reshuffles the list when the queue is exhausted. (Default recommendation for exclusive buses like Music).
- **Loop (Sequential)**: Loops through all sounds on the bus continuously in their folder/sequential list order.
- **Single (Shuffle)**: Plays exactly one random sound from the bus and stops. (Default recommendation for layered buses like SFX).
- **Single (Sequential)**: Plays one sound sequentially from the bus on each press and stops (keeping track of the last played index).
- **Dynamic Recommendations**: Switching a bus's Playback Mode between exclusive and layered automatically selects the recommended default action.

---

## 6. Symmetric Crossfade & Track-to-Track Overlaps
Transitioning between audio clips is handled symmetrically to provide clean, professional, stutter-free transitions.

- **Exclusive Bus Crossfading**: When starting playback on an exclusive bus, all active channels on other exclusive buses fade out using a configurable **Crossfade (ms)** setting. Symmetrically, the new sound automatically fades in using the same crossfade duration.
- **Track-to-Track Playlist Crossfading**: For looping bus playlists, tracks can transition smoothly into one another. The cleanup timer monitors playback. When the remaining track duration is less than or equal to the configurable **Track Crossfade (ms)** duration, the current track begins to fade out and the next track starts playing and fading in early, producing a seamless overlap.

---

## 7. Comprehensive Accessibility
Designed from the ground up for blind and visually impaired users:

- **Screen Reader Support**: Native widget structure allows standard keyboard navigation (arrows, tab, enter). Dynamically pipes speech feedback to active readers like NVDA, JAWS, or Windows Narrator.
- **Speech Announcements**: Core actions (e.g. playing sounds, setting hotkeys, adjusting volumes, stopping loops) generate spoken speech feedback.
- **Labeling Controls**: Form inputs, spinners, and list columns are explicitly labeled in the accessibility tree, preventing screen readers from reading unlabeled controls.

---

## 8. Robust Project Management & Packaging
- **Serialization Safety**: Project saves are written atomically to a temporary file before replacing `project.json`, protecting against corruption during app shutdown or system crashes.
- **Missing File Verification**: Loading a project checks for missing audio files, marking them as `[MISSING]` in the list and notifying the user.
- **Zip Import/Export**: Export your entire project (config and sounds folder) as a single compressed `.zip` archive, or import an archive to load it instantly.
- **CI/CD Releases**: Pushing a tag (`v*`) triggers GitHub Actions to run tests, bundle all resources into a single standalone portable `OklyPlay.exe` via PyInstaller, extract changelog sections, and publish a GitHub Release automatically.
