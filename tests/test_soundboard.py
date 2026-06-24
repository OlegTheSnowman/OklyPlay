import os
import sys
import shutil
import unittest
import numpy as np
import tempfile
import soundfile as sf
import json
import wx
from unittest.mock import MagicMock, patch

# Add src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from accessible_speech import Speech
from audio_engine import LoadedSound, Channel, AudioEngine
import project_manager
import ui_dialogs
import ui_main

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


class TestUIDialogs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Running wx.App to verify dialog widget construction
        cls.app = wx.App(False)

    @classmethod
    def tearDownClass(cls):
        cls.app.Destroy()

    def test_instantiate_dialogs(self):
        # 1. NewProjectDialog
        dlg1 = ui_dialogs.NewProjectDialog(None)
        self.assertIsNotNone(dlg1)
        dlg1.Destroy()
        
        # 2. PreferencesDialog
        devices = [(0, "Default Device"), (1, "Other Device")]
        dlg2 = ui_dialogs.PreferencesDialog(None, devices, current_device_index=0, current_volume=0.8)
        self.assertIsNotNone(dlg2)
        dlg2.Destroy()
        
        # 3. AddEditSoundDialog
        buses = [
            {"id": "bus-1", "name": "SFX", "mode": "layered", "volume": 1.0},
            {"id": "bus-2", "name": "Music", "mode": "exclusive", "volume": 0.7}
        ]
        dlg3 = ui_dialogs.AddEditSoundDialog(None, buses, sound_data=None)
        self.assertIsNotNone(dlg3)
        dlg3.Destroy()
        
        # 4. AddEditBusDialog
        dlg4 = ui_dialogs.AddEditBusDialog(None, bus_data=None)
        self.assertIsNotNone(dlg4)
        dlg4.Destroy()
        
        # 5. AddEditScenarioDialog
        dlg5 = ui_dialogs.AddEditScenarioDialog(None, buses, scenario_data=None)
        self.assertIsNotNone(dlg5)
        dlg5.Destroy()
        
        # 6. ManageBusesDialog
        project_data = {
            "name": "Test Board",
            "buses": buses,
            "sounds": []
        }
        dlg6 = ui_dialogs.ManageBusesDialog(None, project_data)
        self.assertIsNotNone(dlg6)
        dlg6.Destroy()
        
        # 7. EditScenariosDialog
        sound_data = {
            "id": "sound-1",
            "name": "Airhorn",
            "filename": "horn.mp3",
            "bus_id": "bus-1",
            "default_scenario": {},
            "scenarios": []
        }
        dlg7 = ui_dialogs.EditScenariosDialog(None, buses, sound_data)
        self.assertIsNotNone(dlg7)
        dlg7.Destroy()
        
        # 8. ProjectManagerDialog
        recent = [{"name": "P1", "path": "D:\\p1"}, {"name": "P2", "path": "D:\\p2"}]
        dlg8 = ui_dialogs.ProjectManagerDialog(None, recent, last_project_path="D:\\p1")
        self.assertIsNotNone(dlg8)
        dlg8.Destroy()


