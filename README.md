# YT_Transcriber

## 📋 Description

YT_Transcriber is a desktop application that allows you to:

1. **Extract audio** in MP3 format from any YouTube video
2. **Generate transcriptions** of audio content using offline speech recognition models
3. **Save and manage** audio files and transcriptions easily

The application is completely self-contained and works offline after the initial download of transcription models.

## ✨ Features

- 🎵 **MP3 audio extraction** from YouTube videos
- 🗣️ **Offline transcription** with models of various sizes
- 🌐 **Multilingual support** for transcription
- 💾 **Automatic download** of FFmpeg and transcription models
- 📝 **Copy and save** transcriptions
- 🎛️ **Modern and intuitive** interface

## 🚀 Installation

### Prerequisites

- Python 3.8 or higher
- Internet connection (only for initial download)

### Installation Steps

1. **Clone the repository or download the files**

```
git clone https://github.com/username/youtube-audio-extractor.git
cd youtube-audio-extractor
```
2. **Create a virtual environment (recommended)**

```
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python -m venv venv
source venv/bin/activate
```

3. **Install dependencies**
```
pip install -r requirements.txt
```
Alternatively, directly install the necessary libraries:
```
pip install yt-dlp PyQt6 faster-whisper requests
```

4. **Launch the application**
```
python app.py
```

# User Guide for YouTube Audio Extractor & Transcriber

## Audio Extraction
1. Paste the YouTube video URL in the input field
2. Select the destination folder (optional)
3. Click on "Extract Audio"
4. Wait for the download and extraction to complete

## Transcription Generation
1. Make sure the "Generate content transcription" checkbox is selected
2. Choose the transcription model:
   - `tiny`: Very fast, limited accuracy (~150MB)
   - `base`: Good compromise for short videos (~300MB)
   - `small`: Recommended for general use (~500MB)
   - `medium`: High accuracy, slower (~1.5GB)
   - `large`: Maximum accuracy, very slow (~3GB)
3. Click on "Extract Audio"
4. Wait for the transcription to complete

## Transcription Management
- Use the "Copy Transcription" button to copy the text to the clipboard
- Use the "Save Transcription" button to save the text to a .txt file

## Tips for Optimal Use
- For short videos (less than 5 minutes), the `base` model offers a good balance between speed and accuracy
- For content in languages other than English, it is recommended to use at least the `small` model
- The first run will be slower because it downloads the necessary models
- Close other heavy applications during transcription to improve performance

## Common Troubleshooting
- If the app freezes during download, check your internet connection and restart
- If the transcription is inaccurate, try a larger model or check the audio quality
- If audio extraction fails, check that the URL is correct and the video is accessible

## License

YT_Transcriber is distributed under the GNU General Public License v3.0. See the [LICENSE](LICENSE) file for the full license text.

This software uses the following third-party libraries:
- PyQt6 (GPL v3)
- yt-dlp (Unlicense)
- faster-whisper (MIT)
- FFmpeg (LGPL/GPL)

Using this software implies acceptance of the GPL v3 license terms.

## Copyright

Copyright (C) 2025 Marco Pastorello