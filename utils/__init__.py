##########################################################################################################################
# Author: Nishanth Marer Prabhu
# fileName: __init__.py (utils)
# Description: Public API for the utils package. Exposes logging, image loading, file utilities, content fingerprinting,
#              cache filename generation, and size formatting used across all layers of the application.
# Year: 2026
###########################################################################################################################

from utils.logger import setup_logger
from utils.image_utils import load_image, is_valid_image, get_image_dimensions
from utils.file_utils import (
    compute_fingerprint,
    compute_cache_filename,
    create_output_folder,
    copy_photo,
    sanitize_folder_name,
    human_readable_size,
)

__all__ = [
    "setup_logger",
    "load_image",
    "is_valid_image",
    "get_image_dimensions",
    "compute_fingerprint",
    "compute_cache_filename",
    "create_output_folder",
    "copy_photo",
    "sanitize_folder_name",
    "human_readable_size",
]