class TestMainFrame(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = wx.App(False)

    @classmethod
    def tearDownClass(cls):
        cls.app.Destroy()

    def setUp(self):
        # Temp directories
        self.temp_dir = tempfile.mkdtemp()
        self.temp_user_data_dir = tempfile.mkdtemp()
        
        # Mock StandardPaths
        self.mock_sp = MagicMock()
        self.mock_sp.GetUserDataDir.return_value = self.temp_user_data_dir
        self.patcher_sp = patch('wx.StandardPaths.Get', return_value=self.mock_sp)
        self.patcher_sp.start()
        
        # Mock sounddevice output stream so it doesn't try to open actual audio hardware
        self.mock_sd_stream = MagicMock()
        self.patcher_sd = patch('sounddevice.OutputStream', return_value=self.mock_sd_stream)
        self.patcher_sd.start()

        # Mock speech auto-output
        self.patcher_speech = patch('accessible_speech.Speech.speak')
        self.mock_speak = self.patcher_speech.start()

        # Setup standard test project
        self.proj_path = os.path.join(self.temp_dir, "MyTestProject")
        self.proj_data = project_manager.create_project(self.proj_path, "Cool Board")
        
        # Create a mock sound file to import
        self.sound_source = os.path.join(self.temp_dir, "horn.wav")
        sf.write(self.sound_source, np.zeros((1000, 2)), 44100)

    def tearDown(self):
        self.patcher_speech.stop()
        self.patcher_sd.stop()
        self.patcher_sp.stop()
        shutil.rmtree(self.temp_dir)
        shutil.rmtree(self.temp_user_data_dir)

    def test_mainframe_init_and_load_settings(self):
        # Test default init (no settings exist yet)
        frame = ui_main.MainFrame(None)
        self.assertIsNotNone(frame)
        self.assertEqual(frame.settings["recent_projects"], [])
        frame.Destroy()

    @patch('wx.MessageBox', return_value=wx.OK)
    def test_mainframe_load_project(self, mock_msgbox):
        frame = ui_main.MainFrame(None)
        frame.LoadProject(self.proj_path)
        self.assertEqual(frame.project_dir, self.proj_path)
        self.assertEqual(frame.project_data["name"], "Cool Board")
        self.assertEqual(len(frame.project_data["buses"]), 2)
        
        # Check settings updated
        self.assertEqual(frame.settings["last_project_path"], self.proj_path)
        self.assertEqual(frame.settings["recent_projects"][0]["path"], self.proj_path)
        
        # Clean up
        frame.Destroy()

    @patch('wx.MessageBox', return_value=wx.OK)
    def test_mainframe_load_project_failure(self, mock_msgbox):
        frame = ui_main.MainFrame(None)
        # Try to load non-existent path
        with patch('wx.CallAfter', lambda f, *a, **k: f(*a, **k)):
            with patch.object(frame, 'OnManageProjects') as mock_manage:
                frame.LoadProject("non_existent_path")
                self.assertTrue(mock_manage.called)
        frame.Destroy()

    @patch('wx.MessageBox', return_value=wx.OK)
    def test_volume_adjustments(self, mock_msgbox):
        frame = ui_main.MainFrame(None)
        frame.LoadProject(self.proj_path)
        
        # Test bus volume adjustment
        bus = frame.GetSelectedBus()
        initial_bus_vol = bus["volume"]
        
        # Vol Up (increases by 0.05)
        frame.OnBusVolUp(None)
        self.assertAlmostEqual(bus["volume"], min(initial_bus_vol + 0.05, 1.0))
        
        # Vol Down (decreases by 0.05)
        frame.OnBusVolDown(None)
        frame.OnBusVolDown(None)
        self.assertAlmostEqual(bus["volume"], min(initial_bus_vol + 0.05, 1.0) - 0.10)

        # Master Vol Up/Down
        initial_master_vol = frame.audio_engine._master_volume
        frame.OnMasterVolUp(None)
        self.assertAlmostEqual(frame.audio_engine._master_volume, min(initial_master_vol + 0.05, 1.0))
        frame.OnMasterVolDown(None)
        frame.OnMasterVolDown(None)
        self.assertAlmostEqual(frame.audio_engine._master_volume, min(initial_master_vol + 0.05, 1.0) - 0.10)
        
        frame.Destroy()

    @patch('wx.MessageBox', return_value=wx.OK)
    def test_bus_switching(self, mock_msgbox):
        frame = ui_main.MainFrame(None)
        frame.LoadProject(self.proj_path)
        
        # Initially first bus selected
        first_bus_id = frame.project_data["buses"][0]["id"]
        self.assertEqual(frame.selected_bus_id, first_bus_id)
        
        # Switch to Bus 2 (Ctrl+2 triggers OnSwitchBusHotkey with ID_BUS_BASE + 2)
        event = wx.CommandEvent(wx.wxEVT_MENU, ui_main.ID_BUS_BASE + 2)
        frame.OnSwitchBusHotkey(event)
        second_bus_id = frame.project_data["buses"][1]["id"]
        self.assertEqual(frame.selected_bus_id, second_bus_id)
        
        # Switch back to Bus 1
        event = wx.CommandEvent(wx.wxEVT_MENU, ui_main.ID_BUS_BASE + 1)
        frame.OnSwitchBusHotkey(event)
        self.assertEqual(frame.selected_bus_id, first_bus_id)
        
        frame.Destroy()

    def test_hotkey_parsing(self):
        frame = ui_main.MainFrame(None)
        
        # Test valid parsing
        accel1 = frame.ParseHotkeyToAccel("Ctrl+1", 1001)
        self.assertIsNotNone(accel1)
        self.assertEqual(accel1.GetFlags(), wx.ACCEL_CTRL | wx.ACCEL_NORMAL)
        self.assertEqual(accel1.GetKeyCode(), ord('1'))
        
        accel2 = frame.ParseHotkeyToAccel("Ctrl+Alt+Shift+F5", 1002)
        self.assertIsNotNone(accel2)
        self.assertEqual(accel2.GetFlags(), wx.ACCEL_CTRL | wx.ACCEL_ALT | wx.ACCEL_SHIFT)
        self.assertEqual(accel2.GetKeyCode(), wx.WXK_F5)
        
        accel3 = frame.ParseHotkeyToAccel("Space", 1003)
        self.assertIsNotNone(accel3)
        self.assertEqual(accel3.GetKeyCode(), wx.WXK_SPACE)

        accel4 = frame.ParseHotkeyToAccel("Enter", 1004)
        self.assertIsNotNone(accel4)
        self.assertEqual(accel4.GetKeyCode(), wx.WXK_RETURN)

        # Invalid hotkey
        accel_invalid = frame.ParseHotkeyToAccel("invalid_key_name", 1005)
        self.assertIsNone(accel_invalid)
        
        frame.Destroy()

    @patch('wx.MessageBox', return_value=wx.OK)
    def test_stop_commands(self, mock_msgbox):
        frame = ui_main.MainFrame(None)
        frame.LoadProject(self.proj_path)
        
        # Stop current bus
        with patch.object(frame.audio_engine, 'stop_bus') as mock_stop_bus:
            frame.OnStopBus(None)
            self.assertTrue(mock_stop_bus.called)
            
        # Stop all
        with patch.object(frame.audio_engine, 'stop_all') as mock_stop_all:
            frame.OnStopAll(None)
            self.assertTrue(mock_stop_all.called)
            
        frame.Destroy()

    @patch('wx.MessageBox', return_value=wx.OK)
    @patch('ui_dialogs.NewProjectDialog')
    def test_new_project_flow(self, mock_new_dlg_cls, mock_msgbox):
        frame = ui_main.MainFrame(None)
        frame.LoadProject(self.proj_path)
        
        mock_dlg = MagicMock()
        mock_dlg.ShowModal.return_value = wx.ID_OK
        mock_dlg.GetProjectName.return_value = "Brand New Board"
        new_proj_path = os.path.join(self.temp_dir, "BrandNewProject")
        mock_dlg.GetProjectPath.return_value = new_proj_path
        mock_new_dlg_cls.return_value = mock_dlg
        
        frame.OnNewProject(None)
        self.assertEqual(frame.project_dir, new_proj_path)
        self.assertEqual(frame.project_data["name"], "Brand New Board")
        frame.Destroy()

    @patch('wx.MessageBox', return_value=wx.OK)
    @patch('ui_dialogs.AddEditSoundDialog')
    def test_add_sound_flow(self, mock_sound_dlg_cls, mock_msgbox):
        frame = ui_main.MainFrame(None)
        frame.LoadProject(self.proj_path)
        
        mock_dlg = MagicMock()
        mock_dlg.ShowModal.return_value = wx.ID_OK
        
        # sound_data returned by dialog includes full absolute path
        new_sound_data = {
            "id": "sound-new-123",
            "name": "Siren",
            "filepath_full": self.sound_source,
            "bus_id": frame.project_data["buses"][0]["id"],
            "hotkey": "F3",
            "default_scenario": {
                "volume": 0.9,
                "fade_in_ms": 100,
                "fade_out_ms": 100,
                "speed": 1.0,
                "loop": False
            },
            "scenarios": []
        }
        mock_dlg.GetSoundData.return_value = new_sound_data.copy()
        mock_sound_dlg_cls.return_value = mock_dlg
        
        frame.OnAddSound(None)
        
        # Verify sound was added to project data
        sounds = frame.project_data["sounds"]
        self.assertEqual(len(sounds), 1)
        self.assertEqual(sounds[0]["name"], "Siren")
        self.assertEqual(sounds[0]["filename"], "horn.wav")
        self.assertEqual(sounds[0]["hotkey"], "F3")
        
        frame.Destroy()

    @patch('wx.MessageBox', return_value=wx.YES)
    def test_remove_sound_flow(self, mock_msgbox):
        frame = ui_main.MainFrame(None)
        frame.LoadProject(self.proj_path)
        
        # Add a mock sound manually to metadata first
        sound_meta = {
            "id": "sound-meta-1",
            "name": "Existing Sound",
            "filename": "horn.wav",
            "bus_id": frame.project_data["buses"][0]["id"],
            "hotkey": "F4",
            "default_scenario": {},
            "scenarios": []
        }
        frame.project_data["sounds"].append(sound_meta)
        frame.RefreshSoundsList()
        
        # Select the item
        frame.sounds_list.Select(0)
        
        # Trigger remove
        frame.OnRemoveSound(None)
        
        # Check removed
        self.assertEqual(len(frame.project_data["sounds"]), 0)
        frame.Destroy()

    @patch('wx.MessageBox', return_value=wx.OK)
    @patch('ui_dialogs.PreferencesDialog')
    def test_preferences_flow(self, mock_pref_dlg_cls, mock_msgbox):
        frame = ui_main.MainFrame(None)
        frame.LoadProject(self.proj_path)
        
        mock_dlg = MagicMock()
        mock_dlg.ShowModal.return_value = wx.ID_OK
        mock_dlg.GetSelectedDeviceIndex.return_value = 1
        mock_dlg.GetMasterVolume.return_value = 0.5
        mock_pref_dlg_cls.return_value = mock_dlg
        
        frame.OnPreferences(None)
        
        self.assertEqual(frame.audio_engine._device_index, 1)
        self.assertEqual(frame.audio_engine._master_volume, 0.5)
        self.assertEqual(frame.project_data["output_device"], 1)
        self.assertEqual(frame.project_data["master_volume"], 0.5)
        frame.Destroy()


class TestProjectManagerDialogActions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = wx.App(False)

    @classmethod
    def tearDownClass(cls):
        cls.app.Destroy()

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.p1_path = os.path.join(self.temp_dir, "Proj1")
        self.p2_path = os.path.join(self.temp_dir, "Proj2")
        os.makedirs(self.p1_path, exist_ok=True)
        os.makedirs(self.p2_path, exist_ok=True)
        
        self.recent = [
            {"name": "Proj1", "path": self.p1_path},
            {"name": "Proj2", "path": self.p2_path}
        ]
        
        self.patcher_speech = patch('accessible_speech.Speech.speak')
        self.mock_speak = self.patcher_speech.start()

    def tearDown(self):
        self.patcher_speech.stop()
        shutil.rmtree(self.temp_dir)

    def test_dialog_init_and_list_population(self):
        dlg = ui_dialogs.ProjectManagerDialog(None, self.recent, last_project_path=self.p2_path)
        self.assertEqual(dlg.projects_list.GetItemCount(), 2)
        # Proj2 (index 1) should be selected as last_project_path matches
        self.assertEqual(dlg.projects_list.GetFirstSelected(), 1)
        dlg.Destroy()

    def test_dialog_actions(self):
        # Open
        dlg = ui_dialogs.ProjectManagerDialog(None, self.recent)
        dlg.projects_list.Select(0)
        with patch.object(dlg, 'EndModal'):
            dlg.OnOpen(None)
        self.assertEqual(dlg.action, 'open')
        self.assertEqual(dlg.selected_project_path, self.p1_path)
        dlg.Destroy()

        # New
        dlg = ui_dialogs.ProjectManagerDialog(None, self.recent)
        with patch.object(dlg, 'EndModal'):
            dlg.OnNew(None)
        self.assertEqual(dlg.action, 'create')
        dlg.Destroy()

        # Browse
        dlg = ui_dialogs.ProjectManagerDialog(None, self.recent)
        with patch.object(dlg, 'EndModal'):
            dlg.OnBrowse(None)
        self.assertEqual(dlg.action, 'browse')
        dlg.Destroy()

        # Exit
        dlg = ui_dialogs.ProjectManagerDialog(None, self.recent)
        with patch.object(dlg, 'EndModal'):
            dlg.OnExitBtn(None)
        self.assertEqual(dlg.action, 'exit')
        dlg.Destroy()

    def test_remove_action(self):
        dlg = ui_dialogs.ProjectManagerDialog(None, self.recent)
        dlg.projects_list.Select(0)
        dlg.OnRemove(None)
        self.assertEqual(len(dlg.recent_projects), 1)
        self.assertEqual(dlg.recent_projects[0]["name"], "Proj2")
        self.assertEqual(dlg.projects_list.GetItemCount(), 1)
        dlg.Destroy()

    @patch('wx.MessageBox', return_value=wx.YES)
    def test_delete_action_confirmed(self, mock_msgbox):
        dlg = ui_dialogs.ProjectManagerDialog(None, self.recent)
        dlg.projects_list.Select(0)
        
        self.assertTrue(os.path.exists(self.p1_path))
        
        dlg.OnDelete(None)
        
        self.assertFalse(os.path.exists(self.p1_path))
        self.assertEqual(len(dlg.recent_projects), 1)
        self.assertEqual(dlg.recent_projects[0]["name"], "Proj2")
        dlg.Destroy()


class TestHotkeyCtrl(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = wx.App(False)

    @classmethod
    def tearDownClass(cls):
        cls.app.Destroy()

    def test_hotkey_ctrl_captures_keys(self):
        frame = wx.Frame(None)
        ctrl = ui_dialogs.HotkeyCtrl(frame)
        
        # 1. Test ignoring modifiers when pressed by themselves
        event_mod = MagicMock()
        event_mod.GetKeyCode.return_value = wx.WXK_CONTROL
        event_mod.GetModifiers.return_value = wx.MOD_CONTROL
        
        ctrl.OnKeyDown(event_mod)
        self.assertEqual(ctrl.GetValue(), "")
        
        # 2. Test Ctrl + Shift + A
        event_combo = MagicMock()
        event_combo.GetKeyCode.return_value = ord('A')
        event_combo.GetModifiers.return_value = wx.MOD_CONTROL | wx.MOD_SHIFT
        
        ctrl.OnKeyDown(event_combo)
        self.assertEqual(ctrl.GetValue(), "Ctrl+Shift+A")
        
        # 3. Test Escape
        event_esc = MagicMock()
        event_esc.GetKeyCode.return_value = wx.WXK_ESCAPE
        event_esc.GetModifiers.return_value = 0
        
        ctrl.OnKeyDown(event_esc)
        self.assertEqual(ctrl.GetValue(), "Escape")

        # 4. Test Backspace clears
        event_back = MagicMock()
        event_back.GetKeyCode.return_value = wx.WXK_BACK
        event_back.GetModifiers.return_value = 0
        
        ctrl.OnKeyDown(event_back)
        self.assertEqual(ctrl.GetValue(), "")
        
        frame.Destroy()


class TestAccessibilityLabeling(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = wx.App(False)

    @classmethod
    def tearDownClass(cls):
        cls.app.Destroy()

    def test_dialog_controls_are_labeled(self):
        # 1. NewProjectDialog
        dlg1 = ui_dialogs.NewProjectDialog(None)
        self.assertEqual(dlg1.name_txt.GetAccessible().GetName(0)[1], "Project Name")
        self.assertEqual(dlg1.loc_txt.GetAccessible().GetName(0)[1], "Project Location")
        self.assertEqual(dlg1.browse_btn.GetAccessible().GetName(0)[1], "Browse Project Location")
        dlg1.Destroy()
        
        # 2. PreferencesDialog
        devices = [(0, "Default Device")]
        dlg2 = ui_dialogs.PreferencesDialog(None, devices, current_device_index=0, current_volume=0.8)
        self.assertEqual(dlg2.device_choice.GetAccessible().GetName(0)[1], "Audio Output Device")
        self.assertEqual(dlg2.vol_slider.GetAccessible().GetName(0)[1], "Master Volume")
        dlg2.Destroy()
        
        # 3. AddEditSoundDialog
        buses = [{"id": "bus-1", "name": "SFX", "mode": "layered", "volume": 1.0}]
        dlg3 = ui_dialogs.AddEditSoundDialog(None, buses)
        self.assertEqual(dlg3.name_txt.GetAccessible().GetName(0)[1], "Sound Name")
        self.assertEqual(dlg3.file_txt.GetAccessible().GetName(0)[1], "Audio File Path")
        self.assertEqual(dlg3.file_browse_btn.GetAccessible().GetName(0)[1], "Browse Audio File")
        self.assertEqual(dlg3.bus_choice.GetAccessible().GetName(0)[1], "Bus Assignment")
        self.assertEqual(dlg3.hotkey_txt.GetAccessible().GetName(0)[1], "Hotkey Assignment")
        self.assertEqual(dlg3.vol_slider.GetAccessible().GetName(0)[1], "Volume")
        self.assertEqual(dlg3.fade_in_spin.GetAccessible().GetName(0)[1], "Fade In Milliseconds")
        self.assertEqual(dlg3.fade_out_spin.GetAccessible().GetName(0)[1], "Fade Out Milliseconds")
        self.assertEqual(dlg3.speed_spin.GetAccessible().GetName(0)[1], "Playback Speed Multiplier")
        self.assertEqual(dlg3.loop_chk.GetAccessible().GetName(0)[1], "Loop Audio")
        dlg3.Destroy()
        
        # 4. AddEditBusDialog
        dlg4 = ui_dialogs.AddEditBusDialog(None)
        self.assertEqual(dlg4.name_txt.GetAccessible().GetName(0)[1], "Bus Name")
        self.assertEqual(dlg4.mode_choice.GetAccessible().GetName(0)[1], "Playback Mode")
        self.assertEqual(dlg4.vol_slider.GetAccessible().GetName(0)[1], "Volume")
        dlg4.Destroy()

        # 5. ManageBusesDialog
        project_data = {
            "name": "Test Board",
            "buses": buses,
            "sounds": []
        }
        dlg5 = ui_dialogs.ManageBusesDialog(None, project_data)
        self.assertEqual(dlg5.bus_list.GetAccessible().GetName(0)[1], "Buses List")
        dlg5.Destroy()

        # 6. AddEditScenarioDialog
        dlg6 = ui_dialogs.AddEditScenarioDialog(None, buses)
        self.assertEqual(dlg6.name_txt.GetAccessible().GetName(0)[1], "Scenario Name")
        self.assertEqual(dlg6.vol_slider.GetAccessible().GetName(0)[1], "Volume Override")
        self.assertEqual(dlg6.fade_in_spin.GetAccessible().GetName(0)[1], "Fade In Milliseconds")
        self.assertEqual(dlg6.fade_out_spin.GetAccessible().GetName(0)[1], "Fade Out Milliseconds")
        self.assertEqual(dlg6.speed_spin.GetAccessible().GetName(0)[1], "Speed Override")
        self.assertEqual(dlg6.loop_chk.GetAccessible().GetName(0)[1], "Loop Override")
        self.assertEqual(dlg6.bus_choice.GetAccessible().GetName(0)[1], "Bus Override")
        dlg6.Destroy()

        # 7. EditScenariosDialog
        sound_data = {
            "id": "sound-1",
            "name": "Airhorn",
            "filename": "horn.mp3",
            "bus_id": "bus-1",
            "default_scenario": {},
            "scenarios": []
        }
        dlg7 = ui_dialogs.EditScenariosDialog(None, buses, sound_data)
        self.assertEqual(dlg7.scen_list.GetAccessible().GetName(0)[1], "Scenarios List")
        dlg7.Destroy()

        # 8. ProjectManagerDialog
        recent = [{"name": "P1", "path": "D:\\p1"}]
        dlg8 = ui_dialogs.ProjectManagerDialog(None, recent)
        self.assertEqual(dlg8.projects_list.GetAccessible().GetName(0)[1], "Recent Projects List")
        dlg8.Destroy()


if __name__ == "__main__":
    unittest.main()

