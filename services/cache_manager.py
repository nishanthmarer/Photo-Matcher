##########################################################################################################################
# Author: Nishanth Marer Prabhu
# fileName: cache_manager.py
# Description: Content-addressed embedding cache for incremental photo processing. Stores face embeddings keyed by
#              content fingerprint (SHA-256 of file size + head 64KB + tail 64KB) so the cache is fully portable
#              across drives, folders, and operating systems. Each source folder gets its own cache file inside
#              the photo_cache/ directory, named after the folder for human readability. Config-based versioning
#              ensures the cache is invalidated when ML settings change.
# Year: 2026
###########################################################################################################################

import hashlib
import json
import pickle
from pathlib import Path

from config import CacheConfig, AppConfig, LoggingConfig
from utils.file_utils import compute_fingerprint, compute_cache_filename
from utils.logger import setup_logger

logger = setup_logger("services.cache_manager", LoggingConfig())


class CacheManager:
    """Stores and loads face embeddings to disk for incremental processing.

    The cache maps content fingerprints to their detected face data (bounding boxes + embeddings). On each run,
    only photos whose fingerprint is not already cached go through ML inference — cached results are reused.

    Content fingerprints are derived from the file's actual bytes (size + head + tail), not its path. This means:
    - Moving a photo to a different folder/drive → cache still hits
    - Renaming a photo → cache still hits
    - Copying the cache from Windows to Linux → still works
    - Editing a photo (crop, filter, re-save) → fingerprint changes → correctly reprocessed

    Each source folder gets its own cache file inside the cache directory, named after the folder for readability:
        photo_cache/Cam_1-20260218T100635Z-1-001_a3f2e1b0_cache.pkl

    Config versioning ensures cache validity. A hash is computed from ML settings (det_size, confidence, embedding
    size). If settings change between runs, the cache is discarded because embeddings generated with different
    settings are incompatible.

    An in-memory path-to-fingerprint mapping is built during each run to avoid redundant fingerprint computation
    between the processing phase (which photos are new?) and the matching phase (look up embeddings by path).

    Usage:
        cache = CacheManager(cache_config, app_config)
        cache.load_for_source(source_dir)
        uncached = cache.get_uncached_photos(photo_paths)   # returns [(path, fingerprint), ...]
        # ... process uncached photos through ML pipeline ...
        cache.put(fingerprint, filename, faces, image_shape)
        cache.save()
        # ... during matching phase ...
        entry = cache.get_by_path(photo_path)               # uses cached path→fingerprint mapping
    """

    def __init__(self, config: CacheConfig, app_config: AppConfig) -> None:
        """Initialize cache manager without loading any cache from disk.

        Cache is loaded lazily when a source folder is selected via load_for_source().

        Args:
            config: Cache configuration (cache directory, fingerprint chunk size).
            app_config: Full app configuration — used to compute version hash from ML settings.
        """
        self._cache_dir = Path(config.cache_dir)
        self._chunk_size = config.fingerprint_chunk_size
        self._config_hash = self._compute_config_hash(app_config)
        self._current_source: str | None = None
        self._cache_path: Path | None = None
        self._cache: dict = {}
        self._path_to_fingerprint: dict[str, str] = {}
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
        """Load the cache file for a given source directory.

        Computes the cache filename from the source folder name, then loads the matching file from
        the cache directory. If the file doesn't exist or the config hash doesn't match, starts fresh.

        If already loaded for the same source, returns immediately without reloading.

        Args:
            source_dir: Path to the source photo directory.

        Returns:
            True if a valid cache was loaded, False if starting fresh.
        """
        if self._loaded and self._current_source == source_dir:
            return bool(self._cache)

        self._current_source = source_dir
        self._cache = {}
        self._path_to_fingerprint = {}
        self._loaded = False

        # Compute cache file path
        cache_filename = compute_cache_filename(source_dir)
        self._cache_path = self._cache_dir / cache_filename

        if not self._cache_path.exists():
            logger.info(f"No cache file found at {self._cache_path}")
            return False

        try:
            with open(self._cache_path, "rb") as f:
                data = pickle.load(f)

            # Validate config hash — if ML settings changed, embeddings are invalid
            cached_hash = data.get("_config_hash", None)
            if cached_hash != self._config_hash:
                logger.warning(
                    f"Cache config mismatch (cached: {cached_hash}, current: {self._config_hash}). "
                    f"Discarding cache — all photos will be reprocessed."
                )
                return False

            cache = data.get("entries", {})
            self._cache = cache
            self._loaded = True
            logger.info(f"Loaded cache with {len(cache)} entries from {cache_filename}")
            return True

        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")
            return False

    def save(self) -> None:
        """Write current cache to disk with config version stamp.

        Creates the cache directory if it doesn't exist. The cache file is named after the
        source folder for human readability.
        """
        if self._cache_path is None:
            logger.warning("Cannot save — no source loaded")
            return

        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)

            data = {
                "_config_hash": self._config_hash,
                "entries": self._cache,
            }

            with open(self._cache_path, "wb") as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)

            self._loaded = True
            logger.info(f"Saved cache with {len(self._cache)} entries to {self._cache_path.name}")

        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    # ------------------------------------------------------------------------------------------------------------------
    # Fingerprint computation and lookup
    # ------------------------------------------------------------------------------------------------------------------

    def get_uncached_photos(self, photo_paths: list[str]) -> list[tuple[str, str]]:
        """Identify photos that need processing by computing content fingerprints.

        For each photo, computes a content fingerprint and checks if it exists in the cache.
        Photos whose fingerprint is already cached are skipped. Also builds an in-memory
        path-to-fingerprint mapping for use during the matching phase (avoids recomputing).

        Args:
            photo_paths: Full list of scanned photo paths.

        Returns:
            List of (photo_path, fingerprint) tuples for photos not in cache.
            Photos that fail fingerprinting are included with a generated fallback fingerprint.
        """
        self._path_to_fingerprint = {}
        uncached = []
        cached_count = 0
        failed_count = 0

        for path in photo_paths:
            fingerprint = compute_fingerprint(path, self._chunk_size)

            if fingerprint is None:
                # Fingerprinting failed (unreadable file) — skip this photo
                failed_count += 1
                continue

            self._path_to_fingerprint[path] = fingerprint

            if fingerprint in self._cache:
                cached_count += 1
            else:
                uncached.append((path, fingerprint))

        logger.info(
            f"Fingerprint check: {len(photo_paths)} total, "
            f"{len(uncached)} new, {cached_count} cached, {failed_count} unreadable"
        )

        return uncached

    def get(self, fingerprint: str) -> dict | None:
        """Look up a cached entry by its content fingerprint.

        Args:
            fingerprint: 16-character hex fingerprint string.

        Returns:
            Cached data dict with keys (filename, faces, image_shape), or None if not cached.
        """
        return self._cache.get(fingerprint)

    def get_by_path(self, photo_path: str) -> dict | None:
        """Look up a cached entry by file path.

        Uses the in-memory path-to-fingerprint mapping built during get_uncached_photos() for fast
        lookup. If the mapping doesn't contain this path (e.g., path wasn't in the original scan),
        computes the fingerprint on the fly.

        Args:
            photo_path: Absolute path to the photo file.

        Returns:
            Cached data dict with keys (filename, faces, image_shape), or None if not cached.
        """
        fingerprint = self._path_to_fingerprint.get(photo_path)

        if fingerprint is None:
            # Path wasn't in the original scan — compute fingerprint on the fly
            fingerprint = compute_fingerprint(photo_path, self._chunk_size)
            if fingerprint is None:
                return None
            self._path_to_fingerprint[photo_path] = fingerprint

        return self._cache.get(fingerprint)

    def put(self, fingerprint: str, filename: str, faces: list[dict],
            image_shape: tuple[int, int] = None) -> None:
        """Store processed data for a single photo, keyed by content fingerprint.

        Args:
            fingerprint: 16-character hex fingerprint identifying the file's content.
            filename: Original filename (e.g., "IMG_001.jpg") for traceability during copy operations.
            faces: List of face dicts, each with 'bbox' and 'embedding' keys.
            image_shape: Tuple of (height, width) of the original image. Used for min_face_percent filtering.
        """
        self._cache[fingerprint] = {
            "filename": filename,
            "faces": faces,
            "image_shape": image_shape,
        }

    # ------------------------------------------------------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------------------------------------------------------

    def clear(self) -> None:
        """Delete the cache file for the current source from memory and disk."""
        self._cache.clear()
        self._path_to_fingerprint.clear()
        self._current_source = None
        self._loaded = False

        if self._cache_path is not None and self._cache_path.exists():
            self._cache_path.unlink()
            logger.info(f"Cache cleared: {self._cache_path.name}")

        self._cache_path = None

    def clear_all(self) -> None:
        """Delete all cache files from the cache directory.

        Removes every .pkl file in the cache directory, then removes the directory itself if empty.
        """
        self._cache.clear()
        self._path_to_fingerprint.clear()
        self._current_source = None
        self._cache_path = None
        self._loaded = False

        if self._cache_dir.exists():
            deleted = 0
            for pkl_file in self._cache_dir.glob("*_cache.pkl"):
                try:
                    pkl_file.unlink()
                    deleted += 1
                except OSError as e:
                    logger.error(f"Failed to delete {pkl_file.name}: {e}")

            # Remove directory if empty
            try:
                if self._cache_dir.exists() and not any(self._cache_dir.iterdir()):
                    self._cache_dir.rmdir()
            except OSError:
                pass

            logger.info(f"Cleared all caches: {deleted} files deleted")

    def is_valid_for_source(self, source_dir: str) -> bool:
        """Check if the cache is loaded and has entries for the given source directory.

        Args:
            source_dir: Path to the source directory to check against.

        Returns:
            True if cache is loaded, non-empty, and was loaded for this source directory.
        """
        return self._loaded and bool(self._cache) and self._current_source == source_dir

    def get_fingerprint_for_path(self, photo_path: str) -> str | None:
        """Get the fingerprint for a path from the in-memory mapping.

        Returns the cached mapping if available, otherwise computes it.

        Args:
            photo_path: Absolute path to the photo file.

        Returns:
            16-character hex fingerprint, or None if the file cannot be read.
        """
        fingerprint = self._path_to_fingerprint.get(photo_path)

        if fingerprint is None:
            fingerprint = compute_fingerprint(photo_path, self._chunk_size)
            if fingerprint is not None:
                self._path_to_fingerprint[photo_path] = fingerprint

        return fingerprint

    @property
    def source_dir(self) -> str | None:
        """The source directory this cache was loaded for, or None."""
        return self._current_source

    @property
    def size(self) -> int:
        """Number of entries in the cache."""
        return len(self._cache)

    @property
    def cache_dir(self) -> str:
        """Path to the cache directory."""
        return str(self._cache_dir)