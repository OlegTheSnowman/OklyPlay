import os
import shutil
import unittest
import numpy as np
import tempfile
import soundfile as sf
import json

from accessible_speech import Speech
from audio_engine import LoadedSound, Channel, AudioEngine
import project_manager

class TestSpeechModule(unittest.TestCase):
    def test_singleton(self):
        s1 = Speech.get()
        s2 = Speech.get()
        self.assertEqual(s1, s2)

class TestAudioEngine(unittest.TestCase):
    def setUp(self):
        # Create a temporary WAV file for testing
        self.temp_dir = tempfile.mkdtemp()
        self.wav_path = os.path.join(self.temp_dir, "test.wav")
        
        # 1 second of stereo 440Hz sine wave
        self.sample_rate = 44100
        t = np.linspace(0, 1.0, self.sample_rate, endpoint=False)
        sine = np.sin(2 * np.pi * 440.0 * t)
        self.stereo_data = np.column_stack((sine, sine)).astype(np.float32)
        sf.write(self.wav_path, self.stereo_data, self.sample_rate)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_loaded_sound_resampling(self):
        # Test loading normal file
        sound = LoadedSound(self.wav_path, self.sample_rate)
        self.assertEqual(sound.samplerate, self.sample_rate)
        self.assertEqual(sound.data.shape, (self.sample_rate, 2))
        
        # Test resampling down to 22050
        sound_resampled = LoadedSound(self.wav_path, 22050)
        self.assertEqual(sound_resampled.samplerate, 22050)
        self.assertEqual(sound_resampled.data.shape, (22050, 2))

    def test_loaded_sound_speed_adjustment(self):
        sound = LoadedSound(self.wav_path, self.sample_rate)
        
        # Speed 2.0 (should halve the sample count)
        data_2x = sound.get_data_for_speed(2.0)
        self.assertEqual(data_2x.shape, (self.sample_rate // 2, 2))
        
        # Speed 0.5 (should double the sample count)
        data_05x = sound.get_data_for_speed(0.5)
        self.assertEqual(data_05x.shape, (self.sample_rate * 2, 2))

    def test_channel_fades(self):
        sound = LoadedSound(self.wav_path, self.sample_rate)
        
        # Fade In Test
        fade_in_ms = 100
        fade_in_samples = int(fade_in_ms * self.sample_rate / 1000) # 4410
        ch = Channel(
            sound_data=sound.data,
            volume=1.0,
            fade_in_ms=fade_in_ms,
            fade_out_ms=0,
            loop=False,
            bus_id="test_bus",
            sample_rate=self.sample_rate
        )
        
        # Render first chunk
        chunk = ch.render(2000)
        # Verify it started at 0 volume and increased
        self.assertTrue(np.all(np.abs(chunk[0]) < 1e-4))
        self.assertTrue(np.all(np.abs(chunk[1999]) > np.abs(chunk[1])))
        
        # Fade Out Test
        ch2 = Channel(
            sound_data=sound.data,
            volume=1.0,
            fade_in_ms=0,
            fade_out_ms=100,
            loop=False,
            bus_id="test_bus",
            sample_rate=self.sample_rate
        )
        # Render a chunk to start
        ch2.render(2000)
        # Trigger fade-out
        ch2.start_fade_out()
        self.assertTrue(ch2._fading_out)
        self.assertFalse(ch2.is_done)
        
        # Render rest and verify it eventually completes
        ch2.render(5000)
        self.assertTrue(ch2.is_done)


class TestProjectManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.proj_path = os.path.join(self.temp_dir, "MyTestProject")
        
        # Create a mock sound file to import
        self.sound_source = os.path.join(self.temp_dir, "horn.wav")
        sf.write(self.sound_source, np.zeros((1000, 2)), 44100)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_create_and_load_and_save(self):
        # Create
        data = project_manager.create_project(self.proj_path, "Cool Board")
        self.assertEqual(data["name"], "Cool Board")
        self.assertEqual(len(data["buses"]), 2)
        
        # Load
        loaded_data = project_manager.load_project(self.proj_path)
        self.assertEqual(loaded_data["name"], "Cool Board")
        
        # Import sound
        rel_path = project_manager.import_sound(self.proj_path, self.sound_source)
        self.assertEqual(rel_path, "horn.wav")
        self.assertTrue(os.path.exists(os.path.join(self.proj_path, "sounds", rel_path)))
        
        # Add to metadata and save
        new_sound = {
            "id": "sound-1",
            "name": "Horn",
            "filename": rel_path,
            "bus_id": loaded_data["buses"][0]["id"],
            "hotkey": "F1",
            "default_scenario": {
                "volume": 1.0,
                "fade_in_ms": 0,
                "fade_out_ms": 0,
                "speed": 1.0,
                "loop": False
            },
            "scenarios": []
        }
        loaded_data["sounds"].append(new_sound)
        project_manager.save_project(self.proj_path, loaded_data)
        
        # Reload and verify
        reloaded = project_manager.load_project(self.proj_path)
        self.assertEqual(len(reloaded["sounds"]), 1)
        self.assertEqual(reloaded["sounds"][0]["name"], "Horn")

    def test_import_export_zip(self):
        project_manager.create_project(self.proj_path, "ExportProj")
        
        zip_path = os.path.join(self.temp_dir, "export.zip")
        project_manager.export_project(self.proj_path, zip_path)
        self.assertTrue(os.path.exists(zip_path))
        
        import_path = os.path.join(self.temp_dir, "ImportProj")
        project_manager.import_project(zip_path, import_path)
        self.assertTrue(os.path.exists(os.path.join(import_path, "project.json")))
        
        loaded = project_manager.load_project(import_path)
        self.assertEqual(loaded["name"], "ExportProj")

if __name__ == "__main__":
    unittest.main()
