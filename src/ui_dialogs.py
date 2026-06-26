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
        if childId == wx.ACC_SELF:
            return wx.ACC_OK, self.name
        return wx.ACC_NOT_SUPPORTED, ""

def label_control(control, name):
    control.SetName(name)
    # Avoid SetAccessible for controls with native children (lists, dropdowns)
    # as overriding their accessible object breaks child item navigation/reading.
    if not isinstance(control, (wx.ListBox, wx.ListCtrl, wx.Choice)):
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


class QuickHotkeyDialog(wx.Dialog):
    """Simple dialog to assign a hotkey quickly to a sound."""
    def __init__(self, parent, name, current_hotkey=""):
        super().__init__(parent, title=f"Set Hotkey for {name}", size=(350, 160))
        
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        label = wx.StaticText(panel, label=f"Press the key combination for '{name}':")
        self.hotkey_ctrl = HotkeyCtrl(panel)
        self.hotkey_ctrl.SetValue(current_hotkey)
        self.hotkey_ctrl.hotkey_value = current_hotkey
        
        # Label the control for screen readers
        label_control(self.hotkey_ctrl, f"Press the key combination you want to assign to '{name}'. Press Tab and then Enter to confirm, or Escape to cancel.")
        
        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(panel, wx.ID_OK)
        cancel_btn = wx.Button(panel, wx.ID_CANCEL)
        btn_sizer.AddButton(ok_btn)
        btn_sizer.AddButton(cancel_btn)
        btn_sizer.Realize()
        
        sizer.Add(label, 0, wx.ALL | wx.EXPAND, 10)
        sizer.Add(self.hotkey_ctrl, 0, wx.ALL | wx.EXPAND, 10)
        sizer.Add(btn_sizer, 0, wx.ALL | wx.ALIGN_RIGHT, 10)
        
        panel.SetSizer(sizer)
        self.hotkey_ctrl.SetFocus()
        self.CenterOnParent()
        
    def GetValue(self):
        return self.hotkey_ctrl.GetValue().strip()


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


