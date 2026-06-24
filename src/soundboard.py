import wx
from ui_main import MainFrame

def main():
    # Instantiate the wx.App
    app = wx.App(False)  # False to prevent redirecting stdout/stderr to a separate window
    
    # Create the main window
    frame = MainFrame(None, title="OklyPlay Soundboard")
    frame.Show(True)
    
    # Start the event loop
    app.MainLoop()

if __name__ == "__main__":
    main()
