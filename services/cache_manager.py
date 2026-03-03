##########################################################################################################################
# Author: Nishanth Marer Prabhu
# fileName: cache_manager.py
# Description: Embedding cache for incremental photo processing. Stores face embeddings and bounding boxes to disk
#              (pickle) so unchanged photos skip ML inference on subsequent runs. Tracks file modification time and
#              size to detect changes. Includes config-based versioning — if detection settings (det_size, confidence
#              threshold) change, the entire cache is invalidated and rebuilt from scratch.
# Year: 2026
###########################################################################################################################

import hashlib
import json
import os
import pickle
from pathlib import Path

from config import CacheConfig, AppConfig, LoggingConfig
from utils.logger import setup_logger

logger = setup_logger("services.cache_manager", LoggingConfig())


class CacheManager:
    """Stores and loads face embeddings to disk for incremental processing.

    The cache maps photo file paths to their detected face data (bounding boxes + embeddings). On each run,
    only new or modified photos go through ML inference — cached results are reused directly.

    Staleness detection uses file modification time and size. If either changes, the photo is reprocessed.

    Config versioning ensures cache validity. A hash is computed from detection settings (det_size, confidence
    threshold, embedding size). If settings change between runs, the entire cache is discarded because
    embeddings generated with different settings are incompatible.

    Uses pickle for serialization — handles numpy arrays natively.

    Usage:
        cache = CacheManager(cache_config, app_config)
        if cache.is_stale(photo_path):
            # process photo, then:
            cache.put(photo_path, mtime, size, faces)
        else:
            faces = cache.get(photo_path)["faces"]
        cache.save()
    """

    def __init__(self, config: CacheConfig, app_config: AppConfig) -> None:
        """Initialize cache manager without loading any cache from disk.

        Cache is loaded lazily when a source folder is selected via load_for_source().

        Args:
            config: Cache configuration (cache file path).
            app_config: Full app configuration — used to compute version hash from detection settings.
        """
        self._cache_path = Path(config.cache_file)
        self._config_hash = self._compute_config_hash(app_config)
        self._source_dir = None
        self._cache: dict = {}
        self._loaded = False

    def _compute_config_hash(self, config: AppConfig) -> str:
        """Compute a hash from config values that affect cached embeddings.

        If any of these values change, cached embeddings are invalid and must be regenerated.

        Args:
            config: Full application configuration.

        Returns:
            SHA256 hex digest string (first 16 chars for readability).
        """
        versioned_values = {
            "det_size": config.detection.det_size,
            "confidence_threshold": config.detection.confidence_threshold,
            "embedding_size": config.embedding.embedding_size,
            "model_name": config.detection.model_name,
        }

        raw = json.dumps(versioned_values, sort_keys=True)

        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def load_for_source(self, source_dir: str) -> bool:
        """Load cache from disk and validate it matches the given source folder.

        This is the only way cache gets loaded from disk. Called when the user selects a source folder.
        If already loaded for the same source, returns immediately without reloading.
        If the cache file exists and matches both the config hash and source directory, it is loaded.
        Otherwise, starts with an empty cache.

        Args:
            source_dir: Path to the source photo directory.

        Returns:
            True if a valid cache is available, False if starting fresh.
        """
        # Already loaded for this source — don't reload
        if self._loaded and self._source_dir == source_dir:
            return bool(self._cache)

        self._source_dir = source_dir
        self._cache = {}
        self._loaded = False

        if not self._cache_path.exists():
            logger.info("No cache file found on disk")
            return False

        try:
            with open(self._cache_path, "rb") as f:
                data = pickle.load(f)

            # Validate config hash
            cached_hash = data.get("_config_hash", None)
            if cached_hash != self._config_hash:
                logger.warning(
                    f"Cache config mismatch (cached: {cached_hash}, current: {self._config_hash}). "
                    f"Discarding cache — all photos will be reprocessed."
                )
                return False

            # Validate source directory
            cached_source = data.get("_source_dir", None)
            if cached_source != source_dir:
                logger.warning(
                    f"Cache source mismatch (cached: {cached_source}, selected: {source_dir}). "
                    f"Discarding cache — all photos will be reprocessed."
                )
                return False

            cache = data.get("entries", {})
            self._cache = cache
            self._loaded = True
            logger.info(f"Loaded cache with {len(cache)} entries for {source_dir}")
            return True

        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")
            return False

    def save(self) -> None:
        """Write current cache to disk with config version stamp and source directory."""
        try:
            data = {
                "_config_hash": self._config_hash,
                "_source_dir": self._source_dir,
                "entries": self._cache,
            }

            with open(self._cache_path, "wb") as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)

            self._loaded = True
            logger.info(f"Saved cache with {len(self._cache)} entries")

        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    def get(self, photo_path: str) -> dict | None:
        """Look up a single photo in the cache.

        Args:
            photo_path: Absolute path to the photo.

        Returns:
            Cached data dict with keys (modified_time, file_size, faces), or None if not cached.
        """
        return self._cache.get(photo_path)

    def put(self, photo_path: str, modified_time: float, file_size: int,
            faces: list[dict], image_shape: tuple[int, int] = None) -> None:
        """Store processed data for a single photo.

        Args:
            photo_path: Absolute path to the photo.
            modified_time: File's last modification timestamp.
            file_size: File size in bytes.
            faces: List of face dicts, each with 'bbox' and 'embedding' keys.
            image_shape: Tuple of (height, width) of the original image. Used for min_face_percent filtering.
        """
        self._cache[photo_path] = {
            "modified_time": modified_time,
            "file_size": file_size,
            "faces": faces,
            "image_shape": image_shape,
        }

    def is_stale(self, photo_path: str) -> bool:
        """Check if a cached entry is outdated or missing.

        Compares cached modified_time and file_size against the current file on disk.

        Args:
            photo_path: Absolute path to the photo.

        Returns:
            True if the file needs reprocessing (changed, new, or missing from disk).
        """
        cached = self._cache.get(photo_path)

        if cached is None:
            return True

        try:
            stat = os.stat(photo_path)

            if stat.st_mtime != cached["modified_time"]:
                return True

            if stat.st_size != cached["file_size"]:
                return True

            return False

        except OSError as e:
            logger.warning(f"Cannot stat file {photo_path}: {e}")
            return True

    def get_stale_and_new(self, photo_paths: list[str]) -> tuple[list[str], list[str]]:
        """Identify photos that need processing.

        Separates photos into those that are stale (modified since last cache) and those that are completely
        new (not in cache at all).

        Args:
            photo_paths: Full list of scanned photo paths.

        Returns:
            Tuple of (stale_paths, new_paths).
        """
        stale = []
        new = []

        for path in photo_paths:
            cached = self._cache.get(path)

            if cached is None:
                new.append(path)
            elif self.is_stale(path):
                stale.append(path)

        logger.info(
            f"Cache check: {len(photo_paths)} total, "
            f"{len(new)} new, {len(stale)} stale, "
            f"{len(photo_paths) - len(new) - len(stale)} cached"
        )

        return stale, new

    def clear(self) -> None:
        """Delete all cached data from memory and disk."""
        self._cache.clear()
        self._source_dir = None
        self._loaded = False

        if self._cache_path.exists():
            self._cache_path.unlink()

        logger.info("Cache cleared")

    def is_valid_for_source(self, source_dir: str) -> bool:
        """Check if the cache is loaded and was built for the given source directory.

        Args:
            source_dir: Path to the source directory to check against.

        Returns:
            True if cache is loaded, non-empty, and matches this source directory.
        """
        return self._loaded and bool(self._cache) and self._source_dir == source_dir

    @property
    def source_dir(self) -> str | None:
        """The source directory this cache was built for, or None."""
        return self._source_dir

    @property
    def size(self) -> int:
        """Number of entries in the cache."""
        return len(self._cache)