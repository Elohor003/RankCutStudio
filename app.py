from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.utils import secure_filename
from pathlib import Path
import subprocess
import tempfile
import shutil
import uuid
import re

APP_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = APP_DIR / "uploads"
OUTPUT_DIR = APP_DIR / "outputs"

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024 * 1024

VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}


def tool_exists(name):
return shutil.which(name) is not None


def run_command(command):
result = subprocess.run(
command,
stdout=subprocess.PIPE,
stderr=subprocess.PIPE,
text=True
)

if result.returncode != 0:
raise RuntimeError(result.stderr[-2500:])

return result


def get_duration(path):
result = subprocess.run(
[
"ffprobe", "-v", "error",
"-show_entries", "format=duration",
"-of", "default=noprint_wrappers=1:nokey=1",
str(path)
],
capture_output=True,
text=True
)

try:
return float(result.stdout.strip())
except (ValueError, TypeError):
return 0.0


def detect_scene_changes(path):
"""Find visual scene changes using FFmpeg."""
try:
result = subprocess.run(
[
"ffmpeg", "-hide_banner",
"-i", str(path),
"-vf", "select='gt(scene,0.22)',showinfo",
"-an", "-f", "null", "-"
],
capture_output=True,
text=True,
timeout=180
)

return [
float(value)
for value in re.findall(
r"pts_time:([0-9]+(?:\.[0-9]+)?)",
result.stderr
)
]
except Exception:
return []


def choose_highlight(path, duration, target_length):
"""
Select a candidate highlight near a cluster of scene changes.
This is a visual heuristic, not semantic AI.
"""
length = min(duration, max(1.0, target_length))

if duration <= length:
return 0.0, duration

scenes = detect_scene_changes(path)

if scenes:
radius = min(5.0, length)

anchor = max(
scenes,
key=lambda timestamp: sum(
1 for other in scenes
if abs(other - timestamp) <= radius
)
)
else:
anchor = duration / 2

start = max(
0.0,
min(duration - length, anchor - length * 0.35)
)

return start, length


@app.route("/")
def index():
return render_template(
"index.html",
ffmpeg_ready=(
tool_exists("ffmpeg") and tool_exists("ffprobe")
)
)


@app.route("/api/render", methods=["POST"])
def render_video():
if not tool_exists("ffmpeg") or not tool_exists("ffprobe"):
return jsonify(
error="Install FFmpeg and ffprobe before rendering."
), 500

clips = [
file for file in request.files.getlist("clips")
if file and file.filename
]

if not clips:
return jsonify(
error="Please upload at least one video."
), 400

work = Path(tempfile.mkdtemp(prefix="rankcut_"))

try:
saved_clips = []

titles = request.form.getlist("clip_titles")
rank_labels = request.form.getlist("rank_labels")
trim_starts = request.form.getlist("trim_starts")
trim_ends = request.form.getlist("trim_ends")

for index, file in enumerate(clips):
extension = Path(
secure_filename(file.filename)
).suffix.lower()

if extension not in VIDEO_EXTS:
return jsonify(
error=f"Unsupported video format: {extension}"
), 400

destination = work / f"clip_{index:03d}{extension}"
file.save(destination)
saved_clips.append(destination)

durations = [get_duration(path) for path in saved_clips]

if any(duration <= 0 for duration in durations):
return jsonify(
error="Could not read a source video."
), 400

auto_highlights = (
request.form.get("auto_highlights", "on") == "on"
)

vertical = request.form.get("format", "vertical") == "vertical"
captions = request.form.get("captions", "on") == "on"

try:
font_size = int(request.form.get("font_size", "42"))
except ValueError:
font_size = 42

font_size = max(18, min(72, font_size))

project_title = request.form.get(
"project_title", "MY RANKING"
).strip()[:100]

try:
music_volume = float(
request.form.get("music_volume", "0.18")
)
except ValueError:
music_volume = 0.18

music_volume = max(0, min(1, music_volume))

try:
sfx_volume = float(
request.form.get("sfx_volume", "0.8")
)
except ValueError:
sfx_volume = 0.8

sfx_volume = max(0, min(2, sfx_volume))

# The complete video must remain within 60 seconds.
segment_budget = 60.0 / len(saved_clips)

width, height = (
(1080, 1920) if vertical else (1920, 1080)
)

normalized = []

for index, source in enumerate(saved_clips):
source_duration = durations[index]

if auto_highlights:
start, segment_length = choose_highlight(
source,
source_duration,
min(8.0, segment_budget)
)
else:
try:
start = float(
trim_starts[index]
) if index < len(trim_starts) else 0.0

end = float(
trim_ends[index]
) if index < len(trim_ends) else source_duration
except ValueError:
start, end = 0.0, source_duration

start = max(
0.0,
min(start, source_duration - 0.1)
)

end = min(source_duration, end)

segment_length = max(
0.5,
min(
end - start,
segment_budget,
source_duration - start
)
)

target = work / f"normalized_{index:03d}.mp4"

video_filter = (
f"scale={width}:{height}:"
"force_original_aspect_ratio=increase,"
f"crop={width}:{height},"
"setsar=1,fps=30,format=yuv420p"
)

label = (
rank_labels[index]
if index < len(rank_labels) else ""
).strip()[:40]

clip_title = (
titles[index]
if index < len(titles) else ""
).strip()[:120]

