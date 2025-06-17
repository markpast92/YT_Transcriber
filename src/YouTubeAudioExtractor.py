import sys
import os
import uuid
import shutil
from pathlib import Path
import threading
import subprocess
import requests
import zipfile
import platform
import time

import yt_dlp
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                            QProgressBar, QFileDialog, QMessageBox, QStatusBar,
                            QCheckBox, QTextEdit)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QFont, QColor, QPalette

from src.DownloadSignals import DownloadSignals

class YouTubeAudioExtractor(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Application directory
        self.app_dir = Path(os.path.dirname(os.path.abspath(__file__))).parent
        
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
        
        # Spacing
        main_layout.addSpacing(10)
        
        # URL input
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.youtube.com/watch?v=...")
        self.url_input.setMinimumHeight(40)
        self.url_input.setStyleSheet("QLineEdit::placeholder { color: white; }")
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
        
        # Transcription model selection
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Transcription model:"))
        
        self.model_selector = QLineEdit("small")
        self.model_selector.setToolTip("Available models: tiny, base, small, medium, large")
        model_layout.addWidget(self.model_selector)
        
        model_info = QLabel("(tiny=fast, small=balanced, large=accurate)")
        model_layout.addWidget(model_info)
        
        main_layout.addLayout(model_layout)
        
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
        
        # Start download in a separate thread - non serve più il destination_folder
        threading.Thread(
            target=self.extract_audio,
            args=(url,),
            daemon=True
        ).start()

    def extract_audio(self, url):
        try:
            # Progress monitoring hook for yt-dlp
            def progress_hook(d):
                if d['status'] == 'downloading':
                    if 'total_bytes' in d and d['total_bytes'] > 0:
                        percent = (d['downloaded_bytes'] / d['total_bytes']) * 50
                        self.signals.progress.emit(percent)
                        self.signals.status.emit(f"Downloading: {percent*2:.1f}%")
                    elif 'downloaded_bytes' in d:
                        self.signals.status.emit(f"Downloading: {d['downloaded_bytes'] / 1024 / 1024:.1f} MB")
                elif d['status'] == 'finished':
                    self.signals.status.emit("Download completed, extracting audio...")
                    self.signals.progress.emit(50)
            
            # Get FFmpeg path or download if not available
            ffmpeg_path = self.get_or_download_ffmpeg()
            
            # Generate unique ID for this download
            download_id = uuid.uuid4().hex
            
            # Configure yt-dlp options for audio extraction
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': str(self.temp_dir / f"{download_id}"),
                'quiet': True,
                'no_warnings': True,
                'progress_hooks': [progress_hook]
            }
            
            # Add FFmpeg path if available
            if ffmpeg_path:
                ydl_opts['ffmpeg_location'] = ffmpeg_path
            
            # Execute download and extract video metadata
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.signals.status.emit("Retrieving video information...")
                info = ydl.extract_info(url, download=True)
                title = info.get('title', 'audio')
            
            # Locate the downloaded MP3 file - using the download_id
            mp3_file = self.temp_dir / f"{download_id}.mp3"
            
            if not mp3_file.exists():
                self.signals.error.emit("MP3 extraction failed. Check installation.")
                return
            
            # Sanitize title for safe file naming
            import re
            # Remove hashtags and trailing content
            clean_title = re.sub(r'#.*$', '', title)
            # Remove special characters, keep alphanumeric, spaces and basic punctuation
            clean_title = re.sub(r'[^\w\s\-\.\(\)]', '', clean_title)
            # Remove multiple spaces and limit length
            clean_title = ' '.join(clean_title.split()).strip()[:50]
            
            # Fallback to generic name if title is empty after cleaning
            if not clean_title:
                clean_title = f"audio_{download_id[:8]}"
            
            # Create final filename and path
            safe_filename = f"{clean_title}.mp3"
            destination_path = self.temp_dir / safe_filename
            
            # Copy file with sanitized name
            shutil.copy2(mp3_file, destination_path)
            
            # Generate transcription
            transcript = ""
            self.signals.status.emit("Starting audio transcription...")
            transcript = self.transcribe_audio(str(mp3_file))
            
            # Clean up temporary file
            os.remove(mp3_file)
            
            # Signal process completion
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
            self.signals.progress.emit(60)
            
            # Import here to avoid loading at app startup
            from faster_whisper import WhisperModel
            
            # Ottieni il modello selezionato dall'utente
            model_size = self.model_selector.text().strip() or "small"
            self.signals.status.emit(f"Loading transcription model '{model_size}'...")
            self.signals.progress.emit(70)
            
            # Carica il modello
            model = WhisperModel(
                model_size, 
                device="cpu", 
                compute_type="int8", 
                download_root=str(self.models_dir)
            )
            
            self.signals.status.emit("Starting transcription... (may take several minutes)")
            self.signals.progress.emit(75)
            
            # Esegui la trascrizione
            segments_generator, info = model.transcribe(
                audio_file, 
                beam_size=5,
                word_timestamps=False
            )
            
            # Raccogli i segmenti e monitora il progresso
            transcript = ""
            segments = []
            segment_count = 0
            
            # Simuliamo il progresso durante la trascrizione
            for segment in segments_generator:
                segments.append(segment)
                segment_count += 1
                transcript += f"{segment.text} "
                
                # Aggiorna lo stato e il progresso ogni 5 segmenti
                if segment_count % 5 == 0:
                    progress_value = 75 + min(segment_count, 100) / 5
                    if progress_value > 95:
                        progress_value = 95
                    self.signals.progress.emit(progress_value)
                    self.signals.status.emit(f"Transcribing: {segment_count} segments processed")
            
            # Segnala il completamento
            self.signals.progress.emit(95)
            self.signals.status.emit("Transcription completed successfully")
            
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

        # Completa la barra di progresso al 100%
        self.progress_bar.setValue(100)
        
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
            
        # Usa la directory Downloads dell'utente come destinazione predefinita
        downloads_dir = Path.home() / "Downloads"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Transcription", 
            str(downloads_dir / "transcription.txt"),
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