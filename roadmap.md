# OklyPlay — Roadmap & Technical Specification

A screenreader-accessible soundboard for streamers, built with **wxPython**, **sounddevice/soundfile/numpy**, and **accessible_output2**.

---

## 1. Architecture Overview

```
soundboard.py          <- Entry point: creates wx.App, loads config, launches MainFrame
├── ui_main.py         <- MainFrame: split panel (buses list | sounds list), menu bar, status bar
├── ui_dialogs.py      <- All modal dialogs (new project, preferences, add/edit sound, manage buses, edit scenarios)
├── audio_engine.py    <- Custom software mixer: buses, channels, fade, device selection
├── project_manager.py <- Load/save/import/export projects (JSON + sounds/ folder)
└── accessible_speech.py <- Wrapper around accessible_output2 for spoken announcements
```

### Dependencies (all already installed)
- `wxPython` 4.2.5
- `sounddevice` 0.5.5
- `soundfile` 0.14.0
- `numpy` 2.4.6
- `accessible_output2` 0.17

### Python Version
- Python 3.14.3 (Windows x64)

IMPORTANT: `pygame` does NOT work on Python 3.14 due to `distutils.msvccompiler` removal. We use `sounddevice` + `soundfile` + `numpy` instead.

---

## 2. Core Concepts

### 2.1 Projects
A project is a self-contained directory:
```
MyProject/
├── project.json      <- All metadata (buses, sounds, scenarios, hotkeys)
└── sounds/           <- Imported audio files (copied here on import)
    ├── airhorn.mp3
    ├── rain.ogg
    └── intro_music.wav
```

When a user imports a sound, the file is **copied** into the `sounds/` folder. This ensures portability — the entire project directory can be zipped and shared.

### 2.2 Buses
Buses are user-created audio groups. Each bus has:
- **name**: Display name (e.g., "Music", "SFX", "Ambient")
- **mode**: `"exclusive"` (one sound at a time; new sound stops old) or `"layered"` (unlimited polyphony)
- **volume**: Float 0.0–1.0 (bus-level volume multiplier)

Every project starts with two default buses: "Music" (exclusive) and "SFX" (layered). The user can add/remove/rename buses freely.

### 2.3 Sounds
A sound entry belongs to **one bus** and has:
- **id**: UUID string
- **name**: Display name
- **filename**: Relative path inside `sounds/` folder
- **bus_id**: Which bus this sound is assigned to
- **hotkey**: Optional hotkey string (e.g., `"F5"`) — triggers default scenario
- **default_scenario**: The scenario settings used when no specific scenario is selected
- **scenarios**: List of named scenario presets (see below)

