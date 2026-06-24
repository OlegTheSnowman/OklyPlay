import wx
import os
import uuid

def create_dialog_buttons(panel, ok_label="OK", cancel_label="Cancel"):
    """Creates OK and Cancel buttons with the panel as their parent to avoid sizer parent assert."""
    btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
    ok_btn = wx.Button(panel, wx.ID_OK, ok_label)
    cancel_btn = wx.Button(panel, wx.ID_CANCEL, cancel_label)
    btn_sizer.Add(ok_btn, 0, wx.ALL, 5)
    btn_sizer.Add(cancel_btn, 0, wx.ALL, 5)
    return btn_sizer, ok_btn, cancel_btn

class AccessibleName(wx.Accessible):
    def __init__(self, window, name):
        super().__init__(window)
        self.name = name

    def GetName(self, childId):
        return wx.ACC_OK, self.name

def label_control(control, name):
    control.SetName(name)
    acc = AccessibleName(control, name)
    control.SetAccessible(acc)
    control._accessible_obj = acc
    
    # Also label the internal Edit/Text child for spin controls
    if isinstance(control, (wx.SpinCtrl, wx.SpinCtrlDouble)):
        # 1. Try wxPython children first (works for wx.SpinCtrlDouble)
        labeled_child = False
        for child in control.GetChildren():
            if isinstance(child, wx.TextCtrl):
                child.SetName(name)
                child_acc = AccessibleName(child, name)
                child.SetAccessible(child_acc)
                # Keep it alive by storing on the parent control
                control._accessible_child_obj = child_acc
                labeled_child = True
                break
                
        # 2. Try Win32 sibling HWND (works for wx.SpinCtrl on Windows)
        if not labeled_child:
            try:
                import ctypes
                hwnd = control.GetHandle()
                if hwnd:
                    # GW_HWNDPREV = 3
                    prev_hwnd = ctypes.windll.user32.GetWindow(hwnd, 3)
                    if prev_hwnd:
                        buf = ctypes.create_unicode_buffer(100)
                        ctypes.windll.user32.GetClassNameW(prev_hwnd, buf, 100)
                        if buf.value == "Edit":
                            child_win = wx.Window()
                            child_win.AssociateHandle(prev_hwnd)
                            child_win.SetName(name)
                            child_acc = AccessibleName(child_win, name)
                            child_win.SetAccessible(child_acc)
                            # Keep it alive by storing on the parent control
                            control._accessible_sibling_obj = child_acc
                            control._accessible_sibling_win = child_win
            except Exception:
                pass

class HotkeyCtrl(wx.TextCtrl):
    """Custom TextCtrl that captures keypresses and formats them as hotkey strings."""
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.hotkey_value = ""
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)

    def OnKeyDown(self, event):
        key_code = event.GetKeyCode()
        modifiers = event.GetModifiers()

        # Allow Tab and Shift+Tab to navigate out of the control
        if key_code == wx.WXK_TAB:
            event.Skip()
            return

        # Ignore modifier-only keypresses
        if key_code in (wx.WXK_CONTROL, wx.WXK_SHIFT, wx.WXK_ALT, wx.WXK_WINDOWS_LEFT, wx.WXK_WINDOWS_RIGHT, wx.WXK_WINDOWS_MENU):
            event.Skip()
            return

        # Build hotkey string (e.g. "Ctrl+Alt+F5", "Shift+A", "Space")
        parts = []
        if modifiers & wx.MOD_CONTROL:
            parts.append("Ctrl")
        if modifiers & wx.MOD_SHIFT:
            parts.append("Shift")
        if modifiers & wx.MOD_ALT:
            parts.append("Alt")

        key_name = ""
        if wx.WXK_F1 <= key_code <= wx.WXK_F12:
            key_name = f"F{key_code - wx.WXK_F1 + 1}"
        elif key_code == wx.WXK_SPACE:
            key_name = "Space"
        elif key_code == wx.WXK_RETURN:
            key_name = "Enter"
        elif key_code == wx.WXK_ESCAPE:
            key_name = "Escape"
        elif 32 <= key_code < 127:
            key_name = chr(key_code).upper()

        if key_name:
            parts.append(key_name)
            self.hotkey_value = "+".join(parts)
            self.SetValue(self.hotkey_value)
        else:
            # Backspace or Delete clears the hotkey
            if key_code in (wx.WXK_BACK, wx.WXK_DELETE):
                self.hotkey_value = ""
                self.SetValue("")
            else:
                event.Skip()


