import os
import json
import shutil
import zipfile
import uuid
from accessible_speech import Speech

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
            {
                "id": music_bus_id,
                "name": "Music",
                "mode": "exclusive",
                "volume": 0.7
            },
            {
                "id": sfx_bus_id,
                "name": "SFX",
                "mode": "layered",
                "volume": 1.0
            }
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
    if "sounds" not in data:
        data["sounds"] = []
    if "master_volume" not in data:
        data["master_volume"] = 1.0
    if "output_device" not in data:
        data["output_device"] = None
        
    sounds_dir = os.path.join(path, "sounds")
    if not os.path.exists(sounds_dir):
        os.makedirs(sounds_dir, exist_ok=True)
        
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

def import_project(zip_path, target_dir):
    """Unzips a project archive and verifies it contains a valid project.json."""
    os.makedirs(target_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zipf:
        zipf.extractall(target_dir)
        
    json_path = os.path.join(target_dir, "project.json")
    if not os.path.exists(json_path):
        shutil.rmtree(target_dir, ignore_errors=True)
        raise ValueError("Invalid project zip: project.json not found at root.")
