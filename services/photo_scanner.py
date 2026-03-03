##########################################################################################################################
# Author: Nishanth Marer Prabhu
# fileName: photo_scanner.py
# Description: Directory scanner for valid image files. Recursively walks a source directory and collects all files
#              matching configured image extensions (.jpg, .png, .bmp, etc.). Supports excluding directories (e.g.,
#              output folders) from the scan to prevent processing already-segregated photos.
# Year: 2026
###########################################################################################################################

from collections import Counter
from pathlib import Path

from config import AppConfig, LoggingConfig
from utils.logger import setup_logger
from utils.image_utils import is_valid_image

logger = setup_logger("services.photo_scanner", LoggingConfig())


class PhotoScanner:
    """Scans directories for valid image files.

    Entry point for the services layer — discovers what photos are available for processing. Walks the directory
    tree recursively, filters by configured image extensions, and returns sorted absolute paths.

    Supports excluding directories to prevent scanning output folders or other unwanted locations.

    Usage:
        scanner = PhotoScanner(config)
        paths = scanner.scan("/photos/wedding")                              # all images
        paths = scanner.scan("/photos/wedding", exclude_dirs=["/output"])    # skip output folder
        summary = scanner.get_scan_summary(paths)                            # {"total": 5000, ".jpg": 4200}
    """

    def __init__(self, config: AppConfig) -> None:
        """Initialize with application configuration.

        Args:
            config: Application configuration (provides image_extensions).
        """
        self._extensions = config.image_extensions

    def scan(self, directory: str, exclude_dirs: list[str] = None) -> list[str]:
        """Recursively scan a directory for valid image files.

        Args:
            directory: Path to the directory to scan.
            exclude_dirs: Optional list of directory paths to skip entirely.

        Returns:
            Sorted list of absolute file paths for valid images. Empty list if directory doesn't exist.
        """
        dir_path = Path(directory)

        if not dir_path.is_dir():
            logger.error(f"Directory not found: {directory}")
            return []

        excluded = {Path(d).resolve() for d in exclude_dirs} if exclude_dirs else set()

        file_paths = [
            str(file.resolve())
            for file in dir_path.rglob("*")
            if file.is_file()
            and not self._is_under_excluded(file, excluded)
            and is_valid_image(str(file), self._extensions)
        ]

        file_paths.sort()

        logger.info(f"Scanned {directory}: found {len(file_paths)} valid images")

        return file_paths

    def scan_non_recursive(self, directory: str) -> list[str]:
        """Scan only the top-level of a directory for valid image files.

        Does not descend into subfolders. Useful when the source folder contains subfolders that should
        be excluded.

        Args:
            directory: Path to the directory to scan.

        Returns:
            Sorted list of absolute file paths for valid images. Empty list if directory doesn't exist.
        """
        dir_path = Path(directory)

        if not dir_path.is_dir():
            logger.error(f"Directory not found: {directory}")
            return []

        file_paths = [
            str(file.resolve())
            for file in dir_path.iterdir()
            if file.is_file() and is_valid_image(str(file), self._extensions)
        ]

        file_paths.sort()

        logger.info(f"Scanned {directory} (non-recursive): found {len(file_paths)} valid images")

        return file_paths

    def get_scan_summary(self, file_paths: list[str]) -> dict[str, int]:
        """Get a summary of scanned files by extension.

        Args:
            file_paths: List of image file paths from a scan.

        Returns:
            Dictionary with extension counts and total count.
            Example: {"total": 5000, ".jpg": 4200, ".png": 800}
        """
        counts = dict(Counter(Path(p).suffix.lower() for p in file_paths))
        counts["total"] = len(file_paths)

        return counts

    @staticmethod
    def _is_under_excluded(file_path: Path, excluded: set[Path]) -> bool:
        """Check if a file is inside any excluded directory.

        Args:
            file_path: Path to the file.
            excluded: Set of resolved excluded directory paths.

        Returns:
            True if the file is under an excluded directory.
        """
        if not excluded:
            return False

        resolved = file_path.resolve()

        for exc_dir in excluded:
            try:
                resolved.relative_to(exc_dir)
                return True
            except ValueError:
                continue

        return False