# Photo Matcher

**Automatically find and sort photos of specific people from large photo collections using face recognition.**

I built this app for my wife after our wedding to sort through thousands of photos for our close friends and family. I wanted it to be simple enough for her to use — and for anyone else in the future. If you feel you can improve it, please feel free to raise a PR and open a GitHub issue to track it. I hope you enjoy the app.

---

## What It Does

Photo Matcher scans your photo collection, detects every face using AI, and matches them against reference photos you provide. It then copies every photo containing your selected people into named folders — ready to share, print, or archive.

The entire pipeline runs locally on your machine. No cloud uploads, no subscriptions, no internet required after the initial setup. Processing is cached using content-based fingerprints, so you can move, rename, or reorganize your photos across drives and operating systems without losing any work.

## Features

- **Face detection & recognition** — powered by RetinaFace and ArcFace via InsightFace, with FAISS for fast similarity search
- **Built-in image review** — per-person folder cleanup tool with keyboard shortcuts
- **Cross-platform** — runs on Windows and Linux
- **Privacy-first** — everything runs locally, no data leaves your machine

---

## Use Cases

**Wedding & Event Photography**

A photographer delivers 10,000+ photos across multiple cameras. Photo Matcher pulls out every photo of the bride, groom, family members, or guests into individual folders — hours of manual sorting reduced to minutes.

**Family Photo Organization**

You have years of unsorted family photos across multiple folders, drives, or backups. Provide a few reference photos of each family member, and Photo Matcher finds them across your entire collection regardless of where the files are stored.

---

## Getting Started

### Prerequisites

- Python 3.11 or higher (3.12 recommended)
- NVIDIA GPU with CUDA (optional but recommended — 5-10x faster)

### Installation

```bash
# Clone the repository
git clone https://github.com/nishanthmarer/Photo_Matcher.git
cd Photo_Matcher

# Create and activate a virtual environment
python -m venv photo_matcher_env

# Windows
photo_matcher_env\Scripts\activate

# Linux / macOS
source photo_matcher_env/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

On first run, InsightFace will download the `buffalo_l` model pack (~326MB) to `./models/buffalo_l/`. Subsequent launches load from disk in ~2 seconds. The status bar shows 🟢 GPU or 🟡 CPU to confirm your device.

For detailed setup instructions including GPU configuration, conda setup, and troubleshooting, see [docs/SETUP.md](docs/SETUP.md).

### Automated Setup

**Windows:**
```bash
setup_env.bat
```

**Linux / macOS:**
```bash
chmod +x setup_env.sh
./setup_env.sh
```

These scripts detect whether Conda is available and use it if so, otherwise fall back to pip with a virtual environment.

---

## Usage Guide

### Step 1 — Add Reference Faces

In the **Reference Faces** panel:

1. Enter the person's name
2. Click **Browse Photos** and select 2-4 clear photos of that person
3. Click **+ Add**

For best results, use reference photos with varied angles — one frontal, one slight turn, one with different lighting.

### Step 2 — Select Source Folder

In the **Photo Source** panel:

1. Click **Browse** next to Source Folder and select your photo directory
2. The output folder auto-populates as `{source}_output` (editable)
3. The scan summary shows how many images were found

### Step 3 — Build Cache

Click **Build Cache** to process all photos through the ML pipeline:

- Each photo goes through face detection → alignment → embedding extraction
- Results are cached to `photo_cache/` using content fingerprints
- Progress is shown in real-time with per-photo updates
- Click the ⏹ stop button to pause — processed photos are saved automatically
- Re-running skips already-cached photos

For 15,000 photos on a mid-range GPU (RTX 3060), expect ~2-3 hours for the first run.

### Step 4 — Generate Folders

Click **Generate Folders** to match and copy:

- Cached embeddings are compared against your reference faces
- Matched photos are copied (not moved) to per-person subfolders in the output directory
- Already-copied files are skipped on re-runs

This step takes seconds, not hours. You can add new people and re-run without rebuilding the cache.

### Step 5 — Review Results

Each person's result entry has a **Review** button that opens the built-in image review tool:

| Key | Action |
|-----|--------|
| **D** / Delete | Mark for deletion |
| **S** / Right Arrow | Keep and advance |
| **B** / Left Arrow | Go back |
| **R** | Restore (undo deletion mark) |
| **Q** / Escape | Quit and confirm |

Deletions are deferred — files are only removed from disk after you confirm on quit.

### Standalone Image Review

The review tool can also be run independently to clean up any photo folder:

```bash
python tools/review_photos.py
```

---

## Troubleshooting

### GPU not detected

The status bar shows 🟡 CPU instead of 🟢 GPU.

1. Check CUDA is installed: `nvidia-smi` should show your GPU
2. Check ONNX Runtime providers:
   ```python
   python -c "import onnxruntime; print(onnxruntime.get_available_providers())"
   ```
3. Ensure `onnxruntime-gpu` is installed, not just `onnxruntime`
4. CUDA and cuDNN versions must match — see [docs/SETUP.md](docs/SETUP.md) for details

### Application won't start

Run the diagnostic script:

```bash
python debug.py
```

This tests each component in order and shows exactly where the failure occurs.

---

## License

This project is licensed under the **GNU General Public License v3.0** — see the [LICENSE](LICENSE) file for details.

You are free to use, modify, and distribute this software, but any derivative work must also be released under GPL v3 with source code available.

## Model License Notice

Photo Matcher's source code is released under GPL v3. However, the pretrained ML models (`buffalo_l`) downloaded at runtime are provided by InsightFace and are licensed for **non-commercial research purposes only**. If you intend to use this application in a commercial setting, please contact InsightFace at recognition-oss-pack@insightface.ai for model licensing.

---

## Acknowledgments

- [InsightFace](https://github.com/deepinsight/insightface) — RetinaFace detection and ArcFace recognition models
- [FAISS](https://github.com/facebookresearch/faiss) — fast similarity search by Meta AI
- [ONNX Runtime](https://onnxruntime.ai/) — high-performance ML inference by Microsoft
- [PySide6](https://doc.qt.io/qtforpython-6/) — Qt for Python UI framework

---

**Built by [Nishanth Marer Prabhu](https://github.com/nishanthmarer)**