class NewProjectDialog(wx.Dialog):
    """Dialog to create a new project with Name and Path fields."""
    def __init__(self, parent):
        super().__init__(parent, title="New Project", size=(450, 220))
        
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Grid Sizer for form
        grid = wx.FlexGridSizer(0, 2, 10, 10)
        grid.AddGrowableCol(1, 1)
        
        # Name field
        name_lbl = wx.StaticText(panel, label="Project Name:")
        self.name_txt = wx.TextCtrl(panel)
        label_control(self.name_txt, "Project Name")
        grid.Add(name_lbl, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.name_txt, 1, wx.EXPAND)
        
        # Location field
        loc_lbl = wx.StaticText(panel, label="Location:")
        loc_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.loc_txt = wx.TextCtrl(panel)
        label_control(self.loc_txt, "Project Location")
        self.browse_btn = wx.Button(panel, label="&Browse...")
        label_control(self.browse_btn, "Browse Project Location")
        loc_sizer.Add(self.loc_txt, 1, wx.EXPAND | wx.RIGHT, 5)
        loc_sizer.Add(self.browse_btn, 0)
        grid.Add(loc_lbl, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(loc_sizer, 1, wx.EXPAND)
        self.browse_btn.Bind(wx.EVT_BUTTON, self.OnBrowse)
        
        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        panel_sizer.Add(grid, 1, wx.EXPAND | wx.ALL, 15)
        
        # Standard buttons
        btn_sizer, ok_btn, cancel_btn = create_dialog_buttons(panel, ok_label="Create")
        ok_btn.Bind(wx.EVT_BUTTON, self.OnOK)
            
        panel_sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.BOTTOM | wx.RIGHT, 15)
        panel.SetSizer(panel_sizer)
        
        main_sizer.Add(panel, 1, wx.EXPAND)
        self.SetSizer(main_sizer)
        self.name_txt.SetFocus()  # Set focus on first field
        self.CenterOnParent()

    def OnOK(self, event):
        name = self.name_txt.GetValue().strip()
        path = self.loc_txt.GetValue().strip()
        
        if not name:
            wx.MessageBox("Project name cannot be empty.", "Error", wx.OK | wx.ICON_ERROR)
            self.name_txt.SetFocus()
            return
            
        if not path or not os.path.isdir(path):
            wx.MessageBox("Please select a valid directory path.", "Error", wx.OK | wx.ICON_ERROR)
            self.loc_txt.SetFocus()
            return
            
        event.Skip()  # Continue standard dialog dismissal

    def OnBrowse(self, event):
        default_path = self.loc_txt.GetValue().strip()
        if not default_path or not os.path.exists(default_path):
            default_path = os.path.expanduser("~")
        dlg = wx.DirDialog(self, "Choose project location", defaultPath=default_path, style=wx.DD_DEFAULT_STYLE)
        if dlg.ShowModal() == wx.ID_OK:
            self.loc_txt.SetValue(dlg.GetPath())
        dlg.Destroy()

    def GetProjectName(self):
        return self.name_txt.GetValue().strip()

    def GetProjectPath(self):
        return os.path.join(self.loc_txt.GetValue().strip(), self.name_txt.GetValue().strip())


class PreferencesDialog(wx.Dialog):
    """Dialog to configure output device and master volume."""
    def __init__(self, parent, devices, current_device_index, current_volume):
        super().__init__(parent, title="Preferences", size=(400, 220))
        
        panel = wx.Panel(self)
        grid = wx.FlexGridSizer(0, 2, 12, 10)
        grid.AddGrowableCol(1, 1)
        
        # Output device choice
        device_lbl = wx.StaticText(panel, label="Audio Output Device:")
        self.devices = devices  # List of (index, name)
        device_names = [d[1] for d in devices]
        self.device_choice = wx.Choice(panel, choices=device_names)
        label_control(self.device_choice, "Audio Output Device")
        grid.Add(device_lbl, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.device_choice, 1, wx.EXPAND)
        
        # Set selection
        selected_idx = 0
        for i, (idx, name) in enumerate(devices):
            if idx == current_device_index:
                selected_idx = i
                break
        if device_names:
            self.device_choice.SetSelection(selected_idx)
            
        # Master volume slider
        vol_lbl = wx.StaticText(panel, label="Master Volume:")
        self.vol_slider = wx.Slider(panel, value=int(current_volume * 100), minValue=0, maxValue=100, style=wx.SL_HORIZONTAL | wx.SL_LABELS)
        label_control(self.vol_slider, "Master Volume")
        grid.Add(vol_lbl, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.vol_slider, 1, wx.EXPAND)
        
        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        panel_sizer.Add(grid, 1, wx.EXPAND | wx.ALL, 15)
        
        # Buttons
        btn_sizer, ok_btn, cancel_btn = create_dialog_buttons(panel)
        panel_sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.BOTTOM | wx.RIGHT, 15)
        panel.SetSizer(panel_sizer)
        
        self.device_choice.SetFocus()  # Set focus on first field
        self.CenterOnParent()

    def GetSelectedDeviceIndex(self):
        sel = self.device_choice.GetSelection()
        if sel != wx.NOT_FOUND and sel < len(self.devices):
            return self.devices[sel][0]
        return None

    def GetMasterVolume(self):
        return self.vol_slider.GetValue() / 100.0