### 2.4 Scenarios
A scenario is a named preset attached to a sound that overrides playback settings:
- **name**: Display name (e.g., "Quick burst", "Slow fade in")
- **volume**: Float 0.0–1.0 (overrides sound's default volume)
- **fade_in_ms**: Milliseconds for linear fade-in (0 = instant)
- **fade_out_ms**: Milliseconds for linear fade-out (0 = instant)
- **speed**: Float playback speed multiplier (1.0 = normal, 0.5 = half speed, 2.0 = double). Achieved by resampling.
- **loop**: Boolean — whether the sound loops
- **bus_id**: Optional — override the sound's default bus assignment

Each sound always has at least one scenario (its default). The user can add more and trigger them via `Alt+1..9`.

---

## 3. Data Schema — `project.json`

```json
{
  "name": "My Stream Sounds",
  "version": 1,
  "master_volume": 0.8,
  "output_device": null,
  "buses": [
    {
      "id": "bus-uuid-1",
      "name": "Music",
      "mode": "exclusive",
      "volume": 0.7
    },
    {
      "id": "bus-uuid-2",
      "name": "SFX",
      "mode": "layered",
      "volume": 1.0
    }
  ],
  "sounds": [
    {
      "id": "sound-uuid-1",
      "name": "Air Horn",
      "filename": "airhorn.mp3",
      "bus_id": "bus-uuid-2",
      "hotkey": "F5",
      "default_scenario": {
        "volume": 1.0,
        "fade_in_ms": 0,
        "fade_out_ms": 0,
        "speed": 1.0,
        "loop": false
      },
      "scenarios": [
        {
          "name": "Slow fade in",
          "volume": 0.6,
          "fade_in_ms": 2000,
          "fade_out_ms": 500,
          "speed": 1.0,
          "loop": false,
          "bus_id": null
        }
      ]
    }
  ]
}
```

---

## 4. Audio Engine Design (`audio_engine.py`)

### 4.1 Overview
A custom real-time software mixer using `sounddevice.OutputStream` with a numpy callback.

### 4.2 Key Classes

#### `AudioEngine`
Top-level manager. Responsibilities:
- Enumerate output devices via `sounddevice.query_devices()`
- Open/close `sounddevice.OutputStream` for the selected device
- Maintain a list of `Channel` objects (active playback instances)
- Mix all active channels in the stream callback
- Provide `play()`, `stop()`, `stop_bus()`, `stop_all()`, `set_master_volume()`, `set_bus_volume()` methods

#### `LoadedSound`
Represents a preloaded audio file in memory:
- On load: read the file with `soundfile.read()`, convert to float32, resample to the output sample rate using numpy interpolation, convert mono to stereo (duplicate channel)
- Store as a numpy array of shape `(num_samples, 2)` — always stereo float32
- Cache these in a dict keyed by filename to avoid reloading

#### `Channel`
Represents one active playback instance:
- References a `LoadedSound`
- Tracks: current playback position (sample index), volume, fade state, loop flag, bus_id, speed
- The `render(num_frames)` method returns a numpy array of the next N frames, applying volume and fade ramps
- When a channel finishes (position >= length and not looping), it marks itself as done

### 4.3 Stream Callback (Critical Path)
```python
def _callback(self, outdata, frames, time_info, status):
    """Called by sounddevice in a separate thread. Must be fast — no allocations, no I/O."""
    outdata[:] = 0  # silence
    dead_channels = []
    for channel in self._active_channels:
        rendered = channel.render(frames)  # returns (frames, 2) float32
        bus_vol = self._bus_volumes.get(channel.bus_id, 1.0)
        outdata[:len(rendered)] += rendered * bus_vol * self._master_volume
        if channel.is_done:
            dead_channels.append(channel)
    for ch in dead_channels:
        self._active_channels.remove(ch)
    numpy.clip(outdata, -1.0, 1.0, out=outdata)  # prevent clipping
```

### 4.4 Thread Safety
- The callback runs in a C-level audio thread. We must not use Python locks in the callback.
- Use a **copy-on-write** pattern: `self._active_channels` is a list that is only mutated from the main thread by replacing the list reference atomically (Python's GIL makes reference assignment atomic).
- `play()` creates a new list = old list + new channel, then replaces `self._active_channels`.
- `stop()` creates a new list = old list minus the target channel.

### 4.5 Fade & Crossfade Implementation (DETAILED)

Fades are the most critical audio feature to get right. All fade logic lives inside `Channel.render()` — the mixer callback just sums channels and doesn't know about fades.

#### Channel State Machine

Each `Channel` tracks its fade state with these fields:

```python
class Channel:
    def __init__(self, sound, volume, fade_in_ms, fade_out_ms, loop, bus_id, sample_rate):
        self.sound = sound              # LoadedSound (numpy array)
        self.position = 0               # Current read position (sample index)
        self.target_volume = volume     # The volume we're fading TO (0.0–1.0)
        self.loop = loop
        self.bus_id = bus_id
        self.is_done = False

        # Fade-in state
        self._fade_in_samples = int(fade_in_ms * sample_rate / 1000)
        self._samples_played = 0        # Total samples rendered so far

        # Fade-out state
        self._fading_out = False
        self._fade_out_samples = int(fade_out_ms * sample_rate / 1000)
        self._fade_out_elapsed = 0      # Samples since fade-out started
        self._fade_out_start_vol = 0.0  # Volume at the moment fade-out was triggered
```

#### Fade-In (on play)

When a channel starts, if `fade_in_ms > 0`:
- Volume begins at **0.0** and linearly ramps to `target_volume` over `fade_in_samples` samples.
- The ramp factor at sample `s` is: `min(1.0, s / fade_in_samples)`
- After `fade_in_samples` samples, the channel plays at `target_volume` normally.

#### Fade-Out (on stop)

When `channel.start_fade_out(fade_out_ms=None)` is called:
- If `fade_out_ms` is provided, override the channel's default. Otherwise use `self._fade_out_samples`.
- Capture the current effective volume as `_fade_out_start_vol` (accounting for where we are in any active fade-in).
- Set `_fading_out = True`, reset `_fade_out_elapsed = 0`.
- The ramp factor at elapsed sample `e` is: `max(0.0, 1.0 - e / fade_out_samples)`
- Multiply by `_fade_out_start_vol` to get the actual volume.
- When the ramp reaches 0.0 (elapsed >= fade_out_samples), set `is_done = True`.
- If `fade_out_samples == 0`, set `is_done = True` immediately (instant stop).

#### Per-Sample Envelope in `render()`

```python
def render(self, num_frames):
    """Return (N, 2) float32 array of mixed audio. N <= num_frames."""
    # Determine how many samples we can read
    remaining = len(self.sound.data) - self.position
    if remaining <= 0:
        if self.loop:
            self.position = 0
            remaining = len(self.sound.data)
        else:
            self.is_done = True
            return numpy.zeros((num_frames, 2), dtype=numpy.float32)

    n = min(num_frames, remaining)
    chunk = self.sound.data[self.position : self.position + n]  # (n, 2) view

    # --- Build per-sample volume envelope ---
    envelope = numpy.ones(n, dtype=numpy.float32)

    # 1) Fade-in ramp (if still in fade-in phase)
    if self._fade_in_samples > 0 and self._samples_played < self._fade_in_samples:
        sample_indices = numpy.arange(
            self._samples_played,
            self._samples_played + n,
            dtype=numpy.float32
        )
        in_fade = sample_indices < self._fade_in_samples
        envelope[in_fade] = sample_indices[in_fade] / self._fade_in_samples
        # Samples past fade_in_samples stay at 1.0 (already set)

    # 2) Apply target volume
    envelope *= self.target_volume

    # 3) Fade-out ramp (overrides / multiplies on top)
    if self._fading_out:
        if self._fade_out_samples > 0:
            fo_indices = numpy.arange(
                self._fade_out_elapsed,
                self._fade_out_elapsed + n,
                dtype=numpy.float32
            )
            active = fo_indices < self._fade_out_samples
            # Scale envelope by fade-out curve, relative to _fade_out_start_vol
            fade_curve = numpy.zeros(n, dtype=numpy.float32)
            fade_curve[active] = (1.0 - fo_indices[active] / self._fade_out_samples)
            # Replace envelope with: fade_out_start_vol * fade_curve
            # (this replaces the target_volume portion too)
            envelope = self._fade_out_start_vol * fade_curve
            self._fade_out_elapsed += n
            if self._fade_out_elapsed >= self._fade_out_samples:
                self.is_done = True
        else:
            # Instant stop
            self.is_done = True
            return numpy.zeros((num_frames, 2), dtype=numpy.float32)

    # --- Apply envelope to audio data ---
    # envelope is (n,), chunk is (n, 2) → broadcast multiply
    result = numpy.zeros((num_frames, 2), dtype=numpy.float32)
    result[:n] = chunk * envelope[:, numpy.newaxis]

    # Advance position
    self.position += n
    self._samples_played += n

    # Handle loop wrap
    if self.position >= len(self.sound.data) and self.loop and not self._fading_out:
        self.position = 0

    return result
```

#### Crossfade (Exclusive Bus Behavior)

Crossfade is NOT a separate feature — it emerges naturally from the exclusive bus logic:

When `AudioEngine.play(sound, scenario)` is called and the target bus is **exclusive**:

1. **Find all active channels on that bus.**
2. **For each existing channel**: call `channel.start_fade_out(crossfade_ms)` where `crossfade_ms` comes from the **new** sound's scenario `fade_in_ms` (so the old sound fades out over the same duration as the new sound fades in).
3. **Create the new channel** with `fade_in_ms` from the scenario.
4. **Both channels coexist** in `_active_channels` during the crossfade period. The mixer callback sums them — the old one's volume is ramping down while the new one's volume is ramping up.
5. When the old channel's fade-out completes, it sets `is_done = True` and gets cleaned up.

```python
def play(self, sound_id, scenario, buses_config):
    """Play a sound with the given scenario settings."""
    sound = self._loaded_sounds[sound_id]
    bus_id = scenario.get('bus_id') or self._get_sound_bus(sound_id)
    bus_config = buses_config[bus_id]

    fade_in_ms = scenario.get('fade_in_ms', 0)
    fade_out_ms = scenario.get('fade_out_ms', 0)

    # Handle exclusive bus: crossfade out existing channels
    if bus_config['mode'] == 'exclusive':
        current_channels = self._active_channels  # snapshot (COW)
        for ch in current_channels:
            if ch.bus_id == bus_id and not ch._fading_out:
                # Use the NEW sound's fade_in as the crossfade duration
                ch.start_fade_out(fade_in_ms)

    # Create new channel
    new_channel = Channel(
        sound=sound,
        volume=scenario.get('volume', 1.0),
        fade_in_ms=fade_in_ms,
        fade_out_ms=fade_out_ms,
        loop=scenario.get('loop', False),
        bus_id=bus_id,
        sample_rate=self._sample_rate,
    )

    # Copy-on-write: replace the list atomically
    self._active_channels = list(self._active_channels) + [new_channel]
```

#### Crossfade Timing Diagram

```
Time ──────────────────────────────────────────►

Old channel:  ████████████▓▓▓▓░░░░  (fading out)
                          ↑ fade_out starts here
New channel:              ░░▓▓████████████████  (fading in)
                          ↑ new channel starts here

Volume:
Old:  1.0 ─────────────── ╲
                            ╲
                              ╲──── 0.0
New:                    0.0 ──╱
                             ╱
                  1.0 ──────╱

               ◄──────────►
               crossfade region
               (duration = new sound's fade_in_ms)
```

#### Edge Cases
- **Crossfade with `fade_in_ms = 0`**: Old sound stops instantly (fade_out of 0ms), new sound starts at full volume. No overlap.
- **Manual stop during fade-in**: If `start_fade_out()` is called while a channel is still fading in, capture the current interpolated volume as `_fade_out_start_vol` so the fade-out starts from wherever the fade-in got to — no volume jump.
- **Stop all on bus**: `stop_bus(bus_id)` calls `start_fade_out()` on every channel in that bus.
- **Stop all globally**: `stop_all()` calls `start_fade_out()` on every channel across all buses.
- **Layered bus**: No crossfade logic. New sounds just start alongside existing ones. `stop()` on a specific channel still fades it out normally.

### 4.6 Speed/Pitch Change
- Achieved by resampling the `LoadedSound` data at load time or on-the-fly.
- For v1: resample on scenario trigger (pre-compute a speed-adjusted copy using `numpy.interp`). Speed > 1.0 shortens the array, speed < 1.0 lengthens it.

### 4.7 Device Selection
```python
def get_output_devices(self):
    """Return list of (device_index, device_name) for output devices."""
    devices = sounddevice.query_devices()
    return [(i, d['name']) for i, d in enumerate(devices) if d['max_output_channels'] > 0]

def set_output_device(self, device_index):
    """Stop current stream, re-open with new device."""
    self.stop_all()
    self._stream.stop()
    self._stream.close()
    self._device_index = device_index
    self._open_stream()
```

### 4.8 Exclusive Bus Logic
When `play()` is called and the target bus mode is `"exclusive"`:
1. Trigger `start_fade_out(new_fade_in_ms)` on all active channels on that bus (crossfade).
2. Start the new channel with its scenario's `fade_in_ms`.
3. Both old and new channels coexist during the crossfade window; the mixer sums them.
4. Old channel self-removes when its fade-out completes.


---

## 5. Accessible Speech (`accessible_speech.py`)

### 5.1 Design
A singleton wrapper around `accessible_output2.outputs.auto.Auto`.

```python
from accessible_output2.outputs.auto import Auto

class Speech:
    _instance = None

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = Auto()
        return cls._instance

    @classmethod
    def speak(cls, text, interrupt=True):
        """Speak text. If interrupt=True, cancel any previous speech first."""
        cls.get().speak(text, interrupt=interrupt)
```

### 5.2 When to Speak
| Event | Message | Interrupt |
|-------|---------|-----------|
| Sound starts playing | `"Playing {sound_name}"` | Yes |
| Sound stops | `"Stopped {sound_name}"` | Yes |
| Bus switched via Ctrl+N | `"Bus: {bus_name}, {mode}"` | Yes |
| Bus volume changed | `"Volume {percent}%"` | Yes |
| All sounds stopped | `"All sounds stopped"` | Yes |
| Sound added | `"Added {sound_name}"` | Yes |
| Sound removed | `"Removed {sound_name}"` | Yes |
| Scenario triggered | `"Playing {sound_name} — {scenario_name}"` | Yes |
| Project loaded | `"Project loaded: {name}"` | Yes |
| Error (file not found, etc.) | `"Error: {message}"` | Yes |

---

## 6. Project Manager (`project_manager.py`)

### 6.1 Responsibilities
- **create_project(path, name)**: Create directory, `sounds/` subfolder, and initial `project.json` with default buses.
- **load_project(path)**: Read `project.json`, validate schema, return project data dict.
- **save_project(path, data)**: Write project data dict to `project.json` (atomic write: write to `.tmp` then rename).
- **import_sound(project_path, source_file_path)**: Copy the file to `sounds/`, return the relative filename.
- **export_project(project_path, zip_path)**: Zip the entire project directory.
- **import_project(zip_path, target_dir)**: Extract zip to target directory.

### 6.2 UUID Generation
Use `uuid.uuid4()` for generating unique IDs for buses, sounds, etc.

---

## 7. UI Layout (`ui_main.py`)

### 7.1 MainFrame Structure
```
+-----------------------------------------------------------+
| Menu Bar: File | Edit | Buses | Help                      |
+-----------------+-----------------------------------------+
| Buses List      | Sounds List                             |
| (wx.ListBox)    | (wx.ListCtrl, 3 columns)                |
|                 |                                         |
|  > Music <      | Name        | Hotkey | Scenarios        |
|    SFX          |-------------+--------+------------------|
|    Ambient      | Air Horn    | F5     | 2 scenarios      |
|                 | Sad Trombone| F6     | 1 scenario       |
|                 | Rain        |        | 3 scenarios      |
+-----------------+-----------------------------------------+
| Status Bar: Bus: Music (exclusive) | Vol: 70% | playing 2 |
+-----------------------------------------------------------+
```

### 7.2 wxPython Control Choices
| Element | Widget | Accessibility Notes |
|---------|--------|-------------------|
| Buses list | `wx.ListBox` | Screen reader reads item names. Label: "Buses" |
| Sounds list | `wx.ListCtrl` (report mode) | Screen reader reads all columns per row. Label: "Sounds" |
| Status bar | `wx.StatusBar` | Updated programmatically, also spoken via `Speech.speak()` |
| Menu bar | `wx.MenuBar` | Natively accessible, standard Alt+key navigation |

### 7.3 Accessibility Requirements
- **Every control must have a label or accessible name** set via `SetLabel()` or `SetName()`.
- **Focus must be managed explicitly**: when switching buses, focus should move to the sounds list automatically.
- **All non-focus events** (sound playing, volume change) must be spoken via `accessible_speech.py`.
- **No mouse-only actions**: every feature must be reachable via keyboard.

---

## 8. Keyboard Shortcuts

### Navigation
| Shortcut | Action |
|----------|--------|
| `Tab` / `Shift+Tab` | Move focus between Buses list and Sounds list |
| `Arrow Up/Down` | Navigate items in the focused list |
| `Ctrl+1..9` | Switch to bus 1, 2, 3, ... (moves focus to sounds list) |

### Playback
| Shortcut | Action |
|----------|--------|
| `Enter` or `Space` | Play selected sound (default scenario) |
| `Alt+1..9` | Play selected sound with scenario 1, 2, 3, ... |
| `Escape` | Stop all sounds on the currently selected bus |
| `Ctrl+Escape` | Stop ALL sounds globally |
| `F1..F12` | User-assignable hotkeys (trigger specific sounds) |

### Volume
| Shortcut | Action |
|----------|--------|
| `Ctrl+Up` | Increase current bus volume by 5% |
| `Ctrl+Down` | Decrease current bus volume by 5% |
| `Ctrl+Shift+Up` | Increase master volume by 5% |
| `Ctrl+Shift+Down` | Decrease master volume by 5% |

### Editing
| Shortcut | Action |
|----------|--------|
| `Ctrl+N` | New project |
| `Ctrl+O` | Open project |
| `Ctrl+S` | Save project |
| `Ctrl+I` | Import sound(s) into current bus |
| `Ctrl+B` | Manage buses dialog |
| `Ctrl+E` | Edit scenarios for selected sound |
| `F2` | Rename/Edit selected sound |
| `Delete` | Remove selected sound (with confirmation) |

---

## 9. Dialogs (`ui_dialogs.py`)

### 9.1 New Project Dialog
- **Fields**: Project name (wx.TextCtrl), Location (wx.DirPickerCtrl)
- **Buttons**: Create, Cancel
- **On Create**: Calls `project_manager.create_project()`

### 9.2 Preferences Dialog
- **Output Device**: wx.Choice populated from `audio_engine.get_output_devices()`
- **Master Volume**: wx.Slider (0-100)
- **Buttons**: OK, Cancel

### 9.3 Add/Edit Sound Dialog
- **Fields**:
  - Name: wx.TextCtrl
  - File: wx.FilePickerCtrl (filtered to *.mp3, *.wav, *.ogg, *.flac)
  - Bus: wx.Choice (populated from project buses)
  - Hotkey: wx.TextCtrl (captures key press) or a dedicated hotkey picker
  - Volume: wx.Slider (0-100)
  - Fade In (ms): wx.SpinCtrl (0-10000)
  - Fade Out (ms): wx.SpinCtrl (0-10000)
  - Speed: wx.SpinCtrlDouble (0.1-3.0, step 0.1)
  - Loop: wx.CheckBox
- **Buttons**: OK, Cancel

### 9.4 Manage Buses Dialog
- **List** of buses with Name, Mode, Volume columns
- **Buttons**: Add, Edit, Remove, Close
- **Add/Edit sub-dialog**: Name (TextCtrl), Mode (Choice: exclusive/layered), Volume (Slider)

### 9.5 Edit Scenarios Dialog
- **Shows** the selected sound's name at the top
- **List** of scenarios (name, volume, fade_in, fade_out, speed, loop)
- **Buttons**: Add, Edit, Remove, Set as Default, Close

---

## 10. Entry Point (`soundboard.py`)

```python
import wx
from ui_main import MainFrame

def main():
    app = wx.App()
    frame = MainFrame(None, title="OklyPlay Soundboard")
    frame.Show()
    app.MainLoop()

if __name__ == "__main__":
    main()
```

On startup:
1. Initialize `Speech` singleton.
2. Initialize `AudioEngine` (open default device stream).
3. If a recent project path is saved in app settings, auto-load it.
4. Otherwise, show the "New Project" or "Open Project" dialog.

App settings (last project path, window size/position) stored in `wx.StandardPaths.Get().GetUserDataDir() / "settings.json"`.

---

## 11. Error Handling

| Error | Handling |
|-------|----------|
| Audio file corrupted / unreadable | Catch `soundfile.SoundFileError`, speak error, skip the file |
| Output device disconnected mid-stream | Catch `sounddevice.PortAudioError` in callback, attempt to reopen default device, speak error |
| Project JSON malformed | Catch `json.JSONDecodeError`, show error dialog, do not load |
| Hotkey conflict (same key assigned twice) | Warn user in dialog, prevent saving until resolved |
| Sound file missing from `sounds/` folder | On load, check existence. Mark missing sounds with "[MISSING]" prefix, speak warning |

---

## 12. Supported Audio Formats

Via `soundfile` (libsndfile):
- **MP3** (MPEG-1/2 Audio)
- **WAV** (Microsoft WAVE)
- **OGG** (Vorbis in OGG container)
- **FLAC** (Free Lossless Audio Codec)
- **AIFF** (Apple/SGI)
- **AU** (Sun/NeXT)
- **CAF** (Apple Core Audio File)
- **RF64** (RIFF 64)

File picker filter: `"Audio files (*.mp3;*.wav;*.ogg;*.flac;*.aiff)|*.mp3;*.wav;*.ogg;*.flac;*.aiff"`

---

## 13. File-by-File Implementation Order

Build in this exact order to resolve dependencies bottom-up:

1. **`accessible_speech.py`** — No dependencies. Simple singleton. Build and test first.
2. **`audio_engine.py`** — Depends on `sounddevice`, `soundfile`, `numpy`. Build `LoadedSound`, `Channel`, `AudioEngine` classes. Test with a hardcoded WAV file.
3. **`project_manager.py`** — Depends on `json`, `shutil`, `zipfile`, `uuid`. Pure data management. Test by creating/loading a project.
4. **`ui_dialogs.py`** — Depends on `wx`, `project_manager`, `audio_engine`. Build all dialogs.
5. **`ui_main.py`** — Depends on everything above. Build MainFrame, wire up events.
6. **`soundboard.py`** — Entry point. Wire everything together.

---

## 14. Testing Checklist

- [ ] `accessible_speech.py`: `Speech.speak("Hello")` announces via screen reader or SAPI
- [ ] `audio_engine.py`: Load a WAV, play it, hear audio. Play two sounds simultaneously. Test fade-in/out. Test exclusive bus stops old sound.
- [ ] `project_manager.py`: Create project, import sound, save, reload, verify JSON integrity. Export zip, import zip.
- [ ] `ui_main.py`: Launch app, navigate buses with Ctrl+1/2, navigate sounds with arrows, play with Enter, stop with Escape
- [ ] All keyboard shortcuts work as documented
- [ ] Screen reader announces all events from the speech table in section 5.2
- [ ] Device selection works (switch to different output device)
- [ ] Scenarios: create 2 scenarios, trigger via Alt+1 and Alt+2, verify different playback settings
- [ ] Import/export: export project, delete original, import from zip, verify everything works
