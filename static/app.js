const form = document.getElementById("editor-form");
const clipsInput = document.getElementById("clips");
const clipList = document.getElementById("clip-list");
const autoHighlights = document.getElementById("auto-highlights");
const manualTrims = document.getElementById("manual-trims");
const trimList = document.getElementById("trim-list");
const sfxInput = document.getElementById("sfx-files");
const sfxList = document.getElementById("sfx-list");
const renderButton = document.getElementById("render-button");
const statusBox = document.getElementById("status");
const downloadLink = document.getElementById("download-link");

let selectedClips = [];
let selectedSfx = [];

function escapeHTML(value) {
return String(value).replace(/[&<>"']/g, (character) => ({
"&": "&amp;",
"<": "&lt;",
">": "&gt;",
'"': "&quot;",
"'": "&#039;"
})[character]);
}

function showStatus(message, type = "") {
statusBox.hidden = false;
statusBox.className = "status " + type;
statusBox.textContent = message;
}

function clearStatus() {
statusBox.hidden = true;
statusBox.textContent = "";
statusBox.className = "status";
}

function formatFileSize(bytes) {
if (bytes < 1024 * 1024) {
return Math.round(bytes / 1024) + " KB";
}

return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

function buildClipCards() {
clipList.innerHTML = "";
trimList.innerHTML = "";

if (!selectedClips.length) {
clipList.innerHTML =
'<p class="muted">Your selected clips will appear here.</p>';
return;
}

selectedClips.forEach((file, index) => {
const card = document.createElement("div");
card.className = "clip-card";

card.innerHTML = `
<div class="clip-card-header">
<span class="clip-number">${index + 1}</span>
<div class="clip-filename">
${escapeHTML(file.name)}
<div class="muted small">${formatFileSize(file.size)}</div>
</div>
</div>

<label for="rank-${index}">Ranking label</label>
<input
id="rank-${index}"
name="rank_labels"
type="text"
maxlength="40"
value="#${selectedClips.length - index}"
placeholder="#1"
>

<label for="title-${index}">Clip title / caption</label>
<input
id="title-${index}"
name="clip_titles"
type="text"
maxlength="120"
placeholder="Add a title for this moment"
>
`;

clipList.appendChild(card);

const trimCard = document.createElement("div");
trimCard.className = "clip-card";

trimCard.innerHTML = `
<strong>${index + 1}. ${escapeHTML(file.name)}</strong>

<div class="field-grid">
<div>
<label for="trim-start-${index}">Start (seconds)</label>
<input
id="trim-start-${index}"
name="trim_starts"
type="number"
min="0"
step="0.1"
value="0"
>
</div>

<div>
<label for="trim-end-${index}">End (seconds)</label>
<input
id="trim-end-${index}"
name="trim_ends"
type="number"
min="0.5"
step="0.1"
value="10"
>
</div>
</div>
`;

trimList.appendChild(trimCard);
});

manualTrims.hidden = autoHighlights.checked;
}

clipsInput.addEventListener("change", () => {
selectedClips = Array.from(clipsInput.files || []);
buildClipCards();
clearStatus();
downloadLink.hidden = true;

if (selectedClips.length) {
showStatus(
`${selectedClips.length} video file(s) selected. Review the titles before exporting.`,
""
);
}
});

autoHighlights.addEventListener("change", () => {
manualTrims.hidden = autoHighlights.checked;
});

sfxInput.addEventListener("change", () => {
selectedSfx = Array.from(sfxInput.files || []);
sfxList.innerHTML = "";

selectedSfx.forEach((file, index) => {
const card = document.createElement("div");
card.className = "sfx-card";

card.innerHTML = `
<strong>${escapeHTML(file.name)}</strong>

<label for="sfx-time-${index}">
Start time in final video (seconds)
</label>

<input
id="sfx-time-${index}"
name="sfx_times"
type="number"
min="0"
max="59"
step="0.1"
value="0"
>
`;

sfxList.appendChild(card);
});
});

function validateInputs() {
if (!selectedClips.length) {
showStatus("Please select at least one video.", "error");
return false;
}

const maxFileSize = 2 * 1024 * 1024 * 1024;

for (const file of selectedClips) {
if (file.size > maxFileSize) {
showStatus(
`${file.name} is larger than the 2 GB upload limit.`,
"error"
);
return false;
}
}

if (!autoHighlights.checked) {
const starts = form.querySelectorAll('[name="trim_starts"]');
const ends = form.querySelectorAll('[name="trim_ends"]');

for (let i = 0; i < starts.length; i++) {
const start = Number(starts[i].value);
const end = Number(ends[i].value);

if (
!Number.isFinite(start) ||
!Number.isFinite(end) ||
start < 0 ||
end <= start
) {
showStatus(
`Please check the start and end times for clip ${i + 1}.`,
"error"
);
return false;
}
}
}

for (let i = 0; i < selectedSfx.length; i++) {
const timeInput = document.getElementById(`sfx-time-${i}`);
const time = Number(timeInput.value);

if (!Number.isFinite(time) || time < 0 || time > 59) {
showStatus(
`Please enter a valid start time for sound effect ${i + 1}.`,
"error"
);
return false;
}
}

return true;
}

form.addEventListener("submit", async (event) => {
event.preventDefault();

downloadLink.hidden = true;

if (!validateInputs()) {
return;
}

const data = new FormData(form);

// Keep the user's original clip order.
data.delete("clips");
selectedClips.forEach((file) => data.append("clips", file));

data.delete("sfx_files");
selectedSfx.forEach((file) => data.append("sfx_files", file));

// Send a clear on/off value for automatic selection.
data.set(
"auto_highlights",
autoHighlights.checked ? "on" : "off"
);

renderButton.disabled = true;
renderButton.textContent = "⏳ Creating your video...";

showStatus(
"Your video is being processed. Longer videos may take several minutes.",
"loading"
);

try {
const response = await fetch("/api/render", {
method: "POST",
body: data
});

const result = await response.json().catch(() => ({}));

if (!response.ok || !result.ok) {
throw new Error(
result.error || "The video could not be created."
);
}

showStatus(
`Your video is ready! Duration: ${result.duration} seconds.`,
"success"
);

downloadLink.href =
"/download/" + encodeURIComponent(result.filename);

downloadLink.hidden = false;
downloadLink.scrollIntoView({
behavior: "smooth",
block: "center"
});
} catch (error) {
showStatus(
error.message ||
"Something went wrong. Check your files and try again.",
"error"
);
} finally {
renderButton.disabled = false;
renderButton.textContent = "✦ Create my ranking video";
}
});

buildClipCards();

