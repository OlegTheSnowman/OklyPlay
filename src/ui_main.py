import wx
import os
import json
import shutil
from accessible_speech import Speech
from audio_engine import AudioEngine
import project_manager
import ui_dialogs
from version import __version__

# Custom wx IDs
ID_NEW_PROJECT = wx.ID_NEW
ID_OPEN_PROJECT = wx.ID_OPEN
ID_SAVE_PROJECT = wx.ID_SAVE
ID_EXPORT_PROJECT = wx.ID_HIGHEST + 1
ID_IMPORT_PROJECT = wx.ID_HIGHEST + 2

ID_ADD_SOUND = wx.ID_HIGHEST + 3
ID_EDIT_SOUND = wx.ID_HIGHEST + 4
ID_REMOVE_SOUND = wx.ID_HIGHEST + 5
ID_EDIT_SCENARIOS = wx.ID_HIGHEST + 6

ID_MANAGE_BUSES = wx.ID_HIGHEST + 7
ID_STOP_BUS = wx.ID_HIGHEST + 8
ID_STOP_ALL = wx.ID_HIGHEST + 9

ID_BUS_VOL_UP = wx.ID_HIGHEST + 10
ID_BUS_VOL_DOWN = wx.ID_HIGHEST + 11
ID_MASTER_VOL_UP = wx.ID_HIGHEST + 12
ID_MASTER_VOL_DOWN = wx.ID_HIGHEST + 13
ID_MANAGE_PROJECTS = wx.ID_HIGHEST + 14
ID_SET_SOUND_HOTKEY = wx.ID_HIGHEST + 15

ID_BUS_BASE = wx.ID_HIGHEST + 100  # ID_BUS_BASE + 1 to 9
ID_SCENARIO_BASE = wx.ID_HIGHEST + 200  # ID_SCENARIO_BASE + 1 to 9

