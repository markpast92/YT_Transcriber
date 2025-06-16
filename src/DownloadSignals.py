from PyQt6.QtCore import Qt, pyqtSignal, QObject

# Class for handling signals between threads
class DownloadSignals(QObject):
    progress = pyqtSignal(float)
    finished = pyqtSignal(str, str)  # file_path, transcript
    error = pyqtSignal(str)
    status = pyqtSignal(str)