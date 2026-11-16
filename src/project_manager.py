import os
import json
import shutil
import tempfile
import zipfile
import uuid
from accessible_speech import Speech

# Playback settings a sound starts with, and the values filled in for keys
# missing from older project files.
DEFAULT_SCENARIO = {
    "volume": 1.0,
    "fade_in_ms": 0,
    "fade_out_ms": 0,
    "speed": 1.0,
    "pitch_semitones": 0.0,
    "loop": False,
}

# Per-mode bus settings: what a new bus of that mode starts with, and what
# fills in when an older project file lacks the key.
BUS_MODE_DEFAULTS = {
    "exclusive": {"crossfade_ms": 500, "hotkey_action": "loop_shuffle", "track_crossfade_ms": 2000,
                  "duck_factor": 1.0, "duckable": True},
    "layered":   {"crossfade_ms": 0, "hotkey_action": "single_shuffle", "track_crossfade_ms": 0,
                  "duck_factor": 1.0, "duckable": False},
}

def bus_setting(bus, key):
    """A bus setting, falling back to the default for the bus's mode (layered if unknown)."""
    defaults = BUS_MODE_DEFAULTS.get(bus.get("mode"), BUS_MODE_DEFAULTS["layered"])
    return bus.get(key, defaults[key])

def create_project(path, name):
    """Creates a new project directory with default buses and config file."""
    os.makedirs(path, exist_ok=True)
    sounds_dir = os.path.join(path, "sounds")
    os.makedirs(sounds_dir, exist_ok=True)
    
    music_bus_id = str(uuid.uuid4())
    sfx_bus_id = str(uuid.uuid4())
    
    project_data = {
        "name": name,
        "version": 1,
        "master_volume": 0.8,
        "output_device": None,
        "buses": [
            dict(id=music_bus_id, name="Music", mode="exclusive", volume=0.7,
                 **BUS_MODE_DEFAULTS["exclusive"]),
            dict(id=sfx_bus_id, name="SFX", mode="layered", volume=1.0,
                 **BUS_MODE_DEFAULTS["layered"]),
        ],
        "sounds": []
    }
    
    save_project(path, project_data)
    return project_data

def load_project(path):
    """Loads a project config, validates the schema, and detects missing sound files."""
    json_path = os.path.join(path, "project.json")
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"project.json not found in {path}")
        
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    # Basic schema validation/normalization
    if "buses" not in data:
        data["buses"] = []
    for bus in data["buses"]:
        for key in BUS_MODE_DEFAULTS["layered"]:
            bus[key] = bus_setting(bus, key)
    if "sounds" not in data:
        data["sounds"] = []
    if "master_volume" not in data:
        data["master_volume"] = 1.0
    if "output_device" not in data:
        data["output_device"] = None
        
    sounds_dir = os.path.join(path, "sounds")
    if not os.path.exists(sounds_dir):
        os.makedirs(sounds_dir, exist_ok=True)
        
    for sound in data["sounds"]:
        for scen in [sound.setdefault("default_scenario", {})] + sound.get("scenarios", []):
            for key, value in DEFAULT_SCENARIO.items():
                scen.setdefault(key, value)

    missing_count = 0
    for sound in data["sounds"]:
        filename = sound.get("filename", "")
        sound_file_path = os.path.join(sounds_dir, filename)
        if not os.path.exists(sound_file_path):
            sound["missing"] = True
            missing_count += 1
            if not sound["name"].startswith("[MISSING]"):
                sound["name"] = f"[MISSING] {sound['name']}"
        else:
            sound["missing"] = False
            if sound["name"].startswith("[MISSING] "):
                sound["name"] = sound["name"][10:]
                
    if missing_count > 0:
        Speech.speak(f"Warning: {missing_count} sounds are missing from this project.")
        
    return data

def save_project(path, data):
    """Saves the project data atomically to project.json."""
    json_path = os.path.join(path, "project.json")
    tmp_path = json_path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        if os.path.exists(json_path):
            os.replace(tmp_path, json_path)
        else:
            os.rename(tmp_path, json_path)
    except Exception as e:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        raise e

def import_sound(project_path, source_file_path):
    """Copies a sound file into the project's sounds directory and returns the relative path."""
    sounds_dir = os.path.join(project_path, "sounds")
    os.makedirs(sounds_dir, exist_ok=True)
    
    filename = os.path.basename(source_file_path)
    base, ext = os.path.splitext(filename)
    
    target_filename = filename
    counter = 1
    while os.path.exists(os.path.join(sounds_dir, target_filename)):
        target_filename = f"{base}_{counter}{ext}"
        counter += 1
        
    target_path = os.path.join(sounds_dir, target_filename)
    shutil.copy2(source_file_path, target_path)
    return target_filename

def export_project(project_path, zip_path):
    """Zips the entire project directory contents."""
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(project_path):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, project_path)
                if rel_path.endswith(".tmp") or rel_path.endswith(".zip"):
                    continue
                zipf.write(full_path, rel_path)

def is_project_dir(path):
    """True if path is a folder holding an OklyPlay project.json."""
    return os.path.isfile(os.path.join(path, "project.json"))

def import_project(zip_path, target_dir):
    """Unzips a project archive into target_dir, which must not exist yet or be empty.

    project.json may sit at the root of the zip (OklyPlay's own export) or inside
    one top-level folder (a folder zipped with Explorer's Send to). The archive is
    unpacked into a scratch folder first, so a bad zip never touches existing files."""
    if os.path.isdir(target_dir) and os.listdir(target_dir):
        raise ValueError(f"The folder {target_dir} already exists and is not empty. "
                         "Choose another destination.")
    parent = os.path.dirname(os.path.abspath(target_dir))
    os.makedirs(parent, exist_ok=True)
    scratch = tempfile.mkdtemp(prefix=".oklyplay-import-", dir=parent)
    try:
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            zipf.extractall(scratch)
        root = scratch
        if not is_project_dir(root):
            entries = [e for e in os.listdir(scratch) if not e.startswith("__MACOSX")]
            if len(entries) == 1 and is_project_dir(os.path.join(scratch, entries[0])):
                root = os.path.join(scratch, entries[0])
            else:
                raise ValueError("This zip is not an OklyPlay project: project.json was not found.")
        if os.path.isdir(target_dir):
            os.rmdir(target_dir)  # empty, checked above
        shutil.move(root, target_dir)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
