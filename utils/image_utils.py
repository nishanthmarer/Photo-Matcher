##########################################################################################################################
# Author: Nishanth Marer Prabhu
# fileName: image_utils.py
# Description: Image loading and manipulation utilities. Handles loading images from disk, image validation,
#              and dimension queries. Uses OpenCV for all pixel operations.
# Year: 2026
###########################################################################################################################

from pathlib import Path

import cv2
import numpy as np

from config import LoggingConfig
from utils.logger import setup_logger

logger = setup_logger("utils.image_utils", LoggingConfig())


def load_image(path: str) -> np.ndarray | None:
    """Load an image from disk as a BGR numpy array.

    Args:
        path: File path to the image.

    Returns:
        BGR image as numpy array, or None if loading fails.
    """
    try:
        image = cv2.imread(path, cv2.IMREAD_COLOR)

        if image is None:
            logger.warning(f"Failed to load image: {path}")
            return None

        return image

    except Exception as e:
        logger.error(f"Error loading image {path}: {e}")
        return None


def is_valid_image(path: str, extensions: frozenset) -> bool:
    """Check if a file has a valid image extension.

    Args:
        path: File path to check.
        extensions: Set of allowed extensions (e.g., {".jpg", ".png"}).

    Returns:
        True if the file extension is in the allowed set.
    """
    suffix = Path(path).suffix.lower()

    return suffix in extensions


def get_image_dimensions(image: np.ndarray) -> tuple[int, int]:
    """Get image dimensions as (height, width).

    Args:
        image: Image as numpy array.

    Returns:
        Tuple of (height, width).
    """
    return image.shape[:2]