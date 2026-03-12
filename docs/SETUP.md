# Detailed Setup Guide

This guide walks through every step of setting up Photo Matcher, including GPU configuration and troubleshooting common installation issues.

---

## Prerequisites

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Python | 3.11 | 3.12 |
| RAM | 8 GB | 16 GB |
| Disk space | 1 GB (app + models) | 2 GB+ (with cache) |
| GPU (optional) | CUDA-capable, 4 GB VRAM | NVIDIA RTX series, 6 GB+ VRAM |

Photo Matcher runs on CPU out of the box. A GPU is optional but recommended for large collections — it's roughly 5-10x faster for the cache building step.

---

## Installation

### Option A — pip (Recommended)

```bash
# Clone the repository
git clone https://github.com/nishanthmarer/Photo_Matcher.git
cd Photo_Matcher

# Create a virtual environment
python -m venv photo_matcher_env

# Activate it
# Windows:
photo_matcher_env\Scripts\activate

# Linux / macOS:
source photo_matcher_env/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Option B — Conda

```bash
# Clone the repository
git clone https://github.com/nishanthmarer/Photo_Matcher.git
cd Photo_Matcher

# Create environment from the yml file
conda env create -f environment.yml

# If the environment already exists, update it
conda env update -f environment.yml --prune

# Activate
conda activate photo_matcher_env
```

### Option C — Automated Setup Scripts

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

## GPU Setup (Recommended for Large Collections)

GPU acceleration makes cache building 5-10x faster. The status bar in Photo Matcher shows 🟢 GPU or 🟡 CPU to confirm which device is active.

GPU setup requires three components: the NVIDIA driver, CUDA Toolkit, and cuDNN. If any of these are missing or mismatched, Photo Matcher falls back to CPU automatically — it won't crash.

### Step 1 — Check your NVIDIA driver

```bash
nvidia-smi
```

This should display your GPU name, driver version, and CUDA version. If this command fails, install the latest driver from [NVIDIA Drivers](https://www.nvidia.com/Download/index.aspx).

### Step 2 — Install CUDA Toolkit

Download from [NVIDIA CUDA Downloads](https://developer.nvidia.com/cuda-downloads).

Supported versions: CUDA 11.8 or 12.x.

### Step 3 — Install cuDNN

Download from [NVIDIA cuDNN](https://developer.nvidia.com/cudnn) (requires a free NVIDIA account).

cuDNN version must match your CUDA version:
- CUDA 11.8 → cuDNN 8.x
- CUDA 12.x → cuDNN 8.x or 9.x

Follow NVIDIA's installation guide for your platform — it typically involves copying files to the CUDA directory.

### Step 4 — Install GPU-enabled ONNX Runtime

The default `requirements.txt` includes `onnxruntime-gpu`. If you installed the CPU-only version or want to switch:

```bash
# Check what's currently installed
pip show onnxruntime-gpu
pip show onnxruntime

