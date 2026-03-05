##########################################################################################################################
# Author: Nishanth Marer Prabhu
# fileName: segregator.py
# Description: Main orchestrator — coordinates all services and core modules. Single entry point for the UI layer.
#              Provides two main operations:
#              1. Build Cache: scan → fingerprint → ML inference on uncached photos
#              2. Generate Folders: build FAISS index → match embeddings → copy matched photos
#              Uses content-based fingerprinting so the cache is fully portable across drives and operating systems.
#              Supports incremental output (skips already-copied files), graceful stopping via stop events,
#              and post-run cleanup to free memory.
# Year: 2026
###########################################################################################################################

import gc
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from queue import Queue
from threading import Thread, Event
from typing import Callable, Optional

from config import AppConfig, LoggingConfig
from core.pipeline import FacePipeline
from core.indexer import FaceIndexer
from services.photo_scanner import PhotoScanner
from services.cache_manager import CacheManager
from services.reference_manager import ReferenceManager
from utils.image_utils import load_image
from utils.file_utils import copy_photo, create_output_folder, sanitize_folder_name
from utils.logger import setup_logger

logger = setup_logger("services.segregator", LoggingConfig())


class Segregator:
    """Main orchestrator — coordinates all services and core modules.

    Single entry point for the UI layer. Provides two independent operations:

    1. Build Cache (process_photos): scan source folder → compute content fingerprints → run ML inference
       on photos not already cached. Results are saved to disk, keyed by content fingerprint so the cache
       is fully portable across drives, folders, and operating systems.

    2. Generate Folders (match_and_copy): match cached embeddings against references → copy to person folders.
       This is fast (~seconds). Can be re-run after adding new persons without rebuilding the cache.

    Both operations support:
    - Graceful stopping via stop events (one per operation).
    - Status callbacks for real-time UI updates.
    - Incremental output — only new matches are copied.

    Usage:
        segregator = Segregator(config)
        segregator.add_reference("Alice", "alice_ref.jpg")
        segregator.process_photos(source_dir, progress_cb, status_cb)     # Build cache
        segregator.match_and_copy(source_dir, output_dir, status_cb)      # Generate folders
    """

    def __init__(self, config: AppConfig) -> None:
        """Initialize all components from application configuration.

        Args:
            config: Top-level application configuration.
        """
        self._config = config
        self._pipeline = FacePipeline(config)
        self._scanner = PhotoScanner(config)
        self._cache = CacheManager(config.cache, config)
        self._reference_manager = ReferenceManager(self._pipeline)
        self._indexer = FaceIndexer(config.embedding)
        self._cache_stop = Event()
        self._generate_stop = Event()

    # ------------------------------------------------------------------------------------------------------------------
    # Reference management — public API for enrolling/removing persons
    # ------------------------------------------------------------------------------------------------------------------

    def add_reference(self, person_name: str, image_path: str) -> bool:
        """Enroll a single reference photo for a person.

        Args:
            person_name: Name of the person.
            image_path: Path to the reference photo.

        Returns:
            True if enrollment succeeded.
        """
        self._ensure_pipeline_loaded()
        return self._reference_manager.enroll(person_name, image_path)

    def add_references(self, person_name: str, image_paths: list[str]) -> int:
        """Enroll multiple reference photos for a person.

        Args:
            person_name: Name of the person.
            image_paths: List of reference photo paths.

        Returns:
            Number of successfully enrolled photos.
        """
        self._ensure_pipeline_loaded()
        return self._reference_manager.enroll_multiple(person_name, image_paths)

    def remove_reference(self, person_name: str) -> bool:
        """Remove a person and all their reference embeddings.

        Args:
            person_name: Name of the person to remove.

        Returns:
            True if found and removed, False if not found.
        """
        return self._reference_manager.remove_person(person_name)

    # ------------------------------------------------------------------------------------------------------------------
    # Stop control — separate stop events for each operation
    # ------------------------------------------------------------------------------------------------------------------

    def request_cache_stop(self) -> None:
        """Request graceful stop of cache building. Thread-safe."""
        logger.info("Cache stop requested by user")
        self._cache_stop.set()

    def request_generate_stop(self) -> None:
        """Request graceful stop of folder generation. Thread-safe."""
        logger.info("Generate stop requested by user")
        self._generate_stop.set()

    def reset_cache_stop(self) -> None:
        """Reset the cache stop flag for a new run."""
        self._cache_stop.clear()

    def reset_generate_stop(self) -> None:
        """Reset the generate stop flag for a new run."""
        self._generate_stop.clear()

    # ------------------------------------------------------------------------------------------------------------------
    # Operation 1 — Build Cache (process photos through ML pipeline)
    # ------------------------------------------------------------------------------------------------------------------

    def process_photos(
        self,
        source_dir: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        status_callback: Optional[Callable[[str], None]] = None,
        exclude_dirs: list[str] = None
    ) -> dict:
        """Scan and process photos through the ML pipeline, saving results to cache.

        This is the expensive operation. Each uncached photo goes through detect → align → embed.
        Photos whose content fingerprint is already cached are skipped. Progress and status callbacks
        keep the UI updated.

        Args:
            source_dir: Path to the source photo directory.
            progress_callback: Optional callback(current, total, filename) for progress bar updates.
            status_callback: Optional callback(message) for status bar updates.
            exclude_dirs: Optional list of directory paths to skip during scanning.

        Returns:
            Summary dict with processing statistics.
        """
        if status_callback:
            status_callback("Scanning source folder...")

        # Ensure ML models are loaded (reloads if released after previous run)
        self._ensure_pipeline_loaded()

        # Ensure cache is ready for this source (loads from disk if needed, no-op if already loaded)
        self._cache.load_for_source(source_dir)

        all_paths = self._scanner.scan(source_dir, exclude_dirs=exclude_dirs)

        if not all_paths:
            logger.warning(f"No valid images found in {source_dir}")
            if status_callback:
                status_callback("No valid images found")
            return {
                "total_scanned": 0,
                "new_processed": 0,
                "cached_skipped": 0,
            }

        if status_callback:
            status_callback(f"Computing fingerprints for {len(all_paths):,} photos...")

        # Compute fingerprints and identify which photos need processing
        uncached = self._cache.get_uncached_photos(all_paths)
        cached_count = len(all_paths) - len(uncached)

        if status_callback:
            status_callback(
                f"Found {len(all_paths):,} images — "
                f"{len(uncached):,} new, {cached_count:,} cached"
            )

        logger.info(
            f"Processing {len(uncached)} photos "
            f"({len(uncached)} new, {cached_count} cached)"
        )

        actually_processed = 0
        if uncached:
            if status_callback:
                status_callback(f"Processing {len(uncached):,} photos...")
            actually_processed = self._process_with_producer_consumer(uncached, progress_callback)

        self._cache.save()

        summary = {
            "total_scanned": len(all_paths),
            "new_processed": len(uncached),
            "cached_skipped": cached_count,
            "stopped_early": self._cache_stop.is_set(),
            "actually_processed": actually_processed,
        }

        if self._cache_stop.is_set():
            if status_callback:
                status_callback(f"Cache stopped — {actually_processed:,} photos saved")
        else:
            if status_callback:
                status_callback(f"Cache complete — {len(all_paths):,} photos processed")

        logger.info(f"Processing complete: {summary}")

        # Release GPU memory — models reload on next operation
        self._pipeline.release()
        gc.collect()
        logger.info("GPU memory released after cache build")

        return summary

    # ------------------------------------------------------------------------------------------------------------------
    # Operation 2 — Generate Folders (match cached embeddings + copy files)
    # ------------------------------------------------------------------------------------------------------------------

    def match_and_copy(
        self,
        source_dir: str,
        output_dir: str,
        status_callback: Optional[Callable[[str], None]] = None,
        match_progress_callback: Optional[Callable[[int, int, str], None]] = None,
        copy_progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> dict:
        """Match cached face embeddings against references and copy matched photos.

        This is the fast operation (~seconds). Requires that process_photos() has been run first to
        populate the cache. Can be re-run after adding/removing persons without rebuilding the cache.

        Phases:
        1. Build FAISS index from reference embeddings.
        2. Compute fingerprints for all scanned photos (uses cached mapping if available).
        3. Search every cached face against the index.
        4. Copy matched photos to per-person output folders (incremental — skips existing).
        5. Cleanup FAISS index.

        Args:
            source_dir: Path to the source photo directory.
            output_dir: Path to the output directory.
            status_callback: Optional callback(message) for status bar updates.
            match_progress_callback: Optional callback(current, total, filename) for match progress.
            copy_progress_callback: Optional callback(current, total, filename) for copy progress.

        Returns:
            Summary dict with per-person copy counts.
        """
        persons = self._reference_manager.get_all_persons()

        if not persons:
            logger.error("No reference faces enrolled. Cannot generate folders.")
            return {"error": "No reference faces enrolled"}

        # Phase 1 — Build reference index
        if status_callback:
            status_callback("Building reference index...")

        self._build_reference_index(persons)

        if self._generate_stop.is_set():
            return {"stopped": True}

        # Phase 2 — Match cached embeddings against references
        if status_callback:
            status_callback("Matching faces against cached photos...")

        exclude = [output_dir]
        all_paths = self._scanner.scan(source_dir, exclude_dirs=exclude)
        matches: dict[str, set] = {name: set() for name in persons}
        threshold = self._config.matching.distance_threshold

        matched_count = 0
        total_photos = len(all_paths)
        min_face_pct = self._config.matching.min_face_percent

        for idx, photo_path in enumerate(all_paths):
            if self._generate_stop.is_set():
                break

            # Look up cached data using path → fingerprint → cache
            cached = self._cache.get_by_path(photo_path)

            if cached is None:
                continue

            faces = cached["faces"]

            if not faces:
                continue

            # Get image dimensions for face size filtering (graceful fallback for old caches)
            image_shape = cached.get("image_shape")

            for face_data in faces:
                # Filter by min face size if image dimensions are available
                if image_shape is not None and min_face_pct > 0:
                    bbox = face_data["bbox"]
                    face_width = float(bbox[2] - bbox[0])
                    face_height = float(bbox[3] - bbox[1])
                    face_area = face_width * face_height
                    image_area = float(image_shape[0] * image_shape[1])
                    face_percent = (face_area / image_area) * 100.0

                    if face_percent < min_face_pct:
                        continue

                results = self._indexer.search(face_data["embedding"], threshold)

                for result in results:
                    matches[result.photo_path].add(photo_path)
                    matched_count += 1

            if match_progress_callback:
                match_progress_callback(idx + 1, total_photos, photo_path)

        if self._generate_stop.is_set():
            return {"stopped": True}

        if status_callback:
            total_matches = sum(len(paths) for paths in matches.values())
            status_callback(f"Found {total_matches:,} matches — copying to folders...")

        # Phase 3 — Copy results (incremental, skip existing)
        summary = self._copy_results(matches, output_dir, status_callback, copy_progress_callback)

        total_copied = sum(summary.values())

        if status_callback:
            if total_copied == 0:
                status_callback("All up to date — no new photos to copy")
            else:
                status_callback(f"Complete — {total_copied:,} photos copied across {len(persons)} persons")

        logger.info(f"Generate folders complete: {summary}")

        # Phase 4 — Cleanup
        self._post_run_cleanup()

        return summary

    def get_status(self) -> dict:
        """Get current application state.

        Returns:
            Dict with enrolled person count, reference counts per person.
        """
        persons = self._reference_manager.get_all_persons()

        reference_counts = {
            name: self._reference_manager.get_embedding_count(name)
            for name in persons
        }

        return {
            "enrolled_persons": len(persons),
            "persons": persons,
            "reference_counts": reference_counts,
        }

    def has_cache_for_source(self, source_dir: str) -> bool:
        """Check if a valid cache exists for the given source directory.

        Triggers lazy loading from disk — this is the first time cache is read.

        Args:
            source_dir: Path to the source directory.

        Returns:
            True if cache was loaded for this source and has entries.
        """
        self._cache.load_for_source(source_dir)
        return self._cache.is_valid_for_source(source_dir)

    def get_cache_size(self) -> int:
        """Get the number of cached photo entries."""
        return self._cache.size

    def clear_cache(self) -> None:
        """Clear the embedding cache for the current source from memory and disk."""
        self._cache.clear()
        logger.info("Cache cleared by user")

    def clear_all_caches(self) -> None:
        """Clear all cache files from the cache directory."""
        self._cache.clear_all()
        logger.info("All caches cleared by user")

    # ------------------------------------------------------------------------------------------------------------------
    # Processing — producer-consumer pattern for parallel loading + GPU inference
    # ------------------------------------------------------------------------------------------------------------------

    def _process_with_producer_consumer(
        self,
        uncached_photos: list[tuple[str, str]],
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> int:
        """Process photos using producer-consumer pattern with memory control.

        Producer: worker threads load images from disk in chunks.
        Consumer: main thread runs GPU inference one image at a time.
        Queue: bounded buffer caps RAM usage.

        Args:
            uncached_photos: List of (photo_path, fingerprint) tuples to process.
            progress_callback: Optional progress callback.

        Returns:
            Number of photos actually processed.
        """
        total = len(uncached_photos)
        num_workers = self._config.processing.num_workers
        chunk_size = self._config.processing.producer_chunk_size
        image_queue = Queue(maxsize=self._config.processing.queue_max_size)
        SENTINEL = "DONE"
        SKIP = "SKIP"

        def producer():
            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                for chunk_start in range(0, total, chunk_size):
                    if self._cache_stop.is_set():
                        break

                    chunk = uncached_photos[chunk_start:chunk_start + chunk_size]

                    futures = [
                        (executor.submit(self._load_image_for_processing, path), path, fingerprint)
                        for path, fingerprint in chunk
                    ]

                    for future, path, fingerprint in futures:
                        if self._cache_stop.is_set():
                            future.cancel()
                            break

                        result = future.result()
                        if result is not None:
                            image_queue.put((result, path, fingerprint))
                        else:
                            image_queue.put((SKIP, path, fingerprint))

            image_queue.put(SENTINEL)

        producer_thread = Thread(target=producer, daemon=True)
        producer_thread.start()

        processed_count = 0
        last_save_count = 0
        last_reload_count = 0
        save_interval = self._config.processing.cache_save_interval
        reload_interval = self._config.processing.gpu_reload_interval

        while True:
            item = image_queue.get()

            if item is SENTINEL:
                break

            if self._cache_stop.is_set():
                self._drain_queue(image_queue, SENTINEL)
                break

            image, photo_path, fingerprint = item

            if image is SKIP:
                processed_count += 1
                if progress_callback:
                    progress_callback(processed_count, total, photo_path)
                continue

            result = self._pipeline.process_image(image, photo_path)

            # Store image dimensions for min_face_percent filtering during matching
            image_height, image_width = image.shape[:2]

            # Free the full-resolution image from RAM immediately after processing
            del image

            faces_data = [
                {"bbox": face.bbox, "embedding": face.embedding}
                for face in result.faces
            ]

            # Store in cache keyed by content fingerprint with filename for traceability
            self._cache.put(
                fingerprint=fingerprint,
                filename=Path(photo_path).name,
                faces=faces_data,
                image_shape=(image_height, image_width),
            )

            # Free the ProcessedImage (contains aligned crops, embeddings) after caching
            del result

            processed_count += 1

            if progress_callback:
                progress_callback(processed_count, total, photo_path)

            # Periodic checkpoint: save cache and force garbage collection
            if processed_count - last_save_count >= save_interval:
                self._cache.save()
                last_save_count = processed_count
                gc.collect()
                logger.info(f"Cache checkpoint saved at {processed_count}/{total}")

            # Periodic GPU reload: destroy and recreate ONNX sessions to free GPU arena memory
            if processed_count - last_reload_count >= reload_interval:
                logger.info(f"Releasing GPU memory at {processed_count}/{total}...")
                self._cache.save()
                self._pipeline.release()
                gc.collect()
                self._pipeline.reload()
                last_reload_count = processed_count
                logger.info(f"GPU sessions reloaded at {processed_count}/{total}")

        producer_thread.join(timeout=5)

        if processed_count > last_save_count:
            self._cache.save()
            logger.info(f"Final cache save at {processed_count}/{total}")

        return processed_count

    # ------------------------------------------------------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------------------------------------------------------

    def _drain_queue(self, queue: Queue, sentinel: str) -> None:
        """Drain remaining items from the queue to free memory."""
        while True:
            try:
                item = queue.get_nowait()
                if item is sentinel:
                    break
            except Exception:
                break

    def _ensure_pipeline_loaded(self) -> None:
        """Reload ML models if they were released after a previous run.

        Called before any operation that needs GPU inference (add_reference, process_photos).
        If models are already loaded, this is a no-op.
        """
        if not self._pipeline.is_loaded:
            logger.info("Reloading ML models...")
            self._pipeline.reload()
            self._reference_manager.set_pipeline(self._pipeline)
            logger.info("ML models reloaded")

    def _load_image_for_processing(self, photo_path: str):
        """Load an image in a worker thread.

        Images are loaded at full resolution. RetinaFace handles its own internal resize via det_size,
        and alignment crops from the full-resolution image for maximum embedding quality.

        Args:
            photo_path: Path to the image file.

        Returns:
            BGR numpy array of the loaded image, or None if loading fails.
        """
        if self._cache_stop.is_set():
            return None

        return load_image(photo_path)

    def _build_reference_index(self, persons: list[str]) -> None:
        """Build FAISS index from all reference embeddings.

        Args:
            persons: List of enrolled person names.
        """
        self._indexer.reset()

        for person_name in persons:
            embeddings = self._reference_manager.get_embeddings(person_name)

            if embeddings:
                self._indexer.add(embeddings, person_name)

        logger.info(
            f"Built reference index with {self._indexer.size} embeddings for {len(persons)} persons"
        )

    def _copy_results(
        self,
        matches: dict[str, set],
        output_dir: str,
        status_callback: Optional[Callable[[str], None]] = None,
        copy_progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> dict:
        """Copy matched photos to person folders, skipping already-copied files.

        Args:
            matches: Dict mapping person names to sets of matched photo paths.
            output_dir: Root output directory path.
            status_callback: Optional callback for copy progress updates.
            copy_progress_callback: Optional callback(current, total, filename) for progress bar.

        Returns:
            Summary dict with new copy counts per person.
        """
        summary = {}
        total_to_copy = sum(len(paths) for paths in matches.values())
        copied_so_far = 0

        for person_name, photo_paths in matches.items():
            if self._generate_stop.is_set():
                break

            safe_name = sanitize_folder_name(person_name)
            folder = create_output_folder(output_dir, safe_name)

            existing = {f.name for f in folder.iterdir() if f.is_file()}

            new_count = 0
            skipped_count = 0

            if status_callback and photo_paths:
                status_callback(f"Copying: {person_name} — {len(photo_paths):,} matches")

            for path in photo_paths:
                if self._generate_stop.is_set():
                    break

                filename = Path(path).name

                if filename in existing:
                    skipped_count += 1
                else:
                    copy_photo(path, folder)
                    new_count += 1

                copied_so_far += 1
                if copy_progress_callback:
                    copy_progress_callback(copied_so_far, total_to_copy, path)

            summary[person_name] = new_count

            if skipped_count > 0:
                logger.info(f"'{person_name}': {new_count} new, {skipped_count} already existed")
            else:
                logger.info(f"'{person_name}': {new_count} photos copied")

        return summary

    def _post_run_cleanup(self) -> None:
        """Free GPU memory after a completed run.

        Releases ONNX sessions (frees model weights + arena buffers from GPU).
        Keeps: cache dict (CPU RAM), reference embeddings (CPU RAM).
        Models are reloaded on next operation (~2-3 seconds).
        """
        self._pipeline.release()
        self._indexer.reset()
        gc.collect()
        logger.info("Post-run cleanup complete — GPU memory released, FAISS index cleared")