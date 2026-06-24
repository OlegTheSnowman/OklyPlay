@echo off
echo Installing PyInstaller and dependencies...
python -m pip install pyinstaller -r requirements.txt
echo Building portable executable...
python -m PyInstaller --onefile --windowed --paths src --name OklyPlay src/soundboard.py
echo Build complete. Portable version is located in dist/OklyPlay.exe
pause