# If only CPU version is installed, switch to GPU
pip uninstall onnxruntime
pip install onnxruntime-gpu>=1.16.0
```

**Important:** You cannot have both `onnxruntime` and `onnxruntime-gpu` installed at the same time. Uninstall one before installing the other.

For users who do not have an NVIDIA GPU or prefer CPU-only:

```bash
pip uninstall onnxruntime-gpu
pip install onnxruntime>=1.16.0
```

### Step 5 — Verify GPU detection

```python
python -c "import onnxruntime; print(onnxruntime.get_available_providers())"
```

Expected output for a working GPU setup:
```
['CUDAExecutionProvider', 'CPUExecutionProvider']
```

If you only see `['CPUExecutionProvider']`, CUDA or cuDNN is not properly installed. See the troubleshooting section below.

### Step 6 — Run and verify

```bash
python main.py
```

The status bar at the bottom right shows **🟢 GPU** or **🟡 CPU** to confirm which device is active. GPU acceleration applies to the cache building step — matching and copying are fast on both CPU and GPU.

---

## ML Models

Photo Matcher uses the InsightFace `buffalo_l` model pack, which includes:

| Model | File | Size | Purpose |
|-------|------|------|---------|
| RetinaFace (SCRFD) | `det_10g.onnx` | ~16 MB | Face detection |
| ArcFace (w600k_r50) | `w600k_r50.onnx` | ~310 MB | Face recognition |

Models are downloaded automatically on first launch to `./models/buffalo_l/`. If the download fails (firewall, proxy, etc.), you can download the `buffalo_l` pack manually from the [InsightFace model zoo](https://github.com/deepinsight/insightface/tree/master/model_zoo) and place the `.onnx` files in `./models/buffalo_l/`.

---

## Verifying the Installation

Run the diagnostic script to test every component:

```bash
python debug.py
```

This checks in order:
1. PySide6 import
2. QApplication creation
3. Config loading
4. Core ML imports (detector, aligner, embedder, matcher, indexer, pipeline)
5. Services imports (scanner, cache, reference manager, segregator)
6. UI imports
7. MainWindow creation
8. Window display

If it fails, the output tells you exactly which step broke and the full traceback.

---

## Running the Application

```bash
python main.py
```

On first launch:
1. The window appears immediately with panels disabled
2. ML models download in the background (~326MB, shown in the status bar)
3. Once loaded, all panels are enabled and the status bar shows **✅ Ready**

Subsequent launches skip the download and load models from disk in ~2 seconds.

---

## Supported Image Formats

Photo Matcher processes the following formats:

`.jpg` `.jpeg` `.png` `.bmp` `.tiff` `.webp`

This can be changed in `config.py` under `AppConfig.image_extensions`.

---

## Troubleshooting

### GPU detected but slow performance

- Ensure `onnxruntime-gpu` is installed, not `onnxruntime` (CPU-only)
- Check that ONNX Runtime is actually using the GPU: the application logs in `photo_matcher.log` will show "Detection model loaded — GPU (CUDA) active" if the GPU is working
- Close other GPU-intensive applications (games, other ML workloads) that compete for VRAM

### CUDA version mismatch

ONNX Runtime is built against a specific CUDA version. If you see errors like `CUDA_ERROR_NO_DEVICE` or `Failed to load library`:

1. Check your CUDA version: `nvcc --version`
2. Check the [ONNX Runtime CUDA compatibility table](https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html)
3. Install the matching `onnxruntime-gpu` version:
   ```bash
   # For CUDA 11.8
   pip install onnxruntime-gpu==1.16.3

   # For CUDA 12.x
   pip install onnxruntime-gpu>=1.17.0
   ```

### PySide6 issues on Linux

If you see errors related to Qt or display:

```bash
# Install system Qt dependencies (Ubuntu/Debian)
sudo apt install libxcb-xinerama0 libxcb-cursor0 libgl1-mesa-glx libegl1

# If using Wayland and experiencing issues, try forcing X11
export QT_QPA_PLATFORM=xcb
python main.py
```

### Permission errors on Linux

```bash
# If the app can't create cache or log files
chmod -R 755 Photo_Matcher/

# If models directory isn't writable
chmod -R 755 Photo_Matcher/models/
```

### Virtual environment issues

If imports fail after activating the environment:

```bash
# Verify you're in the right environment
which python    # Linux/macOS
where python    # Windows

# Verify packages are installed
pip list | grep insightface
pip list | grep onnxruntime
pip list | grep PySide6
```

---

## Uninstalling

Photo Matcher creates the following files and directories at runtime:

| Path | Contents | Safe to delete? |
|------|----------|-----------------|
| `photo_cache/` | Cached embeddings per source folder | Yes — will be rebuilt on next run |
| `models/buffalo_l/` | Downloaded ML models (~326MB) | Yes — will re-download on next run |
| `photo_matcher.log` | Application logs | Yes |

To fully uninstall, delete the project folder and the virtual environment.
