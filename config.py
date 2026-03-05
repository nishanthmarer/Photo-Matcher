##########################################################################################################################
# Author: Nishanth Marer Prabhu
# fileName: config.py
# Description: Centralized application configuration using Python dataclasses. All tunable parameters live here —
#              ML settings (detection size, confidence, embedding dimensions), processing controls (workers, queue
#              sizes, cache intervals), logging, UI dimensions, image review settings, and supported image formats.
#              Each module receives only the sub-config it needs via the top-level AppConfig.
# Year: 2026
###########################################################################################################################

import logging
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Core — ML related configuration
# ---------------------------------------------------------------------------

@dataclass
class DetectionConfig:
    """Configuration for RetinaFace face detection.

    model_root is the base directory passed to InsightFace. Models will be stored at:
    {model_root}/models/{model_name}/ (e.g., ./models/buffalo_l/)
    """
    model_name: str = "buffalo_l"
    confidence_threshold: float = 0.5
    gpu_id: int = 0
    det_size: tuple[int, int] = (1280, 1280)
    model_root: str = "."


@dataclass
class EmbeddingConfig:
    """Configuration for ArcFace embedding extraction."""
    embedding_size: int = 512


@dataclass
class MatchingConfig:
    """Configuration for face matching."""
    distance_threshold: float = 0.4
    min_face_percent: float = 0.2


@dataclass
class ProcessingConfig:
    """Configuration for batch processing and parallelization."""
    gpu_enabled: bool = True
    num_workers: int = 8
    queue_max_size: int = 8
    producer_chunk_size: int = 32
    cache_save_interval: int = 100
    gpu_reload_interval: int = 500


# ---------------------------------------------------------------------------
# Utils — Logging configuration
# ---------------------------------------------------------------------------

@dataclass
class LoggingConfig:
    """Configuration for application logging."""
    log_format: str = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    log_file: str = "photo_matcher.log"
    log_level: int = logging.INFO


# ---------------------------------------------------------------------------
# Services — Caching configuration
# ---------------------------------------------------------------------------

@dataclass
class CacheConfig:
    """Configuration for embedding cache.

    Cache files are stored in a dedicated directory. Each source folder gets its own cache file,
    named after the source folder for human readability with a short hash of the folder name for
    platform-independent consistency.

    Example: photo_cache/Cam_1-20260218T100635Z-1-001_a3f2e1b0_cache.pkl

    fingerprint_chunk_size controls how many bytes are read from the head and tail of each file
    to compute the content fingerprint. 64KB is sufficient for DSLR photos since EXIF headers
    alone provide unique identification.
    """
    cache_dir: str = "photo_cache"
    fingerprint_chunk_size: int = 65536  # 64KB head + 64KB tail


# ---------------------------------------------------------------------------
# UI — Interface configuration
# ---------------------------------------------------------------------------

@dataclass
class UIConfig:
    """Configuration for the PySide6 user interface."""
    window_title: str = "Photo Matcher"
    window_width: int = 1200
    window_height: int = 800


@dataclass
class ReviewConfig:
    """Configuration for the image review dialog."""
    window_title: str = "Image Review"
    window_width: int = 1000
    window_height: int = 750


# ---------------------------------------------------------------------------
# Top-level — Aggregates all sub-configurations
# ---------------------------------------------------------------------------

@dataclass
class AppConfig:
    """Top-level application configuration.

    Aggregates all sub-configurations into a single entry point.
    Each module receives only the sub-config it needs.
    """
    detection: DetectionConfig = field(default_factory=DetectionConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    matching: MatchingConfig = field(default_factory=MatchingConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    review: ReviewConfig = field(default_factory=ReviewConfig)
    image_extensions: frozenset = frozenset(
        {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}
    )