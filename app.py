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
import uuid
import shutil
from pathlib import Path
import threading
import subprocess
import tempfile
from io import BytesIO
import requests
import zipfile
import platform

import yt_dlp
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                            QProgressBar, QFileDialog, QMessageBox, QStatusBar,
                            QCheckBox, QTextEdit)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QIcon, QFont, QColor, QPalette, QPixmap, QPainter, QLinearGradient
import ctypes

def set_windows_taskbar_icon():
    """Set application ID for Windows taskbar grouping and icon"""
    if sys.platform == 'win32':
        # Unique App id
        app_id = 'com.yourdomain.youtubeaudioextractor.1.0'
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception:
            pass 

# Class for handling signals between threads
class DownloadSignals(QObject):
    progress = pyqtSignal(float)
    finished = pyqtSignal(str, str)  # file_path, transcript
    error = pyqtSignal(str)
    status = pyqtSignal(str)

class YouTubeAudioExtractor(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Application directory
        self.app_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        
        # Set application icon
        icon_path = self.app_dir / "YT_Transcriber.ico" 
        if icon_path.exists():
            app_icon = QIcon(str(icon_path))
            self.setWindowIcon(app_icon)
        
        # Models directory
        self.models_dir = self.app_dir / "models"
        self.models_dir.mkdir(exist_ok=True)
        
        # Temporary directory
        self.temp_dir = self.app_dir / "temp"
        self.temp_dir.mkdir(exist_ok=True)
        
        # FFmpeg directory
        self.ffmpeg_dir = self.app_dir / "ffmpeg"
        self.ffmpeg_dir.mkdir(exist_ok=True)
        
        # Signals for thread communication
        self.signals = DownloadSignals()
        self.signals.progress.connect(self.update_progress)
        self.signals.finished.connect(self.process_finished)
        self.signals.error.connect(self.show_error)
        self.signals.status.connect(self.update_status)
        
        # Window configuration
        self.setWindowTitle("YT Transcribe")
        self.setMinimumSize(700, 500)
        
        # Modern style setup
        self.setup_style()
        
        # UI creation
        self.setup_ui()
    
    def setup_style(self):
        # Set modern theme
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        # Make buttons more visible with a distinct color
        palette.setColor(QPalette.ColorRole.Button, QColor(75, 75, 75))
        palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
        self.setPalette(palette)

    def setup_ui(self):
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Set minimum window size (larger than before)
        self.setMinimumSize(800, 600)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Header layout with title and About button
        header_layout = QHBoxLayout()
        
        # Title
        title_label = QLabel("YouTube Audio Extractor & Transcriber")
        title_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title_label, 1)
        
        # About button (with question mark icon)
        self.about_button = QPushButton("About")
        self.about_button.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_MessageBoxQuestion))
        self.about_button.clicked.connect(self.show_about)
        self.about_button.setMinimumWidth(120)
        self.about_button.setMinimumHeight(40)
        header_layout.addWidget(self.about_button, 0) 
        
        main_layout.addLayout(header_layout)
        
        # Description
        description = QLabel("Paste a YouTube video link to extract audio and generate transcription")
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(description)
        
        # Spacing
        main_layout.addSpacing(10)
        
        # URL input
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.youtube.com/watch?v=...")
        self.url_input.setMinimumHeight(40)
        url_layout.addWidget(self.url_input)
        
        # Extract button
        self.extract_button = QPushButton("Extract Audio")
        self.extract_button.setMinimumHeight(40)
        self.extract_button.setMinimumWidth(120)
        self.extract_button.clicked.connect(self.start_extraction)
        url_layout.addWidget(self.extract_button)
        
        main_layout.addLayout(url_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setMinimumHeight(30)
        main_layout.addWidget(self.progress_bar)
        
        # Transcription checkbox
        self.transcribe_checkbox = QCheckBox("Generate content transcription")
        self.transcribe_checkbox.setChecked(True)
        main_layout.addWidget(self.transcribe_checkbox)
        
        # Transcription model selection
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Transcription model:"))
        
        self.model_selector = QLineEdit("small")
        self.model_selector.setToolTip("Available models: tiny, base, small, medium, large")
        model_layout.addWidget(self.model_selector)
        
        model_info = QLabel("(tiny=fast, small=balanced, large=accurate)")
        model_layout.addWidget(model_info)
        
        main_layout.addLayout(model_layout)
        
        # Destination folder selection
        dest_layout = QHBoxLayout()
        self.dest_label = QLabel("Destination folder:")
        dest_layout.addWidget(self.dest_label)
        
        self.dest_path = QLineEdit()
        self.dest_path.setText(str(Path.home() / "Downloads"))
        self.dest_path.setReadOnly(True)
        dest_layout.addWidget(self.dest_path)
        
        self.browse_button = QPushButton("Browse")
        self.browse_button.setMinimumWidth(120)
        self.browse_button.setMinimumHeight(40)
        self.browse_button.clicked.connect(self.browse_folder)
        dest_layout.addWidget(self.browse_button)
        
        main_layout.addLayout(dest_layout)
        
        # Transcription text area
        self.transcript_label = QLabel("Transcription:")
        main_layout.addWidget(self.transcript_label)
        
        self.transcript_text = QTextEdit()
        self.transcript_text.setReadOnly(True)
        self.transcript_text.setMinimumHeight(150)
        main_layout.addWidget(self.transcript_text)
        
        # Transcription buttons
        transcript_buttons = QHBoxLayout()
        
        self.copy_button = QPushButton("Copy Transcription")
        self.copy_button.setMinimumHeight(40)
        self.copy_button.clicked.connect(self.copy_transcript)
        self.copy_button.setEnabled(False)
        transcript_buttons.addWidget(self.copy_button)
        
        self.save_button = QPushButton("Save Transcription")
        self.save_button.setMinimumHeight(40)
        self.save_button.clicked.connect(self.save_transcript)
        self.save_button.setEnabled(False)
        transcript_buttons.addWidget(self.save_button)
        
        main_layout.addLayout(transcript_buttons)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Variables to track current file
        self.current_audio_file = None
        self.current_transcript = None

    def show_about(self):
        """Show information about the application and its license"""
        about_text = """
        <h2>YT_Transcriber</h2>
        <p>Version 1.0</p>
        <p>A desktop application to extract audio from YouTube videos and generate transcriptions.</p>
        <p>&copy; 2025 Marco Pastorello</p>
        <p>This program is free software: you can redistribute it and/or modify
        it under the terms of the GNU General Public License as published by
        the Free Software Foundation, either version 3 of the License, or
        (at your option) any later version.</p>
        <p><a href="https://www.gnu.org/licenses/gpl-3.0.html">https://www.gnu.org/licenses/gpl-3.0.html</a></p>
        <p>This application uses:</p>
        <ul>
            <li>PyQt6 (GPL v3)</li>
            <li>yt-dlp (Unlicense)</li>
            <li>faster-whisper (MIT)</li>
            <li>FFmpeg (LGPL/GPL)</li>
        </ul>
        """
        QMessageBox.about(self, "About YT_Transcriber", about_text)
    
    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Destination Folder")
        if folder:
            self.dest_path.setText(folder)
    
    def start_extraction(self):
        url = self.url_input.text().strip()
        if not url:
            self.show_error("Please enter a valid YouTube URL")
            return
        
        self.extract_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.transcript_text.clear()
        self.copy_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self.update_status("Initializing download...")
        
        # Start download in a separate thread
        threading.Thread(
            target=self.extract_audio,
            args=(url, self.dest_path.text()),
            daemon=True
        ).start()
    
    def extract_audio(self, url, destination_folder):
        try:
            # Create a unique temporary directory for this download
            download_id = uuid.uuid4().hex
            download_dir = self.temp_dir / download_id
            download_dir.mkdir(exist_ok=True)
            
            # Hook to monitor progress
            def progress_hook(d):
                if d['status'] == 'downloading':
                    if 'total_bytes' in d and d['total_bytes'] > 0:
                        percent = d['downloaded_bytes'] / d['total_bytes'] * 100
                        self.signals.progress.emit(percent)
                        self.signals.status.emit(f"Downloading: {percent:.1f}%")
                    elif 'downloaded_bytes' in d:
                        self.signals.status.emit(f"Downloading: {d['downloaded_bytes'] / 1024 / 1024:.1f} MB")
                elif d['status'] == 'finished':
                    self.signals.status.emit("Download completed, extracting audio...")
                    self.signals.progress.emit(100)
            
            # Ensure FFmpeg is available
            ffmpeg_path = self.get_or_download_ffmpeg()
            
            # yt-dlp configuration for MP3 with integrated extractor
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': str(download_dir / '%(title)s.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
                'progress_hooks': [progress_hook]
            }
            
            # Add FFmpeg path if available
            if ffmpeg_path:
                ydl_opts['ffmpeg_location'] = ffmpeg_path
            
            # Execute download
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.signals.status.emit("Retrieving video information...")
                info = ydl.extract_info(url, download=True)
                title = info.get('title', 'audio')
            
            # Find the generated MP3 file
            mp3_files = list(download_dir.glob('*.mp3'))
            if not mp3_files:
                self.signals.error.emit("MP3 extraction failed. Check installation.")
                return
                
            input_file = mp3_files[0]
            
            # Create a safe filename
            safe_filename = f"{title.replace('/', '_').replace(':', '_').replace('\\', '_')}.mp3"
            
            # Copy the file to the destination folder
            destination_path = Path(destination_folder) / safe_filename
            shutil.copy2(input_file, destination_path)
            
            # Transcription
            transcript = ""
            if self.transcribe_checkbox.isChecked():
                self.signals.status.emit("Starting audio transcription...")
                transcript = self.transcribe_audio(str(input_file))
            
            # Clean up temporary files
            shutil.rmtree(download_dir, ignore_errors=True)
            
            # Signal completion
            self.signals.finished.emit(str(destination_path), transcript)
            
        except Exception as e:
            self.signals.error.emit(f"Error during extraction: {str(e)}")
    
    def get_or_download_ffmpeg(self):
        """Get or download FFmpeg based on platform"""
        
        # Determine platform and set appropriate paths and download URLs
        system = platform.system()
        
        if system == "Windows":
            ffmpeg_exe = self.ffmpeg_dir / "ffmpeg.exe"
            ffprobe_exe = self.ffmpeg_dir / "ffprobe.exe"
            
            # Check if FFmpeg is already downloaded
            if ffmpeg_exe.exists() and ffprobe_exe.exists():
                return str(self.ffmpeg_dir)
                
            # Download URL for Windows
            download_url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
            
            try:
                self.signals.status.emit("Downloading FFmpeg for Windows...")
                zip_path = self.ffmpeg_dir / "ffmpeg.zip"
                
                # Download zip file
                response = requests.get(download_url, stream=True)
                with open(zip_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                # Extract zip file
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    for file in zip_ref.namelist():
                        if file.endswith('ffmpeg.exe') or file.endswith('ffprobe.exe'):
                            filename = os.path.basename(file)
                            source = zip_ref.open(file)
                            target = open(self.ffmpeg_dir / filename, "wb")
                            with source, target:
                                shutil.copyfileobj(source, target)
                
                # Remove zip file
                os.remove(zip_path)
                
                self.signals.status.emit("FFmpeg installed successfully")
                return str(self.ffmpeg_dir)
                
            except Exception as e:
                self.signals.status.emit(f"Error downloading FFmpeg: {str(e)}")
                return None
                
        elif system == "Darwin":  # macOS
            ffmpeg_bin = self.ffmpeg_dir / "ffmpeg"
            ffprobe_bin = self.ffmpeg_dir / "ffprobe"
            
            # Check if FFmpeg is already downloaded
            if ffmpeg_bin.exists() and ffprobe_bin.exists():
                return str(self.ffmpeg_dir)
                
            # Download URL for macOS
            download_url = "https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip"
            ffprobe_url = "https://evermeet.cx/ffmpeg/getrelease/ffprobe/zip"
            
            try:
                self.signals.status.emit("Downloading FFmpeg for macOS...")
                
                # Download and extract ffmpeg
                self.download_and_extract_macos_binary(download_url, "ffmpeg")
                
                # Download and extract ffprobe
                self.download_and_extract_macos_binary(ffprobe_url, "ffprobe")
                
                # Make binaries executable
                os.chmod(ffmpeg_bin, 0o755)
                os.chmod(ffprobe_bin, 0o755)
                
                self.signals.status.emit("FFmpeg installed successfully")
                return str(self.ffmpeg_dir)
                
            except Exception as e:
                self.signals.status.emit(f"Error downloading FFmpeg: {str(e)}")
                return None
                
        elif system == "Linux":
            # For Linux, we'll check if FFmpeg is installed system-wide
            try:
                subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True)
                return None  # Use system FFmpeg
            except:
                self.signals.status.emit("FFmpeg not found on system. Please install FFmpeg using your package manager.")
                return None
        
        return None
    
    def download_and_extract_macos_binary(self, url, binary_name):
        """Helper function to download and extract macOS binaries"""
        zip_path = self.ffmpeg_dir / f"{binary_name}.zip"
        
        # Download zip file
        response = requests.get(url, stream=True)
        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Extract zip file
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(self.ffmpeg_dir)
        
        # Remove zip file
        os.remove(zip_path)
    
    def transcribe_audio(self, audio_file):
        try:
            self.signals.status.emit("Importing transcription library...")
            
            # Import here to avoid loading at app startup
            from faster_whisper import WhisperModel
            
            model_size = self.model_selector.text().strip() or "small"
            self.signals.status.emit(f"Loading transcription model '{model_size}'...")
            
            # Load model from app models folder
            model = WhisperModel(
                model_size, 
                device="cpu", 
                compute_type="int8", 
                download_root=str(self.models_dir)
            )
            
            self.signals.status.emit("Transcription in progress... (may take several minutes)")
            
            # Execute transcription
            segments, info = model.transcribe(audio_file, beam_size=5)
            
            # Join segments into complete text
            transcript = ""
            for segment in segments:
                transcript += f"{segment.text} "
            
            self.signals.status.emit("Transcription completed")
            return transcript.strip()
            
        except ImportError:
            self.signals.status.emit("Installing transcription library...")
            
            # Try to install faster-whisper
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "faster-whisper"])
                self.signals.status.emit("Library installed, restarting transcription...")
                return self.transcribe_audio(audio_file)
            except Exception as e:
                return f"Error installing transcription library: {str(e)}"
            
        except Exception as e:
            error_msg = f"Error during transcription: {str(e)}"
            self.signals.status.emit(error_msg)
            return error_msg
    
    def update_progress(self, value):
        self.progress_bar.setValue(int(value))
    
    def update_status(self, message):
        self.status_bar.showMessage(message)
    
    def process_finished(self, file_path, transcript):
        self.extract_button.setEnabled(True)
        self.update_status(f"Audio extracted successfully: {file_path}")
        
        # Save current file
        self.current_audio_file = file_path
        self.current_transcript = transcript
        
        # Show transcription
        if transcript:
            self.transcript_text.setPlainText(transcript)
            self.copy_button.setEnabled(True)
            self.save_button.setEnabled(True)
        
        # Show completion message
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Process Completed")
        
        if transcript:
            msg_box.setText(f"Audio extracted and transcription generated successfully.\nFile saved at:\n{file_path}")
        else:
            msg_box.setText(f"Audio extracted successfully.\nFile saved at:\n{file_path}")
        
        msg_box.setIcon(QMessageBox.Icon.Information)
        
        open_folder_button = msg_box.addButton("Open Folder", QMessageBox.ButtonRole.ActionRole)
        msg_box.addButton("OK", QMessageBox.ButtonRole.AcceptRole)
        
        msg_box.exec()
        
        # If user clicked "Open Folder"
        if msg_box.clickedButton() == open_folder_button:
            # Open folder containing the file - cross-platform approach
            folder_path = os.path.dirname(file_path)
            self.open_file_explorer(folder_path)
    
    def open_file_explorer(self, path):
        """Open file explorer in a cross-platform way"""
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["open", path])
        else:  # Linux
            subprocess.run(["xdg-open", path])
    
    def copy_transcript(self):
        if self.current_transcript:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.current_transcript)
            self.update_status("Transcription copied to clipboard")
    
    def save_transcript(self):
        if not self.current_transcript:
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Transcription", 
            str(Path(self.dest_path.text()) / "transcription.txt"),
            "Text files (*.txt)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.current_transcript)
                self.update_status(f"Transcription saved to: {file_path}")
            except Exception as e:
                self.show_error(f"Error saving transcription: {str(e)}")
    
    def show_error(self, message):
        self.extract_button.setEnabled(True)
        self.update_status(f"Error: {message}")
        
        QMessageBox.critical(self, "Error", message)

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