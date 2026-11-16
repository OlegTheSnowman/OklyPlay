import ctypes

import wx
from ui_main import MainFrame


def enable_dpi_awareness():
    """Run per-monitor DPI aware. Unaware, Windows stretches the window on a
    scaled display (blurry text), and wx reports control positions to screen
    readers in unscaled pixels while Windows reports the real ones, so NVDA
    placed OK and Cancel inside the Audio Output group at 125% scale."""
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))  # per-monitor v2
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def main():
    enable_dpi_awareness()
    # Instantiate the wx.App
    app = wx.App(False)  # False to prevent redirecting stdout/stderr to a separate window
    # A fixed name keeps settings in %APPDATA%\OklyPlay whatever the exe or script
    # is called; otherwise wx names the folder after the file that was run.
    app.SetAppName("OklyPlay")

    # Create the main window
    frame = MainFrame(None, title="OklyPlay Soundboard")
    frame.Show(True)
    
    # Start the event loop
    app.MainLoop()

if __name__ == "__main__":
    main()
