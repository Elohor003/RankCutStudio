# RankCutStudio

**Your clips. Your countdown. Your style.**

RankCut Studio is a personal video-editing project designed to help create ranking videos for YouTube Shorts and other social platforms.

## ✨ Features

- Upload multiple video files.
- Automatically select candidate highlights using visual scene-change detection.
- Manually specify clip start and end times.
- Create vertical 9:16 videos or landscape videos.
- Add ranking numbers and custom titles.
- Add background music.
- Add custom sound effects at selected timestamps.
- Adjust music and sound-effect volume.
- Export MP4 videos up to 60 seconds.
- Download completed videos without an editor-added watermark.

## ⚠️ Current limitations

Automatic highlight selection uses visual scene changes as a heuristic. It does not understand the meaning of every video or reliably identify the funniest, most impressive, or most relevant moment.

Clip titles are on-screen text, not automatic speech recognition captions.

The current project is a local prototype. It is not yet a hosted website, and the code has not been fully tested in a production environment.

## 🧰 Requirements

- Python 3.10 or newer
- FFmpeg, including FFprobe
- A computer capable of processing video files

## 📥 Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR-USERNAME/RankCut-Studio.git
cd RankCut-Studio
```

Replace `YOUR-USERNAME` with your GitHub username.

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Install FFmpeg

Download FFmpeg from:

https://ffmpeg.org/download.html

Make sure both `ffmpeg` and `ffprobe` are available in your system PATH.

Verify the installation:

```bash
ffmpeg -version
ffprobe -version
```

### 5. Run the application

```bash
python app.py
```

Open this address in your browser:

http://127.0.0.1:5050

## 🎞️ Creating a ranking video

1. Upload the video files you are authorized to use.
2. Choose automatic highlight selection or enter manual trim times.
3. Add a main title and clip titles.
4. Choose vertical or landscape output.
5. Optionally upload background music and sound effects.
6. Choose sound-effect start times.
7. Click **Create my ranking video**.
8. Download the completed MP4.

## 🔒 Privacy and content rights

This prototype processes uploaded videos on the computer running the application. Do not deploy it publicly without adding appropriate authentication, upload limits, secure file handling, and resource controls.

Only use videos, music, and sound effects that you own or have permission to use. A link to a video does not automatically grant permission to download or reuse it.

## 🛠️ Planned improvements

- AI-powered, topic-aware highlight selection.
- Automatic speech-to-text captions.
- A timeline editor with clip preview and trimming.
- Drag-and-drop clip reordering.
- Save and reopen editing projects.
- Supported video-link importing.
- A hosted version with secure user accounts.

## 📄 License

See the `LICENSE` file for licensing information.

