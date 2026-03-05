##########################################################################################################################
# Author: Nishanth Marer Prabhu
# fileName: file_utils.py
# Description: File system utilities for creating output folders, copying photos with duplicate handling, sanitizing
#              folder names, formatting file sizes, computing content-based file fingerprints, and generating
#              human-readable cache filenames. Used by the segregator, cache manager, and image review dialog.
# Year: 2026
###########################################################################################################################

import hashlib
import re
import shutil
from pathlib import Path

from config import LoggingConfig
from utils.logger import setup_logger

logger = setup_logger("utils.file_utils", LoggingConfig())


# ---------------------------------------------------------------------------
# Content fingerprinting — platform-independent file identity
# ---------------------------------------------------------------------------

def compute_fingerprint(file_path: str, chunk_size: int = 65536) -> str | None:
    """Compute a content-based fingerprint for a file.

    The fingerprint is derived from the file's size, first chunk_size bytes, and last chunk_size bytes.
    This is sufficient for uniquely identifying DSLR photos since EXIF headers alone contain unique
    metadata (camera serial, timestamp, shutter count). For files smaller than 2 * chunk_size, the
    entire content is hashed.

    The fingerprint is independent of the file's path, name, or location — only the content matters.
    Moving, renaming, or copying a file to another drive or OS does not change its fingerprint.

    Performance: ~0.5ms per file on SSD (two 64KB reads + SHA-256), negligible vs ML inference.

    Args:
        file_path: Absolute path to the file.
        chunk_size: Number of bytes to read from the head and tail of the file. Default 64KB.

    Returns:
        A 16-character hex string (first 16 chars of SHA-256), or None if the file cannot be read.
    """
    try:
        file_size = Path(file_path).stat().st_size

        if file_size == 0:
            return None

        hasher = hashlib.sha256()

        # Include file size in the hash — eliminates the vast majority of false matches at zero I/O cost
        hasher.update(file_size.to_bytes(8, byteorder="big"))

        with open(file_path, "rb") as f:
            if file_size <= chunk_size * 2:
                # Small file — hash the entire content
                hasher.update(f.read())
            else:
                # Large file — hash first chunk + last chunk
                head = f.read(chunk_size)
                hasher.update(head)

                f.seek(-chunk_size, 2)  # Seek from end of file
                tail = f.read(chunk_size)
                hasher.update(tail)

        return hasher.hexdigest()[:16]

    except OSError as e:
        logger.warning(f"Cannot fingerprint file {file_path}: {e}")
        return None


# ---------------------------------------------------------------------------
# Cache filename generation — platform-independent naming
# ---------------------------------------------------------------------------

def compute_cache_filename(source_dir: str) -> str:
    """Generate a human-readable, platform-independent cache filename for a source directory.

    The filename combines the source folder's name (sanitized for filesystem safety) with a short
    hash of the folder name for consistency. The hash is based on the folder name only — NOT the
    full path — so the same folder produces the same cache filename regardless of where it lives
    or which operating system it's on.

    If two folders with the same name exist at different paths, they share a cache file. This is
    safe because entries inside are keyed by content fingerprint, not by path.

    Example:
        Input:  "D:/Nishanth_Vandana_Wedding/Cam 1-20260218T100635Z-1-001"
        Output: "Cam_1-20260218T100635Z-1-001_a3f2e1b0_cache.pkl"

    Args:
        source_dir: Full path to the source directory.

    Returns:
        Cache filename string (not a full path — just the filename).
    """
    folder_name = Path(source_dir).name

    # Sanitize: replace spaces with underscores, remove filesystem-unsafe characters
    safe_name = re.sub(r'[<>:"/\\|?*]', "", folder_name)
    safe_name = re.sub(r"\s+", "_", safe_name).strip("_")

    if not safe_name:
        safe_name = "unnamed"

    # Short hash of the folder name only (NOT the full path) for platform independence.
    # D:\Wedding\Cam 1 and /home/user/Wedding/Cam 1 produce the same hash.
    # If two different source folders share the same name, their entries merge into one cache file —
    # this is safe because entries are keyed by content fingerprint, not path.
    name_hash = hashlib.sha256(folder_name.encode()).hexdigest()[:8]

    return f"{safe_name}_{name_hash}_cache.pkl"


# ---------------------------------------------------------------------------
# Output folder and file copy utilities
# ---------------------------------------------------------------------------

def create_output_folder(base_path: str, folder_name: str) -> Path:
    """Create a named subfolder inside the output directory.

    Args:
        base_path: Root output directory path.
        folder_name: Name of the subfolder to create.

    Returns:
        Path object for the created folder.
    """
    folder = Path(base_path) / folder_name
    folder.mkdir(parents=True, exist_ok=True)

    return folder


def copy_photo(source: str, destination_folder: Path) -> Path:
    """Copy a photo to a destination folder, preserving metadata.

    If a file with the same name already exists, a numeric suffix is appended to avoid overwriting
    (e.g., IMG_001_1.jpg).

    Args:
        source: Path to the source photo.
        destination_folder: Folder to copy the photo into.

    Returns:
        Path to the copied file.
    """
    source_path = Path(source)
    destination = destination_folder / source_path.name

    if destination.exists():
        stem = source_path.stem
        suffix = source_path.suffix
        counter = 1

        while destination.exists():
            destination = destination_folder / f"{stem}_{counter}{suffix}"
            counter += 1

    try:
        shutil.copy2(source, destination)
        logger.info(f"Copied: {source_path.name} → {destination_folder.name}/")
    except Exception as e:
        logger.error(f"Failed to copy {source}: {e}")

    return destination


# ---------------------------------------------------------------------------
# String and formatting utilities
# ---------------------------------------------------------------------------

def sanitize_folder_name(name: str) -> str:
    """Clean a name to make it safe as a folder name.

    Removes characters invalid in file systems, collapses multiple spaces, and strips leading/trailing whitespace.

    Args:
        name: Raw name string (e.g., person's name).

    Returns:
        Sanitized string safe for use as a folder name.
    """
    sanitized = re.sub(r'[<>:"/\\|?*]', "", name)
    sanitized = re.sub(r"\s+", " ", sanitized)
    sanitized = sanitized.strip()

    if not sanitized:
        sanitized = "unnamed"

    return sanitized


def human_readable_size(size_bytes: int) -> str:
    """Format a byte count as a human-readable string.

    Args:
        size_bytes: File size in bytes.

    Returns:
        Formatted string (e.g., "2.4 MB", "350.0 KB").
    """
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024

    return f"{size_bytes:.1f} TB"