def escape_text(value):
return (
value.replace("\\", "\\\\")
.replace(":", "\\:")
.replace("'", "\\'")
.replace("%", "\\%")
.replace(",", "\\,")
.replace("[", "\\[")
.replace("]", "\\]")
)

if project_title:
video_filter += (
f",drawtext=text='{escape_text(project_title)}':"
f"fontcolor=white:fontsize={font_size}:"
"borderw=3:bordercolor=black:"
"x=(w-text_w)/2:y=h*0.08"
)

if label:
video_filter += (
f",drawtext=text='{escape_text(label)}':"
f"fontcolor=yellow:fontsize={font_size + 10}:"
"borderw=4:bordercolor=black:"
"x=(w-text_w)/2:y=h*0.78"
)

if captions and clip_title:
video_filter += (
f",drawtext=text='{escape_text(clip_title)}':"
f"fontcolor=white:fontsize={max(20, font_size - 8)}:"
"borderw=3:bordercolor=black:"
"box=1:boxcolor=black@0.45:boxborderw=12:"
"x=(w-text_w)/2:y=h*0.87"
)

run_command([
"ffmpeg", "-y",
"-ss", str(start),
"-i", str(source),
"-t", str(segment_length),
"-vf", video_filter,
"-an",
"-c:v", "libx264",
"-preset", "veryfast",
"-crf", "23",
"-movflags", "+faststart",
str(target)
])

normalized.append(target)

# Join the selected clips.
concat_file = work / "concat.txt"

concat_file.write_text(
"".join(
f"file '{path.as_posix()}'\n"
for path in normalized
),
encoding="utf-8"
)

silent_video = work / "silent.mp4"

run_command([
"ffmpeg", "-y",
"-f", "concat",
"-safe", "0",
"-i", str(concat_file),
"-c", "copy",
str(silent_video)
])

duration = get_duration(silent_video)

if duration <= 0 or duration > 60.2:
return jsonify(
error="The final video must be between 0 and 60 seconds."
), 400

output_name = f"rankcut_{uuid.uuid4().hex[:10]}.mp4"
output_path = OUTPUT_DIR / output_name

inputs = ["-i", str(silent_video)]
filters = []
audio_labels = []
input_index = 1

# Add background music.
music = request.files.get("music")

if music and music.filename:
extension = Path(
secure_filename(music.filename)
).suffix.lower()

if extension not in AUDIO_EXTS:
return jsonify(
error="Unsupported background music format."
), 400

music_path = work / f"music{extension}"
music.save(music_path)

inputs += [
"-stream_loop", "-1",
"-i", str(music_path)
]

filters.append(
f"[{input_index}:a]"
f"volume={music_volume},"
f"atrim=0:{duration},"
"asetpts=PTS-STARTPTS[music]"
)

audio_labels.append("[music]")
input_index += 1

# Add custom sound effects at chosen times.
sound_files = request.files.getlist("sfx_files")
sound_times = request.form.getlist("sfx_times")

for index, sound in enumerate(sound_files):
if not sound or not sound.filename:
continue

extension = Path(
secure_filename(sound.filename)
).suffix.lower()

if extension not in AUDIO_EXTS:
continue

sound_path = work / f"sfx_{index}{extension}"
sound.save(sound_path)

try:
start_time = max(
0.0,
float(sound_times[index])
if index < len(sound_times) else 0.0
)
except ValueError:
start_time = 0.0

delay = int(start_time * 1000)

filters.append(
f"[{input_index}:a]"
f"volume={sfx_volume},"
f"adelay={delay}|{delay},"
f"atrim=0:{duration}[sfx{index}]"
)

audio_labels.append(f"[sfx{index}]")

inputs += ["-i", str(sound_path)]
input_index += 1

if audio_labels:
if len(audio_labels) == 1:
filters.append(
f"{audio_labels[0]}alimiter=limit=0.95[aout]"
)
else:
filters.append(
"".join(audio_labels)
+ f"amix=inputs={len(audio_labels)}:"
"duration=first:dropout_transition=2,"
"alimiter=limit=0.95[aout]"
)

command = (
["ffmpeg", "-y"] + inputs
+ [
"-filter_complex", ";".join(filters),
"-map", "0:v:0",
"-map", "[aout]",
"-c:v", "copy",
"-c:a", "aac",
"-b:a", "192k",
"-shortest",
"-movflags", "+faststart",
str(output_path)
]
)
else:
command = [
"ffmpeg", "-y",
"-i", str(silent_video),
"-c", "copy",
"-movflags", "+faststart",
str(output_path)
]

run_command(command)

return jsonify(
ok=True,
filename=output_name,
duration=round(duration, 1),
message="Export finished successfully."
)

except RuntimeError as error:
return jsonify(
error=f"Video processing failed: {error}"
), 500

except Exception as error:
return jsonify(
error=f"Unexpected error: {error}"
), 500

finally:
shutil.rmtree(work, ignore_errors=True)


@app.route("/download/<filename>")
def download_video(filename):
safe_name = secure_filename(filename)
file_path = OUTPUT_DIR / safe_name

if not file_path.exists() or file_path.suffix.lower() != ".mp4":
return "Video not found.", 404

return send_file(
file_path,
as_attachment=True,
download_name="RankCut-Studio-Export.mp4"
)


if __name__ == "__main__":
app.run(host="127.0.0.1", port=5050, debug=False)

