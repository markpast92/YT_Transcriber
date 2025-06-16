"""
YT_Transcriber - YouTube Audio Extractor & Transcriber
Copyright (C) 2025 Marco Pastorello

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import sys
import os
from pathlib import Path
from io import BytesIO
from PyQt6.QtWidgets import (QApplication)
from PyQt6.QtGui import QIcon
import ctypes

from src.YouTubeAudioExtractor import YouTubeAudioExtractor

def set_windows_taskbar_icon():
    """Set application ID for Windows taskbar grouping and icon"""
    if sys.platform == 'win32':
        # Unique App id
        app_id = 'com.yourdomain.youtubeaudioextractor.1.0'
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception:
            pass 

if __name__ == "__main__":
    # Imposta l'ID dell'app per la taskbar di Windows
    set_windows_taskbar_icon()
    
    app = QApplication(sys.argv)
    
    # Imposta l'icona dell'applicazione
    app_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    icon_path = app_dir / "YT_Transcriber.ico"
    
    if icon_path.exists():
        app_icon = QIcon(str(icon_path))
        app.setWindowIcon(app_icon)
    
    window = YouTubeAudioExtractor()
    window.show()
    
    sys.exit(app.exec())