class SoundManagerDialog(wx.Dialog):
    """
    Sound Manager — lets the user import sounds (without mandatory bus assignment),
    view all project sounds, edit their properties inline, and reassign buses
    quickly via Ctrl+1..9 while focused on the list.

    Keyboard shortcuts inside the dialog:
        Ctrl+I          — Import more sounds via file picker
        Ctrl+V          — Paste audio files copied from Explorer
        F2              — Edit selected sound properties
        Delete          — Remove selected sound
        Ctrl+1..9       — Move selected sound to bus 1..9
        Ctrl+U          — Clear bus assignment (unassign)
    """

    AUDIO_WILDCARD = (
        "Audio files (*.mp3;*.wav;*.ogg;*.flac;*.aiff)|*.mp3;*.wav;*.ogg;*.flac;*.aiff"
    )

    def __init__(self, parent, project_data, project_dir):
        super().__init__(parent, title="Sound Manager", size=(720, 500),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.project_data = project_data
        self.project_dir = project_dir
        # Keep a working copy of sounds so we can cancel changes
        import copy
        self._original_sounds = copy.deepcopy(project_data.get("sounds", []))

        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # ── Instruction label ──────────────────────────────────────────────
        hint = wx.StaticText(
            panel,
            label=(
                "Manage all sounds. Use Ctrl+1\u20139 to assign the selected sound to a bus. "
                "Ctrl+U clears the bus. Press F2 to edit, Delete to remove, "
                "Ctrl+I to import from file picker, Ctrl+V to paste files copied from Explorer."
            )
        )
        hint.Wrap(680)
        main_sizer.Add(hint, 0, wx.ALL | wx.EXPAND, 8)

        # ── Sound list ─────────────────────────────────────────────────────
        self.sound_list = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        label_control(self.sound_list, "Sounds List — press Ctrl+1 through 9 to assign bus")
        self.sound_list.InsertColumn(0, "Name", width=200)
        self.sound_list.InsertColumn(1, "Bus", width=130)
        self.sound_list.InsertColumn(2, "Hotkey", width=100)
        self.sound_list.InsertColumn(3, "File", width=230)
        main_sizer.Add(self.sound_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        # ── Buttons row ────────────────────────────────────────────────────
        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self.import_btn = wx.Button(panel, label="&Import Sounds…\tCtrl+I")
        self.edit_btn   = wx.Button(panel, label="&Edit Sound…\tF2")
        self.remove_btn = wx.Button(panel, label="&Remove\tDelete")
        close_btn       = wx.Button(panel, id=wx.ID_OK, label="&Close")

        for b in (self.import_btn, self.edit_btn, self.remove_btn, close_btn):
            btn_row.Add(b, 0, wx.RIGHT, 6)

        main_sizer.Add(btn_row, 0, wx.ALL, 8)

        panel.SetSizer(main_sizer)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.SetSizer(outer)

        # ── Events ────────────────────────────────────────────────────────
        self.import_btn.Bind(wx.EVT_BUTTON, self.OnImport)
        self.edit_btn.Bind(wx.EVT_BUTTON, self.OnEdit)
        self.remove_btn.Bind(wx.EVT_BUTTON, self.OnRemove)
        self.sound_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnEdit)
        self.sound_list.Bind(wx.EVT_KEY_DOWN, self.OnListKeyDown)

        self._PopulateList()
        self.sound_list.SetFocus()
        self.CenterOnParent()

    # ── Internal helpers ──────────────────────────────────────────────────

    def _bus_name(self, bus_id):
        """Return the bus name for a given bus_id, or '(unassigned)'."""
        if not bus_id:
            return "(unassigned)"
        for b in self.project_data.get("buses", []):
            if b["id"] == bus_id:
                return b["name"]
        return "(unassigned)"

    def _PopulateList(self):
        sel = self.sound_list.GetFirstSelected()
        self.sound_list.DeleteAllItems()
        sounds = self.project_data.get("sounds", [])
        for idx, s in enumerate(sounds):
            self.sound_list.InsertItem(idx, s.get("name", "(unnamed)"))
            self.sound_list.SetItem(idx, 1, self._bus_name(s.get("bus_id", "")))
            self.sound_list.SetItem(idx, 2, s.get("hotkey", ""))
            self.sound_list.SetItem(idx, 3, s.get("filename", ""))
            self.sound_list.SetItemData(idx, idx)
        # Restore selection
        if sel != wx.NOT_FOUND and sel < self.sound_list.GetItemCount():
            self.sound_list.Select(sel)
            self.sound_list.Focus(sel)
        elif self.sound_list.GetItemCount() > 0:
            self.sound_list.Select(0)
            self.sound_list.Focus(0)

    def _selected_sound(self):
        """Return (list_idx, sound_dict) for the currently selected item, or (None, None)."""
        sel = self.sound_list.GetFirstSelected()
        if sel == wx.NOT_FOUND:
            return None, None
        sound_idx = self.sound_list.GetItemData(sel)
        sounds = self.project_data.get("sounds", [])
        if sound_idx < len(sounds):
            return sel, sounds[sound_idx]
        return None, None

    def _assign_bus(self, bus_number):
        """Assign the selected sound to bus number (1-based index into buses list)."""
        sel, sound = self._selected_sound()
        if sound is None:
            return
        buses = self.project_data.get("buses", [])
        bus_idx = bus_number - 1
        if bus_idx < 0 or bus_idx >= len(buses):
            wx.Bell()
            return
        target_bus = buses[bus_idx]
        sound["bus_id"] = target_bus["id"]
        self._PopulateList()
        # Keep the same row selected
        if sel < self.sound_list.GetItemCount():
            self.sound_list.Select(sel)
            self.sound_list.Focus(sel)

    # ── Event handlers ────────────────────────────────────────────────────

    def OnListKeyDown(self, event):
        key  = event.GetKeyCode()
        mods = event.GetModifiers()

        # Ctrl+1..9 → assign bus
        if mods == wx.MOD_CONTROL and ord('1') <= key <= ord('9'):
            self._assign_bus(key - ord('0'))
            return

        # Ctrl+U → unassign bus
        if mods == wx.MOD_CONTROL and key == ord('U'):
            _, sound = self._selected_sound()
            if sound is not None:
                sound["bus_id"] = ""
                self._PopulateList()
            return

        # F2 → edit
        if key == wx.WXK_F2 and mods == wx.MOD_NONE:
            self.OnEdit(None)
            return

        # Delete → remove
        if key == wx.WXK_DELETE and mods == wx.MOD_NONE:
            self.OnRemove(None)
            return

        # Ctrl+I → import via file picker
        if mods == wx.MOD_CONTROL and key == ord('I'):
            self.OnImport(None)
            return

        # Ctrl+V → paste files from clipboard
        if mods == wx.MOD_CONTROL and key == ord('V'):
            self._paste_from_clipboard()
            return

        event.Skip()

    def OnImport(self, event):
        """Open a multi-select file picker and import each chosen file as a new sound."""
        dlg = wx.FileDialog(
            self,
            message="Select Audio Files to Import",
            wildcard=self.AUDIO_WILDCARD,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE,
        )
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return

        paths = dlg.GetPaths()
        dlg.Destroy()

        sounds_dir = os.path.join(self.project_dir, "sounds")
        os.makedirs(sounds_dir, exist_ok=True)
        imported = 0
        skipped  = 0

        for src in paths:
            basename = os.path.basename(src)
            name_no_ext = os.path.splitext(basename)[0]

            # Copy file, avoiding name collision
            target = basename
            counter = 1
            while os.path.exists(os.path.join(sounds_dir, target)):
                base, ext = os.path.splitext(basename)
                target = f"{base}_{counter}{ext}"
                counter += 1

            try:
                import shutil
                shutil.copy2(src, os.path.join(sounds_dir, target))
            except Exception as e:
                skipped += 1
                continue

            new_sound = {
                "id":       str(uuid.uuid4()),
                "name":     name_no_ext,
                "filename": target,
                "bus_id":   "",           # intentionally unassigned
                "hotkey":   "",
                "default_scenario": {
                    "volume":          1.0,
                    "fade_in_ms":      0,
                    "fade_out_ms":     0,
                    "speed":           1.0,
                    "pitch_semitones": 0.0,
                    "loop":            False,
                },
                "scenarios": [],
                "missing":   False,
            }
            self.project_data["sounds"].append(new_sound)
            imported += 1

        self._PopulateList()
        msg = f"Imported {imported} sound(s)."
        if skipped:
            msg += f" {skipped} file(s) could not be copied."
        wx.MessageBox(msg, "Import Complete", wx.OK | wx.ICON_INFORMATION)

    def _paste_from_clipboard(self):
        """Import audio files that were copied to the clipboard from Windows Explorer (Ctrl+C → Ctrl+V)."""
        AUDIO_EXTS = {".mp3", ".wav", ".ogg", ".flac", ".aiff"}

        # Read file paths from the clipboard
        file_data = wx.FileDataObject()
        if not wx.TheClipboard.Open():
            wx.MessageBox(
                "Could not open the clipboard.",
                "Paste Error", wx.OK | wx.ICON_ERROR,
            )
            return

        got_data = wx.TheClipboard.GetData(file_data)
        wx.TheClipboard.Close()

        if not got_data:
            wx.MessageBox(
                "The clipboard does not contain any files.\n"
                "Copy audio files in Explorer first, then press Ctrl+V here.",
                "Nothing to Paste", wx.OK | wx.ICON_INFORMATION,
            )
            return

        all_paths   = file_data.GetFilenames()
        audio_paths = [p for p in all_paths
                       if os.path.splitext(p)[1].lower() in AUDIO_EXTS]

        if not audio_paths:
            wx.MessageBox(
                f"No supported audio files found on the clipboard "
                f"({len(all_paths)} non-audio file(s) ignored).\n"
                f"Supported formats: {', '.join(sorted(AUDIO_EXTS))}",
                "Nothing to Paste", wx.OK | wx.ICON_INFORMATION,
            )
            return

        sounds_dir = os.path.join(self.project_dir, "sounds")
        os.makedirs(sounds_dir, exist_ok=True)
        imported = 0
        skipped  = 0

        for src in audio_paths:
            basename    = os.path.basename(src)
            name_no_ext = os.path.splitext(basename)[0]

            # Avoid collisions in the sounds/ folder
            target  = basename
            counter = 1
            while os.path.exists(os.path.join(sounds_dir, target)):
                base, ext = os.path.splitext(basename)
                target = f"{base}_{counter}{ext}"
                counter += 1

            try:
                import shutil
                shutil.copy2(src, os.path.join(sounds_dir, target))
            except Exception:
                skipped += 1
                continue

            self.project_data["sounds"].append({
                "id":       str(uuid.uuid4()),
                "name":     name_no_ext,
                "filename": target,
                "bus_id":   "",
                "hotkey":   "",
                "default_scenario": {
                    "volume":          1.0,
                    "fade_in_ms":      0,
                    "fade_out_ms":     0,
                    "speed":           1.0,
                    "pitch_semitones": 0.0,
                    "loop":            False,
                },
                "scenarios": [],
                "missing":   False,
            })
            imported += 1

        self._PopulateList()
        msg = f"Pasted {imported} sound(s)."
        if skipped:
            msg += f" {skipped} file(s) could not be copied."
        wx.MessageBox(msg, "Paste Complete", wx.OK | wx.ICON_INFORMATION)

    def OnEdit(self, event):
        """Open AddEditSoundDialog for the selected sound."""
        sel, sound = self._selected_sound()
        if sound is None:
            wx.Bell()
            return

        sounds_dir = os.path.join(self.project_dir, "sounds")
        full_path  = os.path.join(sounds_dir, sound.get("filename", ""))
        temp = sound.copy()
        temp["filename"] = full_path

        buses = self.project_data.get("buses", [])
        dlg = AddEditSoundDialog(self, buses, temp,
                                 existing_sounds=self.project_data.get("sounds", []))
        if dlg.ShowModal() == wx.ID_OK:
            updated = dlg.GetSoundData()
            new_full = updated.pop("filepath_full", "")
            # If user picked a new file, copy it in
            if new_full and new_full != full_path and os.path.exists(new_full):
                import shutil
                new_rel = os.path.basename(new_full)
                dest = os.path.join(sounds_dir, new_rel)
                counter = 1
                while os.path.exists(dest) and dest != os.path.join(sounds_dir, sound["filename"]):
                    base, ext = os.path.splitext(new_rel)
                    new_rel = f"{base}_{counter}{ext}"
                    dest = os.path.join(sounds_dir, new_rel)
                    counter += 1
                shutil.copy2(new_full, dest)
                updated["filename"] = new_rel
            else:
                updated["filename"] = sound["filename"]

            # Preserve the id
            updated["id"] = sound["id"]

            # Patch in-place
            sounds = self.project_data.get("sounds", [])
            for i, s in enumerate(sounds):
                if s["id"] == sound["id"]:
                    sounds[i] = updated
                    break
            self._PopulateList()
        dlg.Destroy()

    def OnRemove(self, event):
        sel, sound = self._selected_sound()
        if sound is None:
            wx.Bell()
            return
        answer = wx.MessageBox(
            f"Remove '{sound.get('name', '?')}' from the project?",
            "Confirm Remove",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
        )
        if answer == wx.YES:
            sounds = self.project_data.get("sounds", [])
            self.project_data["sounds"] = [s for s in sounds if s["id"] != sound["id"]]
            self._PopulateList()


class AddEditSoundDialog(wx.Dialog):
    """Dialog to add or edit sound properties (name, file, bus, hotkey, volume, fade, speed, loop)."""
    def __init__(self, parent, buses, sound_data=None, existing_sounds=None):
        title = "Edit Sound" if sound_data else "Add Sound"
        super().__init__(parent, title=title, size=(500, 530))
        
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
        label_control(self.speed_spin, "Playback Speed Multiplier (also shifts pitch, like tape speed)")
        grid.Add(self.speed_spin, 1, wx.EXPAND)

        # Pitch spin (independent from speed)
        grid.Add(wx.StaticText(panel, label="Pitch (semitones):"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.pitch_spin = wx.SpinCtrlDouble(panel, min=-12.0, max=12.0, initial=0.0, inc=0.5)
        label_control(self.pitch_spin, "Pitch Shift in Semitones. Negative values lower pitch, positive raise it. Zero means no change.")
        grid.Add(self.pitch_spin, 1, wx.EXPAND)

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
            self.pitch_spin.SetValue(default_scen.get("pitch_semitones", 0.0))
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
                "pitch_semitones": self.pitch_spin.GetValue(),
                "loop": self.loop_chk.GetValue()
            },
            "scenarios": scenarios
        }


class AddEditBusDialog(wx.Dialog):
    """Dialog to create or edit a bus's name, mode, and volume."""
    def __init__(self, parent, bus_data=None):
        title = "Edit Bus" if bus_data else "Add Bus"
        super().__init__(parent, title=title, size=(420, 560))
        self.bus_data = bus_data
        
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
        self.mode_choice.Bind(wx.EVT_CHOICE, self.OnModeChanged)
        
        # Volume slider
        grid.Add(wx.StaticText(panel, label="Volume:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.vol_slider = wx.Slider(panel, value=100, minValue=0, maxValue=100, style=wx.SL_HORIZONTAL | wx.SL_LABELS)
        label_control(self.vol_slider, "Volume")
        grid.Add(self.vol_slider, 1, wx.EXPAND)
        
        # Hotkey field
        grid.Add(wx.StaticText(panel, label="Hotkey:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.hotkey_txt = HotkeyCtrl(panel)
        label_control(self.hotkey_txt, "Bus Hotkey")
        grid.Add(self.hotkey_txt, 1, wx.EXPAND)

        # Crossfade field
        grid.Add(wx.StaticText(panel, label="Crossfade (ms):"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.crossfade_spin = wx.SpinCtrl(panel, min=0, max=10000, initial=500)
        label_control(self.crossfade_spin, "Crossfade milliseconds")
        grid.Add(self.crossfade_spin, 1, wx.EXPAND)

        # Hotkey Action choice
        grid.Add(wx.StaticText(panel, label="Hotkey Action:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.action_choices = ["Loop (Shuffle)", "Loop (Sequential)", "Single (Shuffle)", "Single (Sequential)"]
        self.action_choice = wx.Choice(panel, choices=self.action_choices)
        label_control(self.action_choice, "Hotkey Action")
        grid.Add(self.action_choice, 1, wx.EXPAND)
        self.action_choice.SetSelection(2)  # Default Single (Shuffle) for layered
        
        self.action_mapping = ["loop_shuffle", "loop_sequential", "single_shuffle", "single_sequential"]

        # Track Crossfade field
        grid.Add(wx.StaticText(panel, label="Track Crossfade (ms):"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.track_crossfade_spin = wx.SpinCtrl(panel, min=0, max=10000, initial=2000)
        label_control(self.track_crossfade_spin, "Track Crossfade milliseconds")
        grid.Add(self.track_crossfade_spin, 1, wx.EXPAND)

        # Ducking Trigger Checkbox
        grid.Add(wx.StaticText(panel, label="Ducking Trigger:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.duck_trigger_chk = wx.CheckBox(panel, label="Duck other buses when playing")
        label_control(self.duck_trigger_chk, "Duck other buses when playing")
        grid.Add(self.duck_trigger_chk, 1, wx.EXPAND)
        self.duck_trigger_chk.Bind(wx.EVT_CHECKBOX, self.OnDuckTriggerChanged)

        # Ducking Factor Slider
        self.duck_factor_lbl = wx.StaticText(panel, label="Duck Volume Level:")
        grid.Add(self.duck_factor_lbl, 0, wx.ALIGN_CENTER_VERTICAL)
        self.duck_factor_slider = wx.Slider(panel, value=30, minValue=0, maxValue=100, style=wx.SL_HORIZONTAL | wx.SL_LABELS)
        label_control(self.duck_factor_slider, "Duck Volume Level")
        grid.Add(self.duck_factor_slider, 1, wx.EXPAND)

        # Duckable Checkbox
        grid.Add(wx.StaticText(panel, label="Ducking Susceptibility:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.duckable_chk = wx.CheckBox(panel, label="Can be ducked by other buses")
        label_control(self.duckable_chk, "Can be ducked by other buses")
        grid.Add(self.duckable_chk, 1, wx.EXPAND)
        
        if bus_data:
            self.name_txt.SetValue(bus_data.get("name", ""))
            mode = bus_data.get("mode", "layered")
            self.mode_choice.SetSelection(0 if mode == "exclusive" else 1)
            self.vol_slider.SetValue(int(bus_data.get("volume", 1.0) * 100))
            self.hotkey_txt.SetValue(bus_data.get("hotkey", ""))
            self.hotkey_txt.hotkey_value = bus_data.get("hotkey", "")
            self.crossfade_spin.SetValue(bus_data.get("crossfade_ms", 500 if mode == "exclusive" else 0))
            
            action = bus_data.get("hotkey_action", "loop_shuffle" if mode == "exclusive" else "single_shuffle")
            try:
                action_idx = self.action_mapping.index(action)
                self.action_choice.SetSelection(action_idx)
            except ValueError:
                self.action_choice.SetSelection(0 if mode == "exclusive" else 2)
                
            self.track_crossfade_spin.SetValue(bus_data.get("track_crossfade_ms", 2000 if mode == "exclusive" else 0))
            
            duck_factor = bus_data.get("duck_factor", 1.0)
            is_triggering = duck_factor < 1.0
            self.duck_trigger_chk.SetValue(is_triggering)
            self.duck_factor_slider.SetValue(int(duck_factor * 100) if is_triggering else 30)
            self.duck_factor_slider.Enable(is_triggering)
            self.duck_factor_lbl.Enable(is_triggering)
            self.duckable_chk.SetValue(bus_data.get("duckable", True if mode == "exclusive" else False))
        else:
            self.duck_trigger_chk.SetValue(False)
            self.duck_factor_slider.SetValue(30)
            self.duck_factor_slider.Enable(False)
            self.duck_factor_lbl.Enable(False)
            self.duckable_chk.SetValue(False)
            
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
            
        hotkey = self.hotkey_txt.GetValue().strip()
        if hotkey:
            # Locate parent window to query project data for verification
            parent_dlg = self.Parent
            while parent_dlg and not hasattr(parent_dlg, "project_data"):
                parent_dlg = parent_dlg.Parent
                
            if parent_dlg and hasattr(parent_dlg, "project_data"):
                project_data = parent_dlg.project_data
                my_id = self.bus_data.get("id") if self.bus_data else None
                
                # Check other buses
                for b in project_data.get("buses", []):
                    if b.get("id") != my_id and b.get("hotkey", "").strip().lower() == hotkey.lower():
                        wx.MessageBox(
                            f"The hotkey '{hotkey}' is already assigned to the bus '{b['name']}'.\n"
                            "Please choose a different hotkey.",
                            "Hotkey Conflict", wx.OK | wx.ICON_WARNING
                        )
                        self.hotkey_txt.SetFocus()
                        return
                
                # Check sounds
                for s in project_data.get("sounds", []):
                    if s.get("hotkey", "").strip().lower() == hotkey.lower():
                        wx.MessageBox(
                            f"The hotkey '{hotkey}' is already assigned to the sound '{s['name']}'.\n"
                            "Please choose a different hotkey.",
                            "Hotkey Conflict", wx.OK | wx.ICON_WARNING
                        )
                        self.hotkey_txt.SetFocus()
                        return
        event.Skip()
 
    def OnDuckTriggerChanged(self, event):
        triggered = self.duck_trigger_chk.GetValue()
        self.duck_factor_slider.Enable(triggered)
        self.duck_factor_lbl.Enable(triggered)
 
    def OnModeChanged(self, event):
        sel = self.mode_choice.GetSelection()
        if sel == 0:  # exclusive
            self.action_choice.SetSelection(0)  # Loop (Shuffle)
            self.crossfade_spin.SetValue(500)
            self.track_crossfade_spin.SetValue(2000)
            self.duckable_chk.SetValue(True)
        else:  # layered
            self.action_choice.SetSelection(2)  # Single (Shuffle)
            self.crossfade_spin.SetValue(0)
            self.track_crossfade_spin.SetValue(0)
            self.duckable_chk.SetValue(False)

    def GetBusData(self):
        sel_mode = "exclusive" if self.mode_choice.GetSelection() == 0 else "layered"
        action_idx = self.action_choice.GetSelection()
        hotkey_action = self.action_mapping[action_idx] if action_idx != wx.NOT_FOUND else "single_shuffle"
        
        is_triggering = self.duck_trigger_chk.GetValue()
        duck_factor = self.duck_factor_slider.GetValue() / 100.0 if is_triggering else 1.0
        
        return {
            "name": self.name_txt.GetValue().strip(),
            "mode": sel_mode,
            "volume": self.vol_slider.GetValue() / 100.0,
            "hotkey": self.hotkey_txt.GetValue().strip(),
            "crossfade_ms": self.crossfade_spin.GetValue(),
            "hotkey_action": hotkey_action,
            "track_crossfade_ms": self.track_crossfade_spin.GetValue(),
            "duck_factor": duck_factor,
            "duckable": self.duckable_chk.GetValue()
        }
 
 
class ManageBusesDialog(wx.Dialog):
    """Dialog to list, add, edit, and remove project buses."""
    def __init__(self, parent, project_data):
        super().__init__(parent, title="Manage Buses", size=(890, 350))
        self.project_data = project_data  # Direct reference to mutate in place
        
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # Left Side: Bus list
        list_sizer = wx.BoxSizer(wx.VERTICAL)
        list_lbl = wx.StaticText(panel, label="Buses:")
        self.bus_list = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        label_control(self.bus_list, "Buses List")
        self.bus_list.InsertColumn(0, "Name", width=120)
        self.bus_list.InsertColumn(1, "Mode", width=80)
        self.bus_list.InsertColumn(2, "Volume", width=60)
        self.bus_list.InsertColumn(3, "Hotkey", width=90)
        self.bus_list.InsertColumn(4, "Crossfade", width=90)
        self.bus_list.InsertColumn(5, "Track Fade", width=90)
        self.bus_list.InsertColumn(6, "Ducking", width=130)
        self.bus_list.InsertColumn(7, "Action", width=140)
        
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
            self.bus_list.SetItem(idx, 3, bus.get("hotkey", ""))
            self.bus_list.SetItem(idx, 4, f"{bus.get('crossfade_ms', 500 if bus.get('mode') == 'exclusive' else 0)} ms")
            self.bus_list.SetItem(idx, 5, f"{bus.get('track_crossfade_ms', 2000 if bus.get('mode') == 'exclusive' else 0)} ms")
            
            duck_factor = bus.get("duck_factor", 1.0)
            duckable = bus.get("duckable", False)
            duck_parts = []
            if duck_factor < 1.0:
                duck_parts.append(f"Ducks ({int(duck_factor * 100)}%)")
            if duckable:
                duck_parts.append("Duckable")
            duck_str = " / ".join(duck_parts) if duck_parts else "Off"
            self.bus_list.SetItem(idx, 6, duck_str)

            action_map = {
                "loop_shuffle": "Loop (Shuffle)",
                "loop_sequential": "Loop (Sequential)",
                "single_shuffle": "Single (Shuffle)",
                "single_sequential": "Single (Sequential)"
            }
            action_code = bus.get("hotkey_action", "loop_shuffle" if bus.get("mode") == "exclusive" else "single_shuffle")
            action_str = action_map.get(action_code, "Single (Shuffle)")
            self.bus_list.SetItem(idx, 7, action_str)
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
        super().__init__(parent, title=title, size=(450, 470))
        
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
        label_control(self.speed_spin, "Speed Override (also shifts pitch, like tape speed)")
        grid.Add(self.speed_spin, 1, wx.EXPAND)

        # Pitch
        grid.Add(wx.StaticText(panel, label="Pitch Override (semitones):"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.pitch_spin = wx.SpinCtrlDouble(panel, min=-12.0, max=12.0, initial=0.0, inc=0.5)
        label_control(self.pitch_spin, "Pitch Shift in Semitones. Negative lowers pitch, positive raises it. Zero means no change.")
        grid.Add(self.pitch_spin, 1, wx.EXPAND)

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
            self.pitch_spin.SetValue(scenario_data.get("pitch_semitones", 0.0))
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
            "pitch_semitones": self.pitch_spin.GetValue(),
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
        self.scen_list.InsertColumn(0, "Name", width=140)
        self.scen_list.InsertColumn(1, "Vol", width=45)
        self.scen_list.InsertColumn(2, "Fade In", width=65)
        self.scen_list.InsertColumn(3, "Fade Out", width=65)
        self.scen_list.InsertColumn(4, "Speed", width=55)
        self.scen_list.InsertColumn(5, "Pitch", width=55)
        self.scen_list.InsertColumn(6, "Loop", width=45)
        self.scen_list.InsertColumn(7, "Bus Override", width=110)
        
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
            pitch = scen.get("pitch_semitones", 0.0)
            pitch_str = f"+{pitch:g}" if pitch > 0 else f"{pitch:g}"
            self.scen_list.SetItem(idx, 5, f"{pitch_str} st")
            self.scen_list.SetItem(idx, 6, "Yes" if scen["loop"] else "No")

            # Bus override text
            bus_id = scen.get("bus_id")
            bus_name = "Default"
            if bus_id:
                for b in self.buses:
                    if b["id"] == bus_id:
                        bus_name = b["name"]
                        break
            self.scen_list.SetItem(idx, 7, bus_name)
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
