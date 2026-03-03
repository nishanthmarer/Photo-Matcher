##########################################################################################################################
# Author: Nishanth Marer Prabhu
# fileName: file_utils.py
# Description: File system utilities for creating output folders, copying photos with duplicate handling, sanitizing
#              folder names, and formatting file sizes. Used by the segregator to build the output directory structure
#              and by the image review dialog for display.
# Year: 2026
###########################################################################################################################

import re
import shutil
from pathlib import Path

from config import LoggingConfig
from utils.logger import setup_logger

logger = setup_logger("utils.file_utils", LoggingConfig())


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