class AddEditSoundDialog(wx.Dialog):
    """Dialog to add or edit sound properties (name, file, bus, hotkey, volume, fade, speed, loop)."""
    def __init__(self, parent, buses, sound_data=None, existing_sounds=None):
        title = "Edit Sound" if sound_data else "Add Sound"
        super().__init__(parent, title=title, size=(500, 480))
        
        self.buses = buses  # List of dicts (id, name)
        self.sound_data = sound_data
        self.existing_sounds = existing_sounds
        
        panel = wx.Panel(self)
        grid = wx.FlexGridSizer(0, 2, 10, 10)
        grid.AddGrowableCol(1, 1)
        
        # Name field
        grid.Add(wx.StaticText(panel, label="Name:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.name_txt = wx.TextCtrl(panel)
        label_control(self.name_txt, "Sound Name")
        grid.Add(self.name_txt, 1, wx.EXPAND)
        
        # File field
        grid.Add(wx.StaticText(panel, label="Audio File:"), 0, wx.ALIGN_CENTER_VERTICAL)
        file_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.file_txt = wx.TextCtrl(panel)
        label_control(self.file_txt, "Audio File Path")
        self.file_browse_btn = wx.Button(panel, label="&Browse...")
        label_control(self.file_browse_btn, "Browse Audio File")
        file_sizer.Add(self.file_txt, 1, wx.EXPAND | wx.RIGHT, 5)
        file_sizer.Add(self.file_browse_btn, 0)
        grid.Add(file_sizer, 1, wx.EXPAND)
        self.file_browse_btn.Bind(wx.EVT_BUTTON, self.OnBrowseFile)
        
        # Bus choice
        grid.Add(wx.StaticText(panel, label="Bus Assignment:"), 0, wx.ALIGN_CENTER_VERTICAL)
        bus_names = [b["name"] for b in buses]
        self.bus_choice = wx.Choice(panel, choices=bus_names)
        label_control(self.bus_choice, "Bus Assignment")
        grid.Add(self.bus_choice, 1, wx.EXPAND)
        if bus_names:
            self.bus_choice.SetSelection(0)
            
        # Hotkey field
        grid.Add(wx.StaticText(panel, label="Hotkey:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.hotkey_txt = HotkeyCtrl(panel)
        label_control(self.hotkey_txt, "Hotkey Assignment")
        grid.Add(self.hotkey_txt, 1, wx.EXPAND)
        
        # Volume slider
        grid.Add(wx.StaticText(panel, label="Volume:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.vol_slider = wx.Slider(panel, value=100, minValue=0, maxValue=100, style=wx.SL_HORIZONTAL | wx.SL_LABELS)
        label_control(self.vol_slider, "Volume")
        grid.Add(self.vol_slider, 1, wx.EXPAND)
        
        # Fade In spin
        grid.Add(wx.StaticText(panel, label="Fade In (ms):"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.fade_in_spin = wx.SpinCtrl(panel, min=0, max=10000, initial=0)
        label_control(self.fade_in_spin, "Fade In Milliseconds")
        grid.Add(self.fade_in_spin, 1, wx.EXPAND)
        
        # Fade Out spin
        grid.Add(wx.StaticText(panel, label="Fade Out (ms):"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.fade_out_spin = wx.SpinCtrl(panel, min=0, max=10000, initial=0)
        label_control(self.fade_out_spin, "Fade Out Milliseconds")
        grid.Add(self.fade_out_spin, 1, wx.EXPAND)
        
        # Speed double spin
        grid.Add(wx.StaticText(panel, label="Playback Speed:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.speed_spin = wx.SpinCtrlDouble(panel, min=0.1, max=3.0, initial=1.0, inc=0.1)
        label_control(self.speed_spin, "Playback Speed Multiplier")
        grid.Add(self.speed_spin, 1, wx.EXPAND)
        
        # Loop checkbox
        grid.Add(wx.StaticText(panel, label=""), 0, wx.ALIGN_CENTER_VERTICAL)
        self.loop_chk = wx.CheckBox(panel, label="Loop Audio")
        label_control(self.loop_chk, "Loop Audio")
        grid.Add(self.loop_chk, 1, wx.EXPAND)
        
        # Populate if editing
        if sound_data:
            self.name_txt.SetValue(sound_data.get("name", ""))
            
            # Show filename or path
            filename = sound_data.get("filename", "")
            self.file_txt.SetValue(filename)
            
            # Select bus
            sound_bus_id = sound_data.get("bus_id")
            for i, b in enumerate(buses):
                if b["id"] == sound_bus_id:
                    self.bus_choice.SetSelection(i)
                    break
                    
            self.hotkey_txt.SetValue(sound_data.get("hotkey", ""))
            
            # Default scenario values
            default_scen = sound_data.get("default_scenario", {})
            self.vol_slider.SetValue(int(default_scen.get("volume", 1.0) * 100))
            self.fade_in_spin.SetValue(default_scen.get("fade_in_ms", 0))
            self.fade_out_spin.SetValue(default_scen.get("fade_out_ms", 0))
            self.speed_spin.SetValue(default_scen.get("speed", 1.0))
            self.loop_chk.SetValue(default_scen.get("loop", False))
            
        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        panel_sizer.Add(grid, 1, wx.EXPAND | wx.ALL, 15)
        
        # Buttons
        btn_sizer, ok_btn, cancel_btn = create_dialog_buttons(panel)
        ok_btn.Bind(wx.EVT_BUTTON, self.OnOK)
            
        panel_sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.BOTTOM | wx.RIGHT, 15)
        panel.SetSizer(panel_sizer)
        
        self.name_txt.SetFocus()  # Set focus on first field
        self.CenterOnParent()

    def OnOK(self, event):
        name = self.name_txt.GetValue().strip()
        filepath = self.file_txt.GetValue().strip()
        hotkey = self.hotkey_txt.GetValue().strip()
        
        if not name:
            wx.MessageBox("Sound name cannot be empty.", "Error", wx.OK | wx.ICON_ERROR)
            self.name_txt.SetFocus()
            return
            
        if not filepath:
            wx.MessageBox("Please select an audio file.", "Error", wx.OK | wx.ICON_ERROR)
            self.file_txt.SetFocus()
            return
            
        if hotkey and self.existing_sounds:
            my_id = self.sound_data.get("id") if self.sound_data else None
            for s in self.existing_sounds:
                if s.get("id") != my_id and s.get("hotkey", "").strip().lower() == hotkey.lower():
                    wx.MessageBox(
                        f"The hotkey '{hotkey}' is already assigned to the sound '{s['name']}'.\n"
                        "Please choose a different hotkey.",
                        "Hotkey Conflict",
                        wx.OK | wx.ICON_ERROR
                    )
                    self.hotkey_txt.SetFocus()
                    return
            
        event.Skip()

    def OnBrowseFile(self, event):
        default_file = self.file_txt.GetValue().strip()
        default_dir = ""
        if default_file and os.path.exists(os.path.dirname(default_file)):
            default_dir = os.path.dirname(default_file)
        dlg = wx.FileDialog(
            self,
            message="Select Audio File",
            defaultDir=default_dir,
            wildcard="Audio files (*.mp3;*.wav;*.ogg;*.flac;*.aiff)|*.mp3;*.wav;*.ogg;*.flac;*.aiff",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        )
        if dlg.ShowModal() == wx.ID_OK:
            self.file_txt.SetValue(dlg.GetPath())
        dlg.Destroy()

    def GetSoundData(self):
        """Returns the updated sound metadata dictionary."""
        bus_idx = self.bus_choice.GetSelection()
        bus_id = self.buses[bus_idx]["id"] if bus_idx != wx.NOT_FOUND else ""
        
        sound_id = self.sound_data.get("id") if self.sound_data else str(uuid.uuid4())
        
        scenarios = self.sound_data.get("scenarios", []) if self.sound_data else []
        
        filepath_full = self.file_txt.GetValue().strip()
        return {
            "id": sound_id,
            "name": self.name_txt.GetValue().strip(),
            "filepath_full": filepath_full,  # Main frame will use this to copy
            "filename": os.path.basename(filepath_full),
            "bus_id": bus_id,
            "hotkey": self.hotkey_txt.GetValue().strip(),
            "default_scenario": {
                "volume": self.vol_slider.GetValue() / 100.0,
                "fade_in_ms": self.fade_in_spin.GetValue(),
                "fade_out_ms": self.fade_out_spin.GetValue(),
                "speed": self.speed_spin.GetValue(),
                "loop": self.loop_chk.GetValue()
            },
            "scenarios": scenarios
        }


class AddEditBusDialog(wx.Dialog):
    """Dialog to create or edit a bus's name, mode, and volume."""
    def __init__(self, parent, bus_data=None):
        title = "Edit Bus" if bus_data else "Add Bus"
        super().__init__(parent, title=title, size=(400, 260))
        
        panel = wx.Panel(self)
        grid = wx.FlexGridSizer(0, 2, 12, 10)
        grid.AddGrowableCol(1, 1)
        
        # Name field
        grid.Add(wx.StaticText(panel, label="Bus Name:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.name_txt = wx.TextCtrl(panel)
        label_control(self.name_txt, "Bus Name")
        grid.Add(self.name_txt, 1, wx.EXPAND)
        
        # Mode choice
        grid.Add(wx.StaticText(panel, label="Playback Mode:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.mode_choice = wx.Choice(panel, choices=["exclusive", "layered"])
        label_control(self.mode_choice, "Playback Mode")
        grid.Add(self.mode_choice, 1, wx.EXPAND)
        self.mode_choice.SetSelection(1)  # Default layered
        
        # Volume slider
        grid.Add(wx.StaticText(panel, label="Volume:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.vol_slider = wx.Slider(panel, value=100, minValue=0, maxValue=100, style=wx.SL_HORIZONTAL | wx.SL_LABELS)
        label_control(self.vol_slider, "Volume")
        grid.Add(self.vol_slider, 1, wx.EXPAND)
        
        if bus_data:
            self.name_txt.SetValue(bus_data.get("name", ""))
            mode = bus_data.get("mode", "layered")
            self.mode_choice.SetSelection(0 if mode == "exclusive" else 1)
            self.vol_slider.SetValue(int(bus_data.get("volume", 1.0) * 100))
            
        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        panel_sizer.Add(grid, 1, wx.EXPAND | wx.ALL, 15)
        
        # Buttons
        btn_sizer, ok_btn, cancel_btn = create_dialog_buttons(panel)
        ok_btn.Bind(wx.EVT_BUTTON, self.OnOK)
            
        panel_sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.BOTTOM | wx.RIGHT, 15)
        panel.SetSizer(panel_sizer)
        
        self.name_txt.SetFocus()  # Set focus on first field
        self.CenterOnParent()

    def OnOK(self, event):
        name = self.name_txt.GetValue().strip()
        if not name:
            wx.MessageBox("Bus name cannot be empty.", "Error", wx.OK | wx.ICON_ERROR)
            self.name_txt.SetFocus()
            return
        event.Skip()

    def GetBusData(self):
        sel_mode = "exclusive" if self.mode_choice.GetSelection() == 0 else "layered"
        return {
            "name": self.name_txt.GetValue().strip(),
            "mode": sel_mode,
            "volume": self.vol_slider.GetValue() / 100.0
        }


class ManageBusesDialog(wx.Dialog):
    """Dialog to list, add, edit, and remove project buses."""
    def __init__(self, parent, project_data):
        super().__init__(parent, title="Manage Buses", size=(500, 350))
        self.project_data = project_data  # Direct reference to mutate in place
        
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # Left Side: Bus list
        list_sizer = wx.BoxSizer(wx.VERTICAL)
        list_lbl = wx.StaticText(panel, label="Buses:")
        self.bus_list = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        label_control(self.bus_list, "Buses List")
        self.bus_list.InsertColumn(0, "Name", width=180)
        self.bus_list.InsertColumn(1, "Mode", width=100)
        self.bus_list.InsertColumn(2, "Volume", width=80)
        
        list_sizer.Add(list_lbl, 0, wx.BOTTOM, 5)
        list_sizer.Add(self.bus_list, 1, wx.EXPAND)
        
        # Right Side: Action buttons
        btn_sizer = wx.BoxSizer(wx.VERTICAL)
        self.add_btn = wx.Button(panel, label="&Add Bus...")
        self.edit_btn = wx.Button(panel, label="&Edit Bus...")
        self.remove_btn = wx.Button(panel, label="&Remove Bus")
        self.close_btn = wx.Button(panel, id=wx.ID_CANCEL, label="&Close")
        
        btn_sizer.Add(self.add_btn, 0, wx.EXPAND | wx.BOTTOM, 8)
        btn_sizer.Add(self.edit_btn, 0, wx.EXPAND | wx.BOTTOM, 8)
        btn_sizer.Add(self.remove_btn, 0, wx.EXPAND | wx.BOTTOM, 20)
        btn_sizer.Add(self.close_btn, 0, wx.EXPAND)
        
        # Bind events
        self.add_btn.Bind(wx.EVT_BUTTON, self.OnAddBus)
        self.edit_btn.Bind(wx.EVT_BUTTON, self.OnEditBus)
        self.remove_btn.Bind(wx.EVT_BUTTON, self.OnRemoveBus)
        self.bus_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnEditBus)
        
        panel_sizer = wx.BoxSizer(wx.HORIZONTAL)
        panel_sizer.Add(list_sizer, 1, wx.EXPAND | wx.ALL, 15)
        panel_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 15)
        panel.SetSizer(panel_sizer)
        
        main_sizer.Add(panel, 1, wx.EXPAND)
        self.SetSizer(main_sizer)
        
        self.PopulateList()
        self.CenterOnParent()

    def PopulateList(self):
        self.bus_list.DeleteAllItems()
        for idx, bus in enumerate(self.project_data["buses"]):
            self.bus_list.InsertItem(idx, bus.get("name", "Unnamed"))
            self.bus_list.SetItem(idx, 1, bus.get("mode", "layered"))
            self.bus_list.SetItem(idx, 2, f"{int(bus.get('volume', 1.0) * 100)}%")
            # Associate bus dict to index
            self.bus_list.SetItemData(idx, idx)

    def OnAddBus(self, event):
        dlg = AddEditBusDialog(self)
        if dlg.ShowModal() == wx.ID_OK:
            new_data = dlg.GetBusData()
            new_data["id"] = str(uuid.uuid4())
            self.project_data["buses"].append(new_data)
            self.PopulateList()
            # Select the newly created item
            new_idx = len(self.project_data["buses"]) - 1
            self.bus_list.Select(new_idx)
            self.bus_list.Focus(new_idx)
        dlg.Destroy()

    def OnEditBus(self, event):
        sel = self.bus_list.GetFirstSelected()
        if sel == wx.NOT_FOUND:
            wx.MessageBox("Please select a bus to edit.", "Information", wx.OK | wx.ICON_INFORMATION)
            return
            
        bus_idx = self.bus_list.GetItemData(sel)
        bus = self.project_data["buses"][bus_idx]
        
        dlg = AddEditBusDialog(self, bus)
        if dlg.ShowModal() == wx.ID_OK:
            updated = dlg.GetBusData()
            bus.update(updated)
            self.PopulateList()
            self.bus_list.Select(sel)
            self.bus_list.Focus(sel)
        dlg.Destroy()

    def OnRemoveBus(self, event):
        sel = self.bus_list.GetFirstSelected()
        if sel == wx.NOT_FOUND:
            wx.MessageBox("Please select a bus to remove.", "Information", wx.OK | wx.ICON_INFORMATION)
            return
            
        if len(self.project_data["buses"]) <= 1:
            wx.MessageBox("You must keep at least one bus in the project.", "Error", wx.OK | wx.ICON_ERROR)
            return
            
        bus_idx = self.bus_list.GetItemData(sel)
        bus_to_delete = self.project_data["buses"][bus_idx]
        
        confirm = wx.MessageBox(
            f"Are you sure you want to remove the bus '{bus_to_delete['name']}'?\n"
            f"Any sounds assigned to this bus will be reassigned to '{self.project_data['buses'][0]['name']}'.",
            "Confirm Delete",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING
        )
        
        if confirm == wx.YES:
            # Reassign sounds
            backup_bus_id = self.project_data["buses"][0]["id"]
            if backup_bus_id == bus_to_delete["id"]:
                backup_bus_id = self.project_data["buses"][1]["id"]
                
            for sound in self.project_data["sounds"]:
                if sound.get("bus_id") == bus_to_delete["id"]:
                    sound["bus_id"] = backup_bus_id
                    
            self.project_data["buses"].pop(bus_idx)
            self.PopulateList()
            # Select first item
            self.bus_list.Select(0)
            self.bus_list.Focus(0)


class AddEditScenarioDialog(wx.Dialog):
    """Dialog to configure or edit a specific sound scenario preset."""
    def __init__(self, parent, buses, scenario_data=None):
        title = "Edit Scenario" if scenario_data else "Add Scenario"
        super().__init__(parent, title=title, size=(450, 420))
        
        self.buses = buses
        panel = wx.Panel(self)
        grid = wx.FlexGridSizer(0, 2, 10, 10)
        grid.AddGrowableCol(1, 1)
        
        # Scenario Name
        grid.Add(wx.StaticText(panel, label="Scenario Name:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.name_txt = wx.TextCtrl(panel)
        label_control(self.name_txt, "Scenario Name")
        grid.Add(self.name_txt, 1, wx.EXPAND)
        
        # Volume
        grid.Add(wx.StaticText(panel, label="Volume Override:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.vol_slider = wx.Slider(panel, value=100, minValue=0, maxValue=100, style=wx.SL_HORIZONTAL | wx.SL_LABELS)
        label_control(self.vol_slider, "Volume Override")
        grid.Add(self.vol_slider, 1, wx.EXPAND)
        
        # Fade In
        grid.Add(wx.StaticText(panel, label="Fade In Override (ms):"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.fade_in_spin = wx.SpinCtrl(panel, min=0, max=10000, initial=0)
        label_control(self.fade_in_spin, "Fade In Milliseconds")
        grid.Add(self.fade_in_spin, 1, wx.EXPAND)
        
        # Fade Out
        grid.Add(wx.StaticText(panel, label="Fade Out Override (ms):"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.fade_out_spin = wx.SpinCtrl(panel, min=0, max=10000, initial=0)
        label_control(self.fade_out_spin, "Fade Out Milliseconds")
        grid.Add(self.fade_out_spin, 1, wx.EXPAND)
        
        # Speed
        grid.Add(wx.StaticText(panel, label="Speed Override:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.speed_spin = wx.SpinCtrlDouble(panel, min=0.1, max=3.0, initial=1.0, inc=0.1)
        label_control(self.speed_spin, "Speed Override")
        grid.Add(self.speed_spin, 1, wx.EXPAND)
        
        # Loop
        grid.Add(wx.StaticText(panel, label=""), 0, wx.ALIGN_CENTER_VERTICAL)
        self.loop_chk = wx.CheckBox(panel, label="Loop Override")
        label_control(self.loop_chk, "Loop Override")
        grid.Add(self.loop_chk, 1, wx.EXPAND)
        
        # Bus Override
        grid.Add(wx.StaticText(panel, label="Bus Override:"), 0, wx.ALIGN_CENTER_VERTICAL)
        bus_choices = ["None (Use Default Bus)"] + [b["name"] for b in buses]
        self.bus_choice = wx.Choice(panel, choices=bus_choices)
        label_control(self.bus_choice, "Bus Override")
        grid.Add(self.bus_choice, 1, wx.EXPAND)
        self.bus_choice.SetSelection(0)
        
        if scenario_data:
            self.name_txt.SetValue(scenario_data.get("name", ""))
            self.vol_slider.SetValue(int(scenario_data.get("volume", 1.0) * 100))
            self.fade_in_spin.SetValue(scenario_data.get("fade_in_ms", 0))
            self.fade_out_spin.SetValue(scenario_data.get("fade_out_ms", 0))
            self.speed_spin.SetValue(scenario_data.get("speed", 1.0))
            self.loop_chk.SetValue(scenario_data.get("loop", False))
            
            # Set bus override
            bus_id = scenario_data.get("bus_id")
            if bus_id:
                for idx, b in enumerate(buses):
                    if b["id"] == bus_id:
                        self.bus_choice.SetSelection(idx + 1)
                        break
                        
        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        panel_sizer.Add(grid, 1, wx.EXPAND | wx.ALL, 15)
        
        # Buttons
        btn_sizer, ok_btn, cancel_btn = create_dialog_buttons(panel)
        ok_btn.Bind(wx.EVT_BUTTON, self.OnOK)
            
        panel_sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.BOTTOM | wx.RIGHT, 15)
        panel.SetSizer(panel_sizer)
        
        self.name_txt.SetFocus()  # Set focus on first field
        self.CenterOnParent()

    def OnOK(self, event):
        name = self.name_txt.GetValue().strip()
        if not name:
            wx.MessageBox("Scenario name cannot be empty.", "Error", wx.OK | wx.ICON_ERROR)
            self.name_txt.SetFocus()
            return
        event.Skip()

    def GetScenarioData(self):
        bus_idx = self.bus_choice.GetSelection()
        bus_id = None
        if bus_idx > 0:
            bus_id = self.buses[bus_idx - 1]["id"]
            
        return {
            "name": self.name_txt.GetValue().strip(),
            "volume": self.vol_slider.GetValue() / 100.0,
            "fade_in_ms": self.fade_in_spin.GetValue(),
            "fade_out_ms": self.fade_out_spin.GetValue(),
            "speed": self.speed_spin.GetValue(),
            "loop": self.loop_chk.GetValue(),
            "bus_id": bus_id
        }


class EditScenariosDialog(wx.Dialog):
    """Dialog to manage scenarios associated with a specific sound."""
    def __init__(self, parent, buses, sound_data):
        super().__init__(parent, title=f"Scenarios for {sound_data['name']}", size=(650, 400))
        self.buses = buses
        self.sound_data = sound_data  # Direct reference
        
        panel = wx.Panel(self)
        
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # Left Side: Scenarios List
        list_sizer = wx.BoxSizer(wx.VERTICAL)
        list_lbl = wx.StaticText(panel, label="Scenarios:")
        self.scen_list = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        label_control(self.scen_list, "Scenarios List")
        self.scen_list.InsertColumn(0, "Name", width=150)
        self.scen_list.InsertColumn(1, "Vol", width=50)
        self.scen_list.InsertColumn(2, "Fade In", width=70)
        self.scen_list.InsertColumn(3, "Fade Out", width=70)
        self.scen_list.InsertColumn(4, "Speed", width=60)
        self.scen_list.InsertColumn(5, "Loop", width=50)
        self.scen_list.InsertColumn(6, "Bus Override", width=120)
        
        list_sizer.Add(list_lbl, 0, wx.BOTTOM, 5)
        list_sizer.Add(self.scen_list, 1, wx.EXPAND)
        
        # Right Side: Action buttons
        btn_sizer = wx.BoxSizer(wx.VERTICAL)
        self.add_btn = wx.Button(panel, label="&Add...")
        self.edit_btn = wx.Button(panel, label="&Edit...")
        self.remove_btn = wx.Button(panel, label="&Remove")
        self.set_default_btn = wx.Button(panel, label="Set as &Default")
        self.close_btn = wx.Button(panel, id=wx.ID_CANCEL, label="&Close")
        
        btn_sizer.Add(self.add_btn, 0, wx.EXPAND | wx.BOTTOM, 8)
        btn_sizer.Add(self.edit_btn, 0, wx.EXPAND | wx.BOTTOM, 8)
        btn_sizer.Add(self.remove_btn, 0, wx.EXPAND | wx.BOTTOM, 8)
        btn_sizer.Add(self.set_default_btn, 0, wx.EXPAND | wx.BOTTOM, 20)
        btn_sizer.Add(self.close_btn, 0, wx.EXPAND)
        
        # Bind events
        self.add_btn.Bind(wx.EVT_BUTTON, self.OnAddScenario)
        self.edit_btn.Bind(wx.EVT_BUTTON, self.OnEditScenario)
        self.remove_btn.Bind(wx.EVT_BUTTON, self.OnRemoveScenario)
        self.set_default_btn.Bind(wx.EVT_BUTTON, self.OnSetAsDefault)
        self.scen_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnEditScenario)
        
        panel_sizer = wx.BoxSizer(wx.HORIZONTAL)
        panel_sizer.Add(list_sizer, 1, wx.EXPAND | wx.ALL, 15)
        panel_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 15)
        panel.SetSizer(panel_sizer)
        
        main_sizer.Add(panel, 1, wx.EXPAND)
        self.SetSizer(main_sizer)
        
        self.PopulateList()
        self.CenterOnParent()

    def PopulateList(self):
        self.scen_list.DeleteAllItems()
        # Initialize sound scenarios list if missing
        if "scenarios" not in self.sound_data:
            self.sound_data["scenarios"] = []
            
        for idx, scen in enumerate(self.sound_data["scenarios"]):
            self.scen_list.InsertItem(idx, scen["name"])
            self.scen_list.SetItem(idx, 1, f"{int(scen['volume'] * 100)}%")
            self.scen_list.SetItem(idx, 2, f"{scen['fade_in_ms']}ms")
            self.scen_list.SetItem(idx, 3, f"{scen['fade_out_ms']}ms")
            self.scen_list.SetItem(idx, 4, f"{scen['speed']}x")
            self.scen_list.SetItem(idx, 5, "Yes" if scen["loop"] else "No")
            
            # Bus override text
            bus_id = scen.get("bus_id")
            bus_name = "Default"
            if bus_id:
                for b in self.buses:
                    if b["id"] == bus_id:
                        bus_name = b["name"]
                        break
            self.scen_list.SetItem(idx, 6, bus_name)
            self.scen_list.SetItemData(idx, idx)

    def OnAddScenario(self, event):
        dlg = AddEditScenarioDialog(self, self.buses)
        if dlg.ShowModal() == wx.ID_OK:
            new_data = dlg.GetScenarioData()
            self.sound_data["scenarios"].append(new_data)
            self.PopulateList()
            new_idx = len(self.sound_data["scenarios"]) - 1
            self.scen_list.Select(new_idx)
            self.scen_list.Focus(new_idx)
        dlg.Destroy()

    def OnEditScenario(self, event):
        sel = self.scen_list.GetFirstSelected()
        if sel == wx.NOT_FOUND:
            wx.MessageBox("Please select a scenario to edit.", "Information", wx.OK | wx.ICON_INFORMATION)
            return
            
        scen_idx = self.scen_list.GetItemData(sel)
        scen = self.sound_data["scenarios"][scen_idx]
        
        dlg = AddEditScenarioDialog(self, self.buses, scen)
        if dlg.ShowModal() == wx.ID_OK:
            updated = dlg.GetScenarioData()
            scen.update(updated)
            self.PopulateList()
            self.scen_list.Select(sel)
            self.scen_list.Focus(sel)
        dlg.Destroy()

    def OnRemoveScenario(self, event):
        sel = self.scen_list.GetFirstSelected()
        if sel == wx.NOT_FOUND:
            wx.MessageBox("Please select a scenario to remove.", "Information", wx.OK | wx.ICON_INFORMATION)
            return
            
        scen_idx = self.scen_list.GetItemData(sel)
        scen = self.sound_data["scenarios"][scen_idx]
        
        confirm = wx.MessageBox(
            f"Are you sure you want to remove the scenario '{scen['name']}'?",
            "Confirm Delete",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING
        )
        
        if confirm == wx.YES:
            self.sound_data["scenarios"].pop(scen_idx)
            self.PopulateList()
            if self.sound_data["scenarios"]:
                self.scen_list.Select(0)
                self.scen_list.Focus(0)

    def OnSetAsDefault(self, event):
        sel = self.scen_list.GetFirstSelected()
        if sel == wx.NOT_FOUND:
            wx.MessageBox("Please select a scenario to set as default.", "Information", wx.OK | wx.ICON_INFORMATION)
            return
            
        scen_idx = self.scen_list.GetItemData(sel)
        scen = self.sound_data["scenarios"][scen_idx]
        
        # Set settings in default_scenario
        self.sound_data["default_scenario"] = {
            "volume": scen["volume"],
            "fade_in_ms": scen["fade_in_ms"],
            "fade_out_ms": scen["fade_out_ms"],
            "speed": scen["speed"],
            "loop": scen["loop"]
        }
        
        # Override sound's bus if scenario overrides it
        if scen.get("bus_id"):
            self.sound_data["bus_id"] = scen["bus_id"]
            
        wx.MessageBox(
            f"Scenario '{scen['name']}' settings copied as the default playback settings for this sound.",
            "Default Updated",
            wx.OK | wx.ICON_INFORMATION
        )


class ProjectManagerDialog(wx.Dialog):
    """Dialog to select, open, manage, and delete projects."""
    def __init__(self, parent, recent_projects, last_project_path=None):
        super().__init__(parent, title="Project Manager", size=(600, 400))
        self.recent_projects = list(recent_projects)  # Copy
        self.selected_project_path = None
        self.action = None  # 'open', 'create', 'browse', 'exit'
        
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # Left Side: Projects List
        list_sizer = wx.BoxSizer(wx.VERTICAL)
        list_lbl = wx.StaticText(panel, label="Recent Projects:")
        self.projects_list = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        label_control(self.projects_list, "Recent Projects List")
        self.projects_list.InsertColumn(0, "Name", width=180)
        self.projects_list.InsertColumn(1, "Path", width=250)
        
        list_sizer.Add(list_lbl, 0, wx.BOTTOM, 5)
        list_sizer.Add(self.projects_list, 1, wx.EXPAND)
        
        # Right Side: Buttons
        btn_sizer = wx.BoxSizer(wx.VERTICAL)
        self.open_btn = wx.Button(panel, label="&Open Selected")
        self.new_btn = wx.Button(panel, label="&New Project...")
        self.browse_btn = wx.Button(panel, label="&Browse Other...")
        self.remove_btn = wx.Button(panel, label="&Remove from List")
        self.delete_btn = wx.Button(panel, label="&Delete Project Files...")
        self.exit_btn = wx.Button(panel, label="&Exit App")
        
        btn_sizer.Add(self.open_btn, 0, wx.EXPAND | wx.BOTTOM, 8)
        btn_sizer.Add(self.new_btn, 0, wx.EXPAND | wx.BOTTOM, 8)
        btn_sizer.Add(self.browse_btn, 0, wx.EXPAND | wx.BOTTOM, 20)
        btn_sizer.Add(self.remove_btn, 0, wx.EXPAND | wx.BOTTOM, 8)
        btn_sizer.Add(self.delete_btn, 0, wx.EXPAND | wx.BOTTOM, 20)
        btn_sizer.Add(self.exit_btn, 0, wx.EXPAND)
        
        # Bind events
        self.open_btn.Bind(wx.EVT_BUTTON, self.OnOpen)
        self.new_btn.Bind(wx.EVT_BUTTON, self.OnNew)
        self.browse_btn.Bind(wx.EVT_BUTTON, self.OnBrowse)
        self.remove_btn.Bind(wx.EVT_BUTTON, self.OnRemove)
        self.delete_btn.Bind(wx.EVT_BUTTON, self.OnDelete)
        self.exit_btn.Bind(wx.EVT_BUTTON, self.OnExitBtn)
        self.projects_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnOpen)
        
        # Layout
        panel_sizer = wx.BoxSizer(wx.HORIZONTAL)
        panel_sizer.Add(list_sizer, 1, wx.EXPAND | wx.ALL, 15)
        panel_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 15)
        panel.SetSizer(panel_sizer)
        
        main_sizer.Add(panel, 1, wx.EXPAND)
        self.SetSizer(main_sizer)
        
        self.PopulateList(last_project_path)
        self.projects_list.SetFocus()
        self.CenterOnParent()
        
    def PopulateList(self, last_project_path=None):
        self.projects_list.DeleteAllItems()
        select_idx = 0
        for idx, proj in enumerate(self.recent_projects):
            self.projects_list.InsertItem(idx, proj["name"])
            self.projects_list.SetItem(idx, 1, proj["path"])
            self.projects_list.SetItemData(idx, idx)
            if last_project_path and proj["path"] == last_project_path:
                select_idx = idx
                
        if self.recent_projects:
            self.projects_list.Select(select_idx)
            self.projects_list.Focus(select_idx)

    def OnOpen(self, event):
        sel = self.projects_list.GetFirstSelected()
        if sel == wx.NOT_FOUND:
            wx.MessageBox("Please select a project from the list.", "Info", wx.OK | wx.ICON_INFORMATION)
            return
        idx = self.projects_list.GetItemData(sel)
        self.selected_project_path = self.recent_projects[idx]["path"]
        self.action = 'open'
        self.EndModal(wx.ID_OK)
        
    def OnNew(self, event):
        self.action = 'create'
        self.EndModal(wx.ID_OK)
        
    def OnBrowse(self, event):
        self.action = 'browse'
        self.EndModal(wx.ID_OK)
        
    def OnRemove(self, event):
        sel = self.projects_list.GetFirstSelected()
        if sel == wx.NOT_FOUND:
            return
        idx = self.projects_list.GetItemData(sel)
        self.recent_projects.pop(idx)
        self.PopulateList()
        
    def OnDelete(self, event):
        sel = self.projects_list.GetFirstSelected()
        if sel == wx.NOT_FOUND:
            return
        idx = self.projects_list.GetItemData(sel)
        proj = self.recent_projects[idx]
        
        confirm = wx.MessageBox(
            f"Are you sure you want to delete all files for project '{proj['name']}'?\n"
            f"This will permanently delete the folder:\n{proj['path']}\n\nTHIS ACTION CANNOT BE UNDONE.",
            "Confirm Project Deletion",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING
        )
        if confirm == wx.YES:
            try:
                import shutil
                shutil.rmtree(proj["path"], ignore_errors=True)
                self.recent_projects.pop(idx)
                self.PopulateList()
                Speech.speak(f"Deleted project {proj['name']}")
            except Exception as e:
                wx.MessageBox(f"Failed to delete directory:\n{e}", "Error", wx.OK | wx.ICON_ERROR)
                
    def OnExitBtn(self, event):
        self.action = 'exit'
        self.EndModal(wx.ID_CANCEL)
