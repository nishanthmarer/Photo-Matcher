##########################################################################################################################
# Author: Nishanth Marer Prabhu
# fileName: image_reviewer.py
# Description: Pure service layer for image review workflow. Scans a directory for valid images, manages a set of
#              files marked for deletion, and executes permanent deletions on confirmation. No UI dependency — used by
#              both the integrated PySide6 review dialog and the standalone review tool. Deletions are deferred until
#              execute_deletions() is called, allowing full undo capability throughout the review session.
# Year: 2026
###########################################################################################################################

import os
from pathlib import Path

from config import AppConfig, LoggingConfig
from utils.logger import setup_logger

logger = setup_logger("services.image_reviewer", LoggingConfig())


class ImageReviewer:
    """Scans a directory for images and manages the mark-for-deletion workflow.

    Pure service — no UI dependency. Handles directory scanning, marking, restoring, and executing permanent
    deletions. Both the PySide6 review dialog and the standalone tool delegate all file logic to this class.

    Deletions are deferred: files are only marked during the review session. Actual deletion happens when
    execute_deletions() is called, enabling full undo (restore) at any point before confirmation.

    Usage:
        reviewer = ImageReviewer(config)
        images = reviewer.scan("/photos/Alice")
        reviewer.mark_for_deletion(images[0])
        reviewer.restore(images[0])        # undo
        summary = reviewer.execute_deletions()  # permanent
    """

    def __init__(self, config: AppConfig) -> None:
        """Initialize with application configuration.

        Args:
            config: Application configuration (provides image_extensions).
        """
        self._extensions = config.image_extensions
        self._marked: set[str] = set()
        self._images: list[str] = []
        self._directory: str = ""

    def scan(self, directory: str) -> list[str]:
        """Scan top-level directory for valid image files.

        Clears any previous state (marks, image list) before scanning. Only scans the top-level directory,
        does not recurse into subdirectories.

        Args:
            directory: Path to the directory to scan.

        Returns:
            Sorted list of absolute image file paths. Empty list if directory doesn't exist or has no images.
        """
        dir_path = Path(directory)

        if not dir_path.is_dir():
            logger.error(f"Review directory not found: {directory}")
            return []

        self._directory = directory
        self._marked.clear()
        self._images = sorted(
            str(f.resolve())
            for f in dir_path.iterdir()
            if f.is_file() and f.suffix.lower() in self._extensions
        )

        logger.info(f"Review scan: found {len(self._images)} images in {directory}")

        return self._images

    def mark_for_deletion(self, path: str) -> None:
        """Mark an image for deletion. Does not delete the file.

        Args:
            path: Absolute path to the image file.
        """
        self._marked.add(path)
        logger.info(f"Marked for deletion: {Path(path).name}")

    def restore(self, path: str) -> None:
        """Remove deletion mark from an image.

        Args:
            path: Absolute path to the image file.
        """
        self._marked.discard(path)
        logger.info(f"Restored: {Path(path).name}")

    def is_marked(self, path: str) -> bool:
        """Check if an image is marked for deletion.

        Args:
            path: Absolute path to the image file.

        Returns:
            True if the image is marked for deletion.
        """
        return path in self._marked

    def execute_deletions(self) -> dict:
        """Permanently delete all marked files from disk.

        Called once on user confirmation. Clears the marked set after execution.

        Returns:
            Summary dict with keys: total, deleted, kept, errors.
        """
        deleted = 0
        errors = []

        for path in list(self._marked):
            try:
                os.remove(path)
                deleted += 1
                logger.info(f"Deleted: {Path(path).name}")
            except OSError as e:
                errors.append(f"{Path(path).name}: {e}")
                logger.error(f"Failed to delete {path}: {e}")

        summary = {
            "total": len(self._images),
            "deleted": deleted,
            "kept": len(self._images) - deleted,
            "errors": errors,
        }

        logger.info(f"Review deletions complete: {summary}")
        self._marked.clear()

        return summary

    def discard_all_marks(self) -> None:
        """Clear all deletion marks without deleting any files."""
        count = len(self._marked)
        self._marked.clear()
        logger.info(f"Discarded {count} deletion marks")

    def reset(self) -> None:
        """Clear all state — marks, images, directory."""
        self._marked.clear()
        self._images.clear()
        self._directory = ""

    @property
    def marked_count(self) -> int:
        """Number of images currently marked for deletion."""
        return len(self._marked)

    @property
    def total_count(self) -> int:
        """Total number of images found in the last scan."""
        return len(self._images)

    @property
    def keeping_count(self) -> int:
        """Number of images not marked for deletion."""
        return len(self._images) - len(self._marked)

    @property
    def directory(self) -> str:
        """The directory being reviewed."""
        return self._directory