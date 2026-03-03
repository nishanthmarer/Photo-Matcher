##########################################################################################################################
# Author: Nishanth Marer Prabhu
# fileName: reference_manager.py
# Description: Manages reference face embeddings for each person. Handles enrollment of reference photos through the
#              ML pipeline, stores their embeddings in memory, and provides them for matching. Supports multiple
#              references per person for the 'match against closest' strategy — more reference angles means better
#              matching for side profiles and varied poses.
# Year: 2026
###########################################################################################################################

import numpy as np

from config import LoggingConfig
from core.pipeline import FacePipeline
from utils.image_utils import load_image
from utils.logger import setup_logger

logger = setup_logger("services.reference_manager", LoggingConfig())


class ReferenceManager:
    """Manages reference face embeddings for each person.

    When a user enrolls a reference photo, this class runs it through the full ML pipeline (detect → align → embed)
    and stores the resulting 512-d embedding. Multiple references per person are supported — during matching, the
    closest reference is used, which improves accuracy across different poses and lighting conditions.

    If a reference photo contains multiple faces, the largest face (by bounding box area) is selected as the
    primary subject.

    References are stored in memory only — they are not persisted to disk. Enrolling is fast (~300ms per photo)
    since it processes one image at a time.

    Usage:
        manager = ReferenceManager(pipeline)
        manager.enroll("Alice", "alice_front.jpg")
        manager.enroll("Alice", "alice_side.jpg")
        embeddings = manager.get_embeddings("Alice")  # returns 2 vectors
    """

    def __init__(self, pipeline: FacePipeline) -> None:
        """Initialize with a face processing pipeline.

        Args:
            pipeline: FacePipeline instance for processing reference images.
        """
        self._pipeline = pipeline
        self._references: dict[str, dict] = {}

    def set_pipeline(self, pipeline: FacePipeline) -> None:
        """Update the pipeline reference after a reload.

        Called by Segregator when the pipeline is recreated after GPU memory release.

        Args:
            pipeline: New FacePipeline instance with freshly loaded models.
        """
        self._pipeline = pipeline

    def enroll(self, person_name: str, image_path: str) -> bool:
        """Enroll a single reference photo for a person.

        Runs the photo through the full ML pipeline. If multiple faces are detected, the largest face (by
        bounding box area) is selected as the primary subject — useful for reference photos that include
        bystanders.

        Args:
            person_name: Name of the person.
            image_path: Path to the reference photo.

        Returns:
            True if enrollment succeeded, False if image couldn't be loaded or no face was found.
        """
        image = load_image(image_path)

        if image is None:
            logger.error(f"Cannot load reference image: {image_path}")
            return False

        result = self._pipeline.process_image(image, image_path)

        if result.face_count == 0:
            logger.warning(f"No face detected in reference image: {image_path}")
            return False

        if result.face_count > 1:
            face = self._select_largest_face(result.faces)
            logger.info(
                f"Multiple faces in reference {image_path}, "
                f"selected largest face (confidence: {face.confidence:.2f})"
            )
        else:
            face = result.faces[0]

        if person_name not in self._references:
            self._references[person_name] = {
                "embeddings": [],
                "photo_paths": [],
            }

        self._references[person_name]["embeddings"].append(face.embedding)
        self._references[person_name]["photo_paths"].append(image_path)

        logger.info(
            f"Enrolled reference for '{person_name}' from {image_path} "
            f"(total references: {len(self._references[person_name]['embeddings'])})"
        )

        return True

    def enroll_multiple(self, person_name: str, image_paths: list[str]) -> int:
        """Enroll multiple reference photos for a person.

        Args:
            person_name: Name of the person.
            image_paths: List of reference photo paths.

        Returns:
            Number of successfully enrolled photos.
        """
        success_count = sum(1 for path in image_paths if self.enroll(person_name, path))

        logger.info(f"Enrolled {success_count}/{len(image_paths)} references for '{person_name}'")

        return success_count

    def get_embeddings(self, person_name: str) -> list[np.ndarray]:
        """Get all stored embeddings for a person.

        Args:
            person_name: Name of the person.

        Returns:
            List of 512-d embedding vectors, or empty list if person not found.
        """
        if person_name not in self._references:
            return []

        return self._references[person_name]["embeddings"]

    def get_all_persons(self) -> list[str]:
        """Get names of all enrolled persons.

        Returns:
            List of person name strings.
        """
        return list(self._references.keys())

    def remove_person(self, person_name: str) -> bool:
        """Remove a person and all their reference embeddings.

        Args:
            person_name: Name of the person to remove.

        Returns:
            True if found and removed, False if not found.
        """
        if person_name not in self._references:
            logger.warning(f"Person '{person_name}' not found for removal")
            return False

        del self._references[person_name]
        logger.info(f"Removed all references for '{person_name}'")

        return True

    @property
    def person_count(self) -> int:
        """Number of enrolled persons."""
        return len(self._references)

    def get_embedding_count(self, person_name: str) -> int:
        """Get the number of reference embeddings for a person.

        Args:
            person_name: Name of the person.

        Returns:
            Number of reference embeddings, or 0 if person not found.
        """
        if person_name not in self._references:
            return 0

        return len(self._references[person_name]["embeddings"])

    @staticmethod
    def _select_largest_face(faces: list) -> object:
        """Select the largest face by bounding box area.

        Used when a reference photo contains multiple faces — the largest is assumed to be the primary subject.

        Args:
            faces: List of ProcessedFace objects.

        Returns:
            The ProcessedFace with the largest bounding box area.
        """
        def bbox_area(face):
            bbox = face.bbox
            return (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])

        return max(faces, key=bbox_area)