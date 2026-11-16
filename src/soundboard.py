import wx
from ui_main import MainFrame

def main():
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