class MainFrame(wx.Frame):
    def __init__(self, parent, title="OklyPlay Soundboard"):
        super().__init__(parent, title=title, size=(800, 600))
        
        # Audio Engine and Project attributes
        self.audio_engine = None
        self.project_dir = None
        self.project_data = None
        self.selected_bus_id = None
        self.current_bus_sounds = []
        self.hotkey_id_map = {}
        self.bus_hotkey_map = {}
        self.active_bus_playlists = {}
        
        # Initialize Audio Engine
        self.audio_engine = AudioEngine()
        
        # Setup UI layout
        self.InitUI()
        
        # Setup cleanup timer (checks audio engine for finished streams)
        self.cleanup_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.OnCleanupTimer, self.cleanup_timer)
        self.cleanup_timer.Start(100)  # every 100ms
        
        # Load last project
        self.LoadSettingsAndLastProject()
        
        # Bind Close event
        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def InitUI(self):
        # Create Splitter Window
        self.splitter = wx.SplitterWindow(self, style=wx.SP_3D | wx.SP_LIVE_UPDATE)
        
        # Left Panel (Buses)
        self.left_panel = wx.Panel(self.splitter)
        left_sizer = wx.BoxSizer(wx.VERTICAL)
        left_lbl = wx.StaticText(self.left_panel, label="Buses:")
        self.buses_list = wx.ListBox(self.left_panel, style=wx.LB_SINGLE)
        ui_dialogs.label_control(self.buses_list, "Buses")
        left_sizer.Add(left_lbl, 0, wx.ALL, 5)
        left_sizer.Add(self.buses_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        self.left_panel.SetSizer(left_sizer)
        
        # Right Panel (Sounds)
        self.right_panel = wx.Panel(self.splitter)
        right_sizer = wx.BoxSizer(wx.VERTICAL)
        right_lbl = wx.StaticText(self.right_panel, label="Sounds:")
        self.sounds_list = wx.ListCtrl(self.right_panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        ui_dialogs.label_control(self.sounds_list, "Sounds")
        self.sounds_list.InsertColumn(0, "Name", width=250)
        self.sounds_list.InsertColumn(1, "Hotkey", width=100)
        self.sounds_list.InsertColumn(2, "Scenarios", width=120)
        
        right_sizer.Add(right_lbl, 0, wx.ALL, 5)
        right_sizer.Add(self.sounds_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        self.right_panel.SetSizer(right_sizer)
        
        # Split layout
        self.splitter.SplitVertically(self.left_panel, self.right_panel, 220)
        
        # Create Menu Bar
        self.CreateMenuBar()
        
        # Create Status Bar (3 fields)
        self.status_bar = self.CreateStatusBar(3)
        self.status_bar.SetStatusWidths([-2, -1, -1])
        
        # Bind events
        self.buses_list.Bind(wx.EVT_LISTBOX, self.OnBusSelected)
        self.sounds_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnSoundActivated)
        self.sounds_list.Bind(wx.EVT_KEY_DOWN, self.OnSoundsListKeyDown)
        
        # Set default focus
        self.buses_list.SetFocus()

    def CreateMenuBar(self):
        menubar = wx.MenuBar()
        
        # File Menu
        file_menu = wx.Menu()
        file_menu.Append(ID_NEW_PROJECT, "&New Project...\tCtrl+N")
        file_menu.Append(ID_OPEN_PROJECT, "&Open Project...\tCtrl+O")
        file_menu.Append(ID_SAVE_PROJECT, "&Save Project\tCtrl+S")
        file_menu.Append(ID_MANAGE_PROJECTS, "&Manage Projects...\tCtrl+M")
        file_menu.AppendSeparator()
        file_menu.Append(ID_EXPORT_PROJECT, "&Export Project (Zip)...")
        file_menu.Append(ID_IMPORT_PROJECT, "&Import Project (Zip)...")
        file_menu.AppendSeparator()
        file_menu.Append(wx.ID_PREFERENCES, "&Preferences...")
        file_menu.AppendSeparator()
        file_menu.Append(wx.ID_EXIT, "E&xit")
        menubar.Append(file_menu, "&File")
        
        # Edit Menu
        edit_menu = wx.Menu()
        edit_menu.Append(ID_ADD_SOUND, "&Add Sound...\tCtrl+I")
        edit_menu.Append(ID_EDIT_SOUND, "&Edit Sound...\tF2")
        edit_menu.Append(ID_REMOVE_SOUND, "&Remove Sound\tDelete")
        edit_menu.Append(ID_SET_SOUND_HOTKEY, "Set Hotkey...\tAlt+K")
        edit_menu.AppendSeparator()
        edit_menu.Append(ID_EDIT_SCENARIOS, "Edit S&cenarios...\tCtrl+E")
        menubar.Append(edit_menu, "&Edit")
        
        # Buses Menu
        buses_menu = wx.Menu()
        buses_menu.Append(ID_MANAGE_BUSES, "&Manage Buses...\tCtrl+B")
        buses_menu.AppendSeparator()
        
        # Dynamic items for Bus selection (Ctrl+1..9)
        for i in range(1, 10):
            buses_menu.Append(ID_BUS_BASE + i, f"Switch to Bus {i}\tCtrl+{i}")
            
        buses_menu.AppendSeparator()
        buses_menu.Append(ID_STOP_BUS, "Stop Current Bus\tEscape")
        buses_menu.Append(ID_STOP_ALL, "Stop All Sounds\tAlt+Escape")
        
        # Volume items
        buses_menu.AppendSeparator()
        buses_menu.Append(ID_BUS_VOL_UP, "Increase Bus Volume (5%)\tCtrl+Up")
        buses_menu.Append(ID_BUS_VOL_DOWN, "Decrease Bus Volume (5%)\tCtrl+Down")
        buses_menu.Append(ID_MASTER_VOL_UP, "Increase Master Volume (5%)\tCtrl+Shift+Up")
        buses_menu.Append(ID_MASTER_VOL_DOWN, "Decrease Master Volume (5%)\tCtrl+Shift+Down")
        
        menubar.Append(buses_menu, "&Buses")
        
        # Scenario Shortcuts Menu (Hidden or explicit, Alt+1..9)
        scen_menu = wx.Menu()
        for i in range(1, 10):
            scen_menu.Append(ID_SCENARIO_BASE + i, f"Play Scenario {i}\tAlt+{i}")
        menubar.Append(scen_menu, "&Scenarios")
        
        # Help Menu
        help_menu = wx.Menu()
        help_menu.Append(wx.ID_ABOUT, "&About...")
        menubar.Append(help_menu, "&Help")
        
        self.SetMenuBar(menubar)
        
        # Bind Menu events
        self.Bind(wx.EVT_MENU, self.OnNewProject, id=ID_NEW_PROJECT)
        self.Bind(wx.EVT_MENU, self.OnOpenProject, id=ID_OPEN_PROJECT)
        self.Bind(wx.EVT_MENU, self.OnSaveProject, id=ID_SAVE_PROJECT)
        self.Bind(wx.EVT_MENU, self.OnManageProjects, id=ID_MANAGE_PROJECTS)
        self.Bind(wx.EVT_MENU, self.OnExportProject, id=ID_EXPORT_PROJECT)
        self.Bind(wx.EVT_MENU, self.OnImportProject, id=ID_IMPORT_PROJECT)
        self.Bind(wx.EVT_MENU, self.OnPreferences, id=wx.ID_PREFERENCES)
        self.Bind(wx.EVT_MENU, self.OnExit, id=wx.ID_EXIT)
        
        self.Bind(wx.EVT_MENU, self.OnAddSound, id=ID_ADD_SOUND)
        self.Bind(wx.EVT_MENU, self.OnEditSound, id=ID_EDIT_SOUND)
        self.Bind(wx.EVT_MENU, self.OnRemoveSound, id=ID_REMOVE_SOUND)
        self.Bind(wx.EVT_MENU, self.OnSetSoundHotkey, id=ID_SET_SOUND_HOTKEY)
        self.Bind(wx.EVT_MENU, self.OnEditScenarios, id=ID_EDIT_SCENARIOS)
        
        self.Bind(wx.EVT_MENU, self.OnManageBuses, id=ID_MANAGE_BUSES)
        self.Bind(wx.EVT_MENU, self.OnStopBus, id=ID_STOP_BUS)
        self.Bind(wx.EVT_MENU, self.OnStopAll, id=ID_STOP_ALL)
        
        self.Bind(wx.EVT_MENU, self.OnBusVolUp, id=ID_BUS_VOL_UP)
        self.Bind(wx.EVT_MENU, self.OnBusVolDown, id=ID_BUS_VOL_DOWN)
        self.Bind(wx.EVT_MENU, self.OnMasterVolUp, id=ID_MASTER_VOL_UP)
        self.Bind(wx.EVT_MENU, self.OnMasterVolDown, id=ID_MASTER_VOL_DOWN)
        
        self.Bind(wx.EVT_MENU, self.OnAbout, id=wx.ID_ABOUT)
        
        # Bind Ctrl+1..9 Switch Bus
        for i in range(1, 10):
            self.Bind(wx.EVT_MENU, self.OnSwitchBusHotkey, id=ID_BUS_BASE + i)
            
        # Bind Alt+1..9 Play Scenario
        for i in range(1, 10):
            self.Bind(wx.EVT_MENU, self.OnPlayScenarioHotkey, id=ID_SCENARIO_BASE + i)

    def LoadSettings(self):
        sp = wx.StandardPaths.Get()
        user_data_dir = sp.GetUserDataDir()
        os.makedirs(user_data_dir, exist_ok=True)
        settings_path = os.path.join(user_data_dir, "settings.json")
        
        self.settings = {}
        if os.path.exists(settings_path):
            try:
                with open(settings_path, "r", encoding="utf-8") as f:
                    self.settings = json.load(f)
            except Exception:
                pass
                
        if "recent_projects" not in self.settings or not isinstance(self.settings["recent_projects"], list):
            self.settings["recent_projects"] = []
            
        # Clean up missing directories from recent list robustly
        cleaned_recent = []
        for p in self.settings["recent_projects"]:
            if isinstance(p, dict) and "path" in p and p["path"]:
                try:
                    if os.path.exists(p["path"]):
                        cleaned_recent.append(p)
                except Exception:
                    pass
        self.settings["recent_projects"] = cleaned_recent

    def SaveSettings(self):
        sp = wx.StandardPaths.Get()
        user_data_dir = sp.GetUserDataDir()
        settings_path = os.path.join(user_data_dir, "settings.json")
        try:
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def LoadSettingsAndLastProject(self):
        self.LoadSettings()
        project_to_load = self.settings.get("last_project_path")
        
        if project_to_load and os.path.exists(project_to_load):
            self.LoadProject(project_to_load)
        else:
            # Welcome the user and open the Project Selection dashboard
            wx.CallAfter(self.OnManageProjects, None)

    def OnManageProjects(self, event):
        # Open ProjectManagerDialog
        dlg = ui_dialogs.ProjectManagerDialog(
            self,
            self.settings.get("recent_projects", []),
            self.settings.get("last_project_path")
        )
        res = dlg.ShowModal()
        
        # Save modifications to recent projects list
        self.settings["recent_projects"] = dlg.recent_projects
        self.SaveSettings()
        
        if res == wx.ID_OK:
            action = dlg.action
            if action == 'open' and dlg.selected_project_path:
                self.LoadProject(dlg.selected_project_path)
            elif action == 'create':
                self.OnNewProject(None)
            elif action == 'browse':
                self.OnOpenProject(None)
        else:
            # Dialog cancelled or Exit App selected
            if dlg.action == 'exit' or self.project_data is None:
                self.Close()
                
        dlg.Destroy()

    def LoadProject(self, path):
        try:
            self.project_data = project_manager.load_project(path)
            self.project_dir = path
            
            # Setup volumes in audio engine
            self.audio_engine.set_master_volume(self.project_data.get("master_volume", 0.8))
            for bus in self.project_data.get("buses", []):
                self.audio_engine.set_bus_volume(bus["id"], bus.get("volume", 1.0))
                
            # Set audio device if saved
            device_index = self.project_data.get("output_device")
            if device_index is not None:
                self.audio_engine.set_output_device(device_index)
                
            # Select first bus
            if self.project_data["buses"]:
                self.selected_bus_id = self.project_data["buses"][0]["id"]
            else:
                self.selected_bus_id = None
                
            # Refresh lists
            self.RefreshBusesList()
            self.RefreshSoundsList()
            
            # Rebuild keyboard shortcuts (accelerator table)
            self.RebuildAccelerators()
            
            # Update settings
            self.settings["last_project_path"] = path
            recent = self.settings.get("recent_projects", [])
            recent = [p for p in recent if p["path"] != path]
            recent.insert(0, {
                "name": self.project_data.get("name", "Unnamed"),
                "path": path
            })
            self.settings["recent_projects"] = recent
            self.SaveSettings()
            
            Speech.speak(f"Project loaded: {self.project_data.get('name', 'Unnamed')}")
            self.UpdateStatusBar()
            
        except Exception as e:
            wx.MessageBox(f"Failed to load project from {path}:\n{e}", "Error", wx.OK | wx.ICON_ERROR)
            if "recent_projects" in self.settings:
                self.settings["recent_projects"] = [
                    p for p in self.settings["recent_projects"]
                    if p["path"] != path
                ]
            if self.settings.get("last_project_path") == path:
                self.settings["last_project_path"] = None
            self.SaveSettings()
            wx.CallAfter(self.OnManageProjects, None)

    def RefreshBusesList(self):
        self.buses_list.Clear()
        if not self.project_data or not self.project_data.get("buses"):
            return
            
        selected_idx = 0
        for idx, bus in enumerate(self.project_data["buses"]):
            self.buses_list.Append(bus["name"])
            if bus["id"] == self.selected_bus_id:
                selected_idx = idx
                
        if self.buses_list.GetCount() > 0:
            self.buses_list.SetSelection(selected_idx)

    def RefreshSoundsList(self):
        self.sounds_list.DeleteAllItems()
        if not self.project_data or not self.selected_bus_id:
            self.current_bus_sounds = []
            return
            
        # Get sounds for current bus
        self.current_bus_sounds = [
            s for s in self.project_data.get("sounds", [])
            if s.get("bus_id") == self.selected_bus_id
        ]
        
        for idx, sound in enumerate(self.current_bus_sounds):
            self.sounds_list.InsertItem(idx, sound["name"])
            self.sounds_list.SetItem(idx, 1, sound.get("hotkey", ""))
            
            scen_count = len(sound.get("scenarios", []))
            self.sounds_list.SetItem(idx, 2, f"{scen_count} scenarios")
            
            # Associate item with index in current_bus_sounds
            self.sounds_list.SetItemData(idx, idx)

    def RebuildAccelerators(self):
        """Rebuilds the accelerator table, combining standard menu bindings and sound-level hotkeys."""
        self.hotkey_id_map.clear()
        self.bus_hotkey_map.clear()
        
        # Base accelerators from Menu Bar shortcuts
        # Standard wxPython handles Menu Ctrl+N, Ctrl+O, etc. automatically via menu item text shortcut.
        # But we build an explicit AcceleratorTable to make sure Alt+1..9, Escape, and Ctrl+1..9 routing is absolute.
        entries = [
            wx.AcceleratorEntry(wx.ACCEL_CTRL, ord('N'), ID_NEW_PROJECT),
            wx.AcceleratorEntry(wx.ACCEL_CTRL, ord('O'), ID_OPEN_PROJECT),
            wx.AcceleratorEntry(wx.ACCEL_CTRL, ord('S'), ID_SAVE_PROJECT),
            wx.AcceleratorEntry(wx.ACCEL_CTRL, ord('M'), ID_MANAGE_PROJECTS),
            wx.AcceleratorEntry(wx.ACCEL_CTRL, ord('I'), ID_ADD_SOUND),
            wx.AcceleratorEntry(wx.ACCEL_NORMAL, wx.WXK_F2, ID_EDIT_SOUND),
            wx.AcceleratorEntry(wx.ACCEL_NORMAL, wx.WXK_DELETE, ID_REMOVE_SOUND),
            wx.AcceleratorEntry(wx.ACCEL_ALT, ord('K'), ID_SET_SOUND_HOTKEY),
            wx.AcceleratorEntry(wx.ACCEL_CTRL, ord('E'), ID_EDIT_SCENARIOS),
            wx.AcceleratorEntry(wx.ACCEL_CTRL, ord('B'), ID_MANAGE_BUSES),
            wx.AcceleratorEntry(wx.ACCEL_NORMAL, wx.WXK_ESCAPE, ID_STOP_BUS),
            wx.AcceleratorEntry(wx.ACCEL_ALT, wx.WXK_ESCAPE, ID_STOP_ALL),
            
            # Volume shortcuts
            wx.AcceleratorEntry(wx.ACCEL_CTRL, wx.WXK_UP, ID_BUS_VOL_UP),
            wx.AcceleratorEntry(wx.ACCEL_CTRL, wx.WXK_DOWN, ID_BUS_VOL_DOWN),
            wx.AcceleratorEntry(wx.ACCEL_CTRL | wx.ACCEL_SHIFT, wx.WXK_UP, ID_MASTER_VOL_UP),
            wx.AcceleratorEntry(wx.ACCEL_CTRL | wx.ACCEL_SHIFT, wx.WXK_DOWN, ID_MASTER_VOL_DOWN),
        ]
        
        # Ctrl+1..9 entries
        for i in range(1, 10):
            entries.append(wx.AcceleratorEntry(wx.ACCEL_CTRL, ord(str(i)), ID_BUS_BASE + i))
            
        # Alt+1..9 entries
        for i in range(1, 10):
            entries.append(wx.AcceleratorEntry(wx.ACCEL_ALT, ord(str(i)), ID_SCENARIO_BASE + i))
            
        # Dynamic local hotkeys registered on sounds
        if self.project_data:
            for idx, sound in enumerate(self.project_data.get("sounds", [])):
                hotkey_str = sound.get("hotkey", "").strip()
                if hotkey_str:
                    cmd_id = wx.ID_HIGHEST + 300 + idx
                    entry = self.ParseHotkeyToAccel(hotkey_str, cmd_id)
                    if entry:
                        entries.append(entry)
                        self.hotkey_id_map[cmd_id] = sound["id"]
                        self.Bind(wx.EVT_MENU, self.OnDynamicHotkeyTriggered, id=cmd_id)
                        
        # Dynamic bus hotkeys registered on buses
        if self.project_data:
            for idx, bus in enumerate(self.project_data.get("buses", [])):
                hotkey_str = bus.get("hotkey", "").strip()
                if hotkey_str:
                    cmd_id = wx.ID_HIGHEST + 1000 + idx
                    entry = self.ParseHotkeyToAccel(hotkey_str, cmd_id)
                    if entry:
                        entries.append(entry)
                        self.bus_hotkey_map[cmd_id] = bus["id"]
                        self.Bind(wx.EVT_MENU, self.OnBusHotkeyTriggered, id=cmd_id)
                        
        self.SetAcceleratorTable(wx.AcceleratorTable(entries))

    def ParseHotkeyToAccel(self, hotkey_str, cmd_id):
        parts = hotkey_str.split("+")
        flags = wx.ACCEL_NORMAL
        key_code = None
        
        for p in parts:
            p_lower = p.lower()
            if p_lower == "ctrl":
                flags |= wx.ACCEL_CTRL
            elif p_lower == "shift":
                flags |= wx.ACCEL_SHIFT
            elif p_lower == "alt":
                flags |= wx.ACCEL_ALT
            else:
                # Resolve key code
                if p_lower.startswith("f") and p_lower[1:].isdigit():
                    f_num = int(p_lower[1:])
                    if 1 <= f_num <= 12:
                        key_code = wx.WXK_F1 + f_num - 1
                elif p_lower == "space":
                    key_code = wx.WXK_SPACE
                elif p_lower == "enter":
                    key_code = wx.WXK_RETURN
                elif p_lower == "escape":
                    key_code = wx.WXK_ESCAPE
                elif len(p) == 1:
                    key_code = ord(p.upper())
                    
        if key_code is not None:
            return wx.AcceleratorEntry(flags, key_code, cmd_id)
        return None

    def GetSelectedBus(self):
        if not self.project_data or not self.selected_bus_id:
            return None
        for b in self.project_data["buses"]:
            if b["id"] == self.selected_bus_id:
                return b
        return None

    def UpdateStatusBar(self):
        if not self.project_data:
            self.status_bar.SetStatusText("No project loaded", 0)
            self.status_bar.SetStatusText("", 1)
            self.status_bar.SetStatusText("", 2)
            return
            
        bus = self.GetSelectedBus()
        if bus:
            self.status_bar.SetStatusText(f"Bus: {bus['name']} ({bus['mode']})", 0)
            self.status_bar.SetStatusText(f"Bus Vol: {int(bus['volume']*100)}%", 1)
        else:
            self.status_bar.SetStatusText("", 0)
            self.status_bar.SetStatusText("", 1)
            
        count = self.audio_engine.get_active_channels_count() if self.audio_engine else 0
        self.status_bar.SetStatusText(f"Playing: {count}", 2)

    # --- File Menu Handlers ---
    def OnNewProject(self, event):
        dlg = ui_dialogs.NewProjectDialog(self)
        if dlg.ShowModal() == wx.ID_OK:
            proj_name = dlg.GetProjectName()
            proj_path = dlg.GetProjectPath()
            
            try:
                project_manager.create_project(proj_path, proj_name)
                self.LoadProject(proj_path)
            except Exception as e:
                wx.MessageBox(f"Failed to create project:\n{e}", "Error", wx.OK | wx.ICON_ERROR)
        dlg.Destroy()

    def OnOpenProject(self, event):
        dlg = wx.DirDialog(self, "Select Project Folder", style=wx.DD_DEFAULT_STYLE)
        if dlg.ShowModal() == wx.ID_OK:
            self.LoadProject(dlg.GetPath())
        dlg.Destroy()

    def OnSaveProject(self, event):
        if not self.project_data or not self.project_dir:
            return
            
        try:
            project_manager.save_project(self.project_dir, self.project_data)
            Speech.speak("Project saved")
        except Exception as e:
            wx.MessageBox(f"Failed to save project:\n{e}", "Error", wx.OK | wx.ICON_ERROR)

    def OnExportProject(self, event):
        if not self.project_data or not self.project_dir:
            wx.MessageBox("No project loaded to export.", "Error", wx.OK | wx.ICON_ERROR)
            return
            
        dlg = wx.FileDialog(
            self,
            message="Export Project Zip",
            defaultFile=f"{self.project_data.get('name', 'project')}.zip",
            wildcard="Zip files (*.zip)|*.zip",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
        )
        if dlg.ShowModal() == wx.ID_OK:
            zip_path = dlg.GetPath()
            try:
                project_manager.export_project(self.project_dir, zip_path)
                Speech.speak("Project exported successfully")
                wx.MessageBox("Project exported successfully!", "Success", wx.OK | wx.ICON_INFORMATION)
            except Exception as e:
                wx.MessageBox(f"Export failed:\n{e}", "Error", wx.OK | wx.ICON_ERROR)
        dlg.Destroy()

    def OnImportProject(self, event):
        file_dlg = wx.FileDialog(
            self,
            message="Select Project Zip to Import",
            wildcard="Zip files (*.zip)|*.zip",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        )
        if file_dlg.ShowModal() != wx.ID_OK:
            file_dlg.Destroy()
            return
            
        zip_path = file_dlg.GetPath()
        file_dlg.Destroy()
        
        dir_dlg = wx.DirDialog(
            self,
            "Select destination directory to extract the project",
            style=wx.DD_DEFAULT_STYLE
        )
        if dir_dlg.ShowModal() != wx.ID_OK:
            dir_dlg.Destroy()
            return
            
        dest_parent = dir_dlg.GetPath()
        dir_dlg.Destroy()
        
        # We will extract it in a subfolder named after the zip base name
        zip_base = os.path.splitext(os.path.basename(zip_path))[0]
        dest_dir = os.path.join(dest_parent, zip_base)
        
        try:
            project_manager.import_project(zip_path, dest_dir)
            self.LoadProject(dest_dir)
        except Exception as e:
            wx.MessageBox(f"Import failed:\n{e}", "Error", wx.OK | wx.ICON_ERROR)

    def OnPreferences(self, event):
        if not self.audio_engine:
            return
            
        devices = self.audio_engine.get_output_devices()
        curr_device = self.audio_engine._device_index
        curr_volume = self.audio_engine._master_volume
        
        dlg = ui_dialogs.PreferencesDialog(self, devices, curr_device, curr_volume)
        if dlg.ShowModal() == wx.ID_OK:
            new_device = dlg.GetSelectedDeviceIndex()
            new_vol = dlg.GetMasterVolume()
            
            # Apply device change
            if new_device != curr_device:
                self.audio_engine.set_output_device(new_device)
                if self.project_data:
                    self.project_data["output_device"] = new_device
                    
            # Apply volume change
            self.audio_engine.set_master_volume(new_vol)
            if self.project_data:
                self.project_data["master_volume"] = new_vol
                
            if self.project_data:
                project_manager.save_project(self.project_dir, self.project_data)
                
            Speech.speak(f"Preferences saved. Master volume set to {int(new_vol * 100)} percent.")
            self.UpdateStatusBar()
        dlg.Destroy()

    def OnExit(self, event):
        self.Close()

    # --- Edit Menu Handlers ---
    def OnAddSound(self, event):
        if not self.project_data:
            wx.MessageBox("Please create or open a project first.", "Error", wx.OK | wx.ICON_ERROR)
            return
            
        dlg = ui_dialogs.AddEditSoundDialog(self, self.project_data["buses"], existing_sounds=self.project_data["sounds"])
        if dlg.ShowModal() == wx.ID_OK:
            sound_data = dlg.GetSoundData()
            filepath_full = sound_data.pop("filepath_full")
            
            try:
                # Copy sound to project directory
                rel_filename = project_manager.import_sound(self.project_dir, filepath_full)
                sound_data["filename"] = rel_filename
                
                # Append sound to project metadata
                self.project_data["sounds"].append(sound_data)
                project_manager.save_project(self.project_dir, self.project_data)
                
                self.RefreshSoundsList()
                self.RebuildAccelerators()
                Speech.speak(f"Added {sound_data['name']}")
            except Exception as e:
                wx.MessageBox(f"Failed to import sound:\n{e}", "Error", wx.OK | wx.ICON_ERROR)
        dlg.Destroy()

    def OnEditSound(self, event):
        if not self.project_data:
            return
            
        sel = self.sounds_list.GetFirstSelected()
        if sel == wx.NOT_FOUND:
            Speech.speak("No sound selected to edit")
            return
            
        sound_idx = self.sounds_list.GetItemData(sel)
        sound = self.current_bus_sounds[sound_idx]
        
        # Find index in global sounds list
        global_sound_idx = self.project_data["sounds"].index(sound)
        
        # Format the relative file path to full path for display
        sounds_dir = os.path.join(self.project_dir, "sounds")
        full_filepath = os.path.join(sounds_dir, sound["filename"])
        
        # Prepare a temporary sound data dictionary with absolute path
        temp_sound = sound.copy()
        temp_sound["filename"] = full_filepath
        
        dlg = ui_dialogs.AddEditSoundDialog(self, self.project_data["buses"], temp_sound, existing_sounds=self.project_data["sounds"])
        if dlg.ShowModal() == wx.ID_OK:
            updated_data = dlg.GetSoundData()
            filepath_full = updated_data.pop("filepath_full")
            
            try:
                # If they picker-selected a new file
                if filepath_full and filepath_full != full_filepath:
                    rel_filename = project_manager.import_sound(self.project_dir, filepath_full)
                    updated_data["filename"] = rel_filename
                else:
                    # Keep original filename
                    updated_data["filename"] = sound["filename"]
                    
                # Update in project
                self.project_data["sounds"][global_sound_idx] = updated_data
                project_manager.save_project(self.project_dir, self.project_data)
                
                self.RefreshSoundsList()
                self.RebuildAccelerators()
                Speech.speak(f"Updated {updated_data['name']}")
            except Exception as e:
                wx.MessageBox(f"Failed to update sound:\n{e}", "Error", wx.OK | wx.ICON_ERROR)
        dlg.Destroy()

    def OnSetSoundHotkey(self, event):
        if not self.project_data:
            return
            
        sel = self.sounds_list.GetFirstSelected()
        if sel == wx.NOT_FOUND:
            Speech.speak("No sound selected to set hotkey")
            return
            
        sound_idx = self.sounds_list.GetItemData(sel)
        sound = self.current_bus_sounds[sound_idx]
        
        dlg = ui_dialogs.QuickHotkeyDialog(self, sound["name"], sound.get("hotkey", ""))
        if dlg.ShowModal() == wx.ID_OK:
            new_hotkey = dlg.GetValue()
            
            # Check for conflict
            conflict = False
            if new_hotkey:
                # Check other sounds
                for s in self.project_data["sounds"]:
                    if s["id"] != sound["id"] and s.get("hotkey", "").strip().lower() == new_hotkey.lower():
                        wx.MessageBox(
                            f"The hotkey '{new_hotkey}' is already assigned to the sound '{s['name']}'.",
                            "Hotkey Conflict", wx.OK | wx.ICON_WARNING
                        )
                        conflict = True
                        break
                # Check buses
                if not conflict:
                    for b in self.project_data["buses"]:
                        if b.get("hotkey", "").strip().lower() == new_hotkey.lower():
                            wx.MessageBox(
                                f"The hotkey '{new_hotkey}' is already assigned to the bus '{b['name']}'.",
                                "Hotkey Conflict", wx.OK | wx.ICON_WARNING
                            )
                            conflict = True
                            break
            if not conflict:
                sound["hotkey"] = new_hotkey
                project_manager.save_project(self.project_dir, self.project_data)
                self.RefreshSoundsList()
                self.RebuildAccelerators()
                Speech.speak(f"Hotkey for {sound['name']} set to {new_hotkey if new_hotkey else 'none'}")
        dlg.Destroy()

    def OnRemoveSound(self, event):
        if not self.project_data:
            return
            
        sel = self.sounds_list.GetFirstSelected()
        if sel == wx.NOT_FOUND:
            Speech.speak("No sound selected to remove")
            return
            
        sound_idx = self.sounds_list.GetItemData(sel)
        sound = self.current_bus_sounds[sound_idx]
        
        confirm = wx.MessageBox(
            f"Are you sure you want to remove the sound '{sound['name']}'?",
            "Confirm Delete",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING
        )
        if confirm == wx.YES:
            global_sound_idx = self.project_data["sounds"].index(sound)
            self.project_data["sounds"].pop(global_sound_idx)
            
            project_manager.save_project(self.project_dir, self.project_data)
            self.RefreshSoundsList()
            self.RebuildAccelerators()
            Speech.speak(f"Removed {sound['name']}")

    def OnEditScenarios(self, event):
        if not self.project_data:
            return
            
        sel = self.sounds_list.GetFirstSelected()
        if sel == wx.NOT_FOUND:
            Speech.speak("No sound selected to edit scenarios")
            return
            
        sound_idx = self.sounds_list.GetItemData(sel)
        sound = self.current_bus_sounds[sound_idx]
        
        dlg = ui_dialogs.EditScenariosDialog(self, self.project_data["buses"], sound)
        dlg.ShowModal()
        dlg.Destroy()
        
        # Save project since scenarios dialog mutates sound directly
        project_manager.save_project(self.project_dir, self.project_data)
        self.RefreshSoundsList()

    # --- Buses Menu Handlers ---
    def OnManageBuses(self, event):
        if not self.project_data:
            return
            
        dlg = ui_dialogs.ManageBusesDialog(self, self.project_data)
        dlg.ShowModal()
        dlg.Destroy()
        
        # Save changes
        project_manager.save_project(self.project_dir, self.project_data)
        
        # Update audio engine bus volumes
        for bus in self.project_data["buses"]:
            self.audio_engine.set_bus_volume(bus["id"], bus.get("volume", 1.0))
            
        # Verify selected bus still exists
        bus_ids = [b["id"] for b in self.project_data["buses"]]
        if self.selected_bus_id not in bus_ids:
            self.selected_bus_id = bus_ids[0]
            
        self.RefreshBusesList()
        self.RefreshSoundsList()
        self.RebuildAccelerators()
        self.UpdateStatusBar()

    def OnStopBus(self, event):
        if not self.selected_bus_id or not self.audio_engine:
            return
        bus = self.GetSelectedBus()
        if bus:
            # Immediately deactivate the playlist loop for this bus
            if self.selected_bus_id in self.active_bus_playlists:
                self.active_bus_playlists[self.selected_bus_id]["active"] = False
            self.audio_engine.stop_bus(self.selected_bus_id)
            Speech.speak(f"Stopped {bus['name']}")

    def OnStopAll(self, event):
        if self.audio_engine:
            # Immediately deactivate all playlist loops
            for playlist in self.active_bus_playlists.values():
                playlist["active"] = False
            self.audio_engine.stop_all()
            Speech.speak("All sounds stopped")

    # --- Bus Navigation and Shortcut Selection ---
    def OnBusSelected(self, event):
        """Triggered when the user clicks or arrows to a different bus in the ListBox."""
        sel = self.buses_list.GetSelection()
        if sel != wx.NOT_FOUND:
            bus = self.project_data["buses"][sel]
            self.selected_bus_id = bus["id"]
            self.RefreshSoundsList()
            self.UpdateStatusBar()
            Speech.speak(f"Bus: {bus['name']}, {bus['mode']}")

    def OnSwitchBusHotkey(self, event):
        """Triggered via Ctrl+1..9. Switches the selected bus and auto-focuses the Sounds list."""
        bus_index = event.GetId() - ID_BUS_BASE - 1
        if self.project_data and 0 <= bus_index < len(self.project_data["buses"]):
            bus = self.project_data["buses"][bus_index]
            self.selected_bus_id = bus["id"]
            self.RefreshBusesList()
            self.RefreshSoundsList()
            self.UpdateStatusBar()
            Speech.speak(f"Bus: {bus['name']}, {bus['mode']}")
            self.sounds_list.SetFocus()
            # Select first item in sounds list if populated
            if self.sounds_list.GetItemCount() > 0:
                self.sounds_list.Select(0)
                self.sounds_list.Focus(0)

    # --- Sound Activation & Playback ---
    def OnSoundActivated(self, event):
        """Triggered when user hits Enter on a sounds list item."""
        self.PlaySelectedSound()

    def OnSoundsListKeyDown(self, event):
        """Intercepts Space key to play sound, or routes other keys."""
        key_code = event.GetKeyCode()
        if key_code == wx.WXK_SPACE:
            self.PlaySelectedSound()
        else:
            event.Skip()

    def PlaySelectedSound(self):
        sel = self.sounds_list.GetFirstSelected()
        if sel == wx.NOT_FOUND:
            return
            
        sound_idx = self.sounds_list.GetItemData(sel)
        sound = self.current_bus_sounds[sound_idx]
        
        # Play using default scenario settings
        self.PlaySound(sound, sound["default_scenario"])

    def OnPlayScenarioHotkey(self, event):
        """Triggered via Alt+1..9. Plays selected sound with the specific scenario override."""
        sel = self.sounds_list.GetFirstSelected()
        if sel == wx.NOT_FOUND:
            Speech.speak("No sound selected")
            return
            
        sound_idx = self.sounds_list.GetItemData(sel)
        sound = self.current_bus_sounds[sound_idx]
        
        scenario_idx = event.GetId() - ID_SCENARIO_BASE - 1
        scenarios = sound.get("scenarios", [])
        
        if 0 <= scenario_idx < len(scenarios):
            scenario = scenarios[scenario_idx]
            self.PlaySound(sound, scenario, scenario.get("name"))
        else:
            Speech.speak(f"Scenario {scenario_idx + 1} not defined for this sound")

    def OnDynamicHotkeyTriggered(self, event):
        """Triggered via dynamic local hotkeys (e.g. F1..F12). Plays the bound sound."""
        sound_id = self.hotkey_id_map.get(event.GetId())
        if not sound_id or not self.project_data:
            return
            
        # Find the sound object
        target_sound = None
        for s in self.project_data["sounds"]:
            if s["id"] == sound_id:
                target_sound = s
                break
                
        if target_sound:
            # Check if missing
            if target_sound.get("missing"):
                Speech.speak(f"Cannot play {target_sound['name']}: file is missing.")
                return
            self.PlaySound(target_sound, target_sound["default_scenario"])

    def PlaySound(self, sound, scenario, scenario_name=None):
        if sound.get("missing"):
            Speech.speak(f"Cannot play {sound['name']}: file is missing.")
            return None
            
        sounds_dir = os.path.join(self.project_dir, "sounds")
        filepath = os.path.join(sounds_dir, sound["filename"])
        
        # Determine bus mode
        bus_id = scenario.get("bus_id") or sound["bus_id"]
        bus_mode = "layered"
        for b in self.project_data["buses"]:
            if b["id"] == bus_id:
                bus_mode = b["mode"]
                break
                
        try:
            ch = self.audio_engine.play(filepath, scenario, bus_id, bus_mode, sound_name=sound["name"])
            self.UpdateStatusBar()
            return ch
        except Exception as e:
            Speech.speak(f"Error: Playback failed for {sound['name']}")
            print(f"Playback failed: {e}")
            return None

    # --- Volume Adjustment Handlers ---
    def OnBusVolUp(self, event):
        bus = self.GetSelectedBus()
        if bus:
            new_vol = min(1.0, bus.get("volume", 1.0) + 0.05)
            bus["volume"] = new_vol
            self.audio_engine.set_bus_volume(bus["id"], new_vol)
            project_manager.save_project(self.project_dir, self.project_data)
            self.UpdateStatusBar()
            Speech.speak(f"Volume {int(new_vol * 100)} percent")

    def OnBusVolDown(self, event):
        bus = self.GetSelectedBus()
        if bus:
            new_vol = max(0.0, bus.get("volume", 1.0) - 0.05)
            bus["volume"] = new_vol
            self.audio_engine.set_bus_volume(bus["id"], new_vol)
            project_manager.save_project(self.project_dir, self.project_data)
            self.UpdateStatusBar()
            Speech.speak(f"Volume {int(new_vol * 100)} percent")

    def OnMasterVolUp(self, event):
        if self.project_data:
            new_vol = min(1.0, self.project_data.get("master_volume", 0.8) + 0.05)
            self.project_data["master_volume"] = new_vol
            self.audio_engine.set_master_volume(new_vol)
            project_manager.save_project(self.project_dir, self.project_data)
            self.UpdateStatusBar()
            Speech.speak(f"Master volume {int(new_vol * 100)} percent")

    def OnMasterVolDown(self, event):
        if self.project_data:
            new_vol = max(0.0, self.project_data.get("master_volume", 0.8) - 0.05)
            self.project_data["master_volume"] = new_vol
            self.audio_engine.set_master_volume(new_vol)
            project_manager.save_project(self.project_dir, self.project_data)
            self.UpdateStatusBar()
            Speech.speak(f"Master volume {int(new_vol * 100)} percent")

    def OnCleanupTimer(self, event):
        """Runs regularly to clean up done streams and keep active stream counts updated in the status bar."""
        if self.audio_engine:
            done_channels = self.audio_engine.cleanup_done_channels()
            if done_channels:
                self.UpdateStatusBar()
                
                # Check if any finished channels belong to our active playlists
                for ch in done_channels:
                    for bus_id, playlist in list(self.active_bus_playlists.items()):
                        if playlist["active"] and playlist.get("current_channel") == ch:
                            # This channel belongs to the active playlist of bus_id.
                            # Was it stopped manually or did it finish naturally?
                            if ch._fading_out:
                                # Stopped manually! Terminate the loop.
                                playlist["active"] = False
                                bus = self.GetBusById(bus_id)
                                Speech.speak(f"Stopped playlist for bus {bus['name'] if bus else 'unknown'}")
                            else:
                                # Finished naturally! Proceed to next track.
                                self.PlayNextSoundInBusPlaylist(bus_id)

    def GetBusById(self, bus_id):
        if not self.project_data:
            return None
        for b in self.project_data.get("buses", []):
            if b["id"] == bus_id:
                return b
        return None

    def OnBusHotkeyTriggered(self, event):
        """Triggered via dynamic bus hotkeys. Toggles the shuffled looping playlist for the bus."""
        bus_id = self.bus_hotkey_map.get(event.GetId())
        if not bus_id or not self.project_data:
            return
        self.ToggleBusPlaylist(bus_id)

    def ToggleBusPlaylist(self, bus_id):
        bus = self.GetBusById(bus_id)
        if not bus:
            return
            
        playlist = self.active_bus_playlists.get(bus_id)
        if playlist and playlist["active"]:
            playlist["active"] = False
            self.audio_engine.stop_bus(bus_id)
            Speech.speak(f"Stopped playlist for bus {bus['name']}")
        else:
            # Gather all non-missing sounds belonging to this bus
            sounds = [s for s in self.project_data.get("sounds", []) if s.get("bus_id") == bus_id and not s.get("missing")]
            if not sounds:
                Speech.speak(f"No sounds in bus {bus['name']} to play.")
                return
                
            # Stop any existing playback on this bus first
            self.audio_engine.stop_bus(bus_id)
            
            # Shuffle and build the queue
            import random
            shuffled_sounds = list(sounds)
            random.shuffle(shuffled_sounds)
            
            # Start the first sound
            sound = shuffled_sounds[0]
            ch = self.PlaySound(sound, sound["default_scenario"])
            if ch:
                self.active_bus_playlists[bus_id] = {
                    "shuffled_sounds": shuffled_sounds,
                    "index": 0,
                    "current_channel": ch,
                    "active": True
                }
                Speech.speak(f"Starting playlist for bus {bus['name']}. Playing {sound['name']}.")
            else:
                Speech.speak(f"Failed to play first sound in playlist for bus {bus['name']}.")

    def PlayNextSoundInBusPlaylist(self, bus_id):
        playlist = self.active_bus_playlists.get(bus_id)
        if not playlist or not playlist["active"]:
            return
            
        shuffled_sounds = playlist["shuffled_sounds"]
        idx = playlist["index"] + 1
        
        # If we reached the end of the queue, reshuffle and start over
        if idx >= len(shuffled_sounds):
            import random
            random.shuffle(shuffled_sounds)
            idx = 0
            
        playlist["index"] = idx
        sound = shuffled_sounds[idx]
        
        bus = self.GetBusById(bus_id)
        # Play next sound
        ch = self.PlaySound(sound, sound["default_scenario"])
        if ch:
            playlist["current_channel"] = ch
            Speech.speak(f"Playing next: {sound['name']}")
        else:
            playlist["active"] = False
            Speech.speak(f"Failed to play next sound {sound['name']}. Playlist stopped.")

    # --- Help & About Dialog ---
    def OnAbout(self, event):
        wx.MessageBox(
            f"OklyPlay Soundboard\nVersion {__version__}\n\nA screenreader-accessible soundboard for streamers.\n"
            "Built with wxPython, sounddevice, soundfile, numpy, and accessible_output2.",
            "About OklyPlay",
            wx.OK | wx.ICON_INFORMATION
        )

    # --- Application Shutdown ---
    def OnClose(self, event):
        # Stop and clean up audio engine
        if self.audio_engine:
            self.audio_engine.close()
        self.cleanup_timer.Stop()
        event.Skip()
