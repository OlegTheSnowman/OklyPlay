# Changelog

All notable changes to OklyPlay are documented here.  
This project follows [Semantic Versioning](https://semver.org/).

---

## [1.1.0] - 2026-06-24

### Added

- **Sound Manager (`Alt+S`)** - A dedicated dialog to manage all project sounds in one place.
  - Import multiple audio files at once (no bus assignment required on import).
  - Sounds appear in a list showing Name, Bus, Hotkey, and File columns.
  - `Ctrl+1` through `Ctrl+9` instantly assigns the selected sound to the corresponding bus.
  - `Ctrl+U` clears a sound's bus assignment (marks it as unassigned).
  - `F2` opens the full Edit Sound dialog for the selected sound.
  - `Delete` removes the selected sound from the project.
  - `Ctrl+I` opens an additional import picker from inside the manager.
- **Bus Hotkeys & Configurable Actions** - Assign hotkeys to buses with configurable activation behaviors:
  - **Loop (Shuffle)**: Shuffles and loops through all sounds on the bus continuously.
  - **Loop (Sequential)**: Plays through all sounds on the bus in sequential order and loops continuously.
  - **Single (Shuffle)**: Plays exactly one random sound from the bus and stops.
  - **Single (Sequential)**: Plays one sound sequentially from the bus on each press and stops.
  - Recommended defaults auto-populated depending on Playback Mode (exclusive defaults to Loop Shuffle; layered defaults to Single Shuffle).
- **Quick Sound Hotkey (`Alt+K`)** - Press `Alt+K` while a sound is selected to assign or change its hotkey without opening the full Edit dialog.
- **Exclusive Bus Crossfading & Editor** - Automatically crossfade between exclusive buses.
  - Playing a sound on an exclusive bus now fades out all channels on other exclusive buses using a configurable crossfade duration.
  - The new sound now fades in using the target bus's crossfade duration as its default fade-in.
  - Layered buses remain unaffected and continue playing on top.
  - A **Crossfade (ms)** field has been added to the bus editor (`AddEditBusDialog`) and the bus management list (`ManageBusesDialog`).
- **Track-to-Track Crossfading** - Looping bus playlists can now crossfade between tracks symmetrically.
  - Plays the next track early (at crossfade remaining duration) and fades out the current track while fading in the new track.
  - A **Track Crossfade (ms)** field has been added to the bus editor (`AddEditBusDialog`) and the bus management list (`ManageBusesDialog`).

### Changed

- `Ctrl+I` (formerly Add Sound) now also works from within the Sound Manager.
- Project is automatically saved after the Sound Manager dialog closes.

---

## [1.0.0] - 2026-06-01

### Added

- Initial release.
- Multi-bus mixer with Layered and Exclusive playback modes.
- Per-sound custom hotkeys with conflict detection.
- Scenarios: per-sound volume, fade-in/out, playback speed, loop, and alternate bus routing.
- Project management: create, save, load, export/import as zip archives.
- Output device selection and master/bus volume controls.
- Full screenreader accessibility via accessible_output2 (NVDA, JAWS, Narrator).
- Automated portable executable build via GitHub Actions.
