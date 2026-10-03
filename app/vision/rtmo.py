"""MMPose RTMO-S ONNX adapter with vendor-neutral SHADE outputs.

The checkpoint/export and training-data rights have not been independently cleared.
Use is restricted to local academic evaluation; do not redistribute the artifact or use
this implementation for production/surveillance deployment until rights are resolved.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import logging
import math
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from vision.types import ActivityObservation, BoundingBox, Detection, Frame, PoseSignal, Track

LOGGER = logging.getLogger(__name__)

KEYPOINT_NAMES = (
    "nose",
    "left_eye",
    "right_eye",
    "left_ear",
    "right_ear",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
)


class RTMOConfigurationError(ValueError):
    """The selected model artifact or device configuration is invalid."""


class RTMOInferenceError(RuntimeError):
    """The selected model could not produce a valid normalized result."""


@dataclass(frozen=True)
class RTMOConfig:
    model_path: Path
    device: str = "cpu"
    confidence_threshold: float = 0.25
    input_size: int = 640
    keypoint_threshold: float = 0.2
    model_name: str = "RTMO-S body7 640x640 (MMPose ONNX export)"

    def __post_init__(self) -> None:
        path = Path(self.model_path).expanduser()
        object.__setattr__(self, "model_path", path)
        if not 0.0 <= self.confidence_threshold <= 1.0:
            raise RTMOConfigurationError("VISION_CONFIDENCE_THRESHOLD must be between 0 and 1.")
        if not 0.0 <= self.keypoint_threshold <= 1.0:
            raise RTMOConfigurationError("VISION_KEYPOINT_THRESHOLD must be between 0 and 1.")
        if self.input_size != 640:
            raise RTMOConfigurationError("RTMO-S body7 ONNX requires a 640x640 input size.")
        if not isinstance(self.device, str) or self.device.strip().lower() not in {
            "cpu",
            "gpu",
        }:
            raise RTMOConfigurationError("VISION_DEVICE must be 'cpu' or 'gpu'.")
        object.__setattr__(self, "device", self.device.strip().lower())


@dataclass(frozen=True)
class _PersonPose:
    detection: Detection
    keypoints: dict[str, tuple[float, float]]
    keypoint_confidences: dict[str, float]
    posture: str
    verticality: float
    model_name: str


class RTMOAdapter:
    """One initialized ONNX model serving detector, pose, and posture contracts."""

    provider_name = "mmpose-rtmo-s-body7-onnx"

    def __init__(self, config: RTMOConfig, *, session_factory: Any = None) -> None:
        self.config = config
        self._session_factory = session_factory
        self._session: Any | None = None
        self._artifact_sha256: str | None = None
        self._input_name: str | None = None
        self._output_names: tuple[str, str] | None = None
        self._pending_poses: dict[tuple[int, Detection], _PersonPose] = {}
        self.tracks = None
        self._previous_centers: dict[str, tuple[float, float]] = {}

    @property
    def model_name(self) -> str:
        return self.config.model_name

    @property
    def artifact_sha256(self) -> str | None:
        """SHA-256 of the configured local artifact, or ``None`` if unavailable."""
        return self._artifact_sha256

    @property
    def model_version(self) -> None:
        """The export supplies no reliable model-version metadata."""
        return None

    @property
    def initialized(self) -> bool:
        return self._session is not None

    def initialize(self) -> None:
        """Load model once; never download or substitute missing weights."""
        if self._session is not None:
            return
        path = self.config.model_path
        if not path.is_file():
            raise RTMOConfigurationError(
                f"Vision model weights unavailable: {path.name}. Set VISION_MODEL_PATH to the local ONNX artifact."
            )
        try:
            if self.config.device == "gpu":
                raise RTMOConfigurationError(
                    "VISION_DEVICE=gpu is unavailable in this CPU-only RTMO-S adapter build; select cpu."
                )
            if self._session_factory is None:
                import onnxruntime as ort

                factory = ort.InferenceSession
            else:
                factory = self._session_factory
            session = factory(str(path), providers=["CPUExecutionProvider"])
            inputs = session.get_inputs()
            outputs = session.get_outputs()
            if len(inputs) != 1 or inputs[0].name != "input":
                raise RTMOConfigurationError("RTMO-S ONNX input signature is incompatible.")
            if len(outputs) < 2 or outputs[0].name != "dets" or outputs[1].name != "keypoints":
                raise RTMOConfigurationError("RTMO-S ONNX output signature is incompatible.")
            self._session = session
            self._input_name = inputs[0].name
            self._output_names = (outputs[0].name, outputs[1].name)
            self._artifact_sha256 = self._compute_artifact_sha256(path)
        except RTMOConfigurationError:
            raise
        except ImportError as exc:
            raise RTMOConfigurationError(
                "ONNX Runtime is unavailable; install the pinned onnxruntime dependency."
            ) from exc
        except Exception as exc:
            raise RTMOConfigurationError(f"Vision model initialization failed: {exc}") from exc
        LOGGER.info(
            "vision.model_initialized provider=%s model=%s device=cpu confidence_threshold=%.3f artifact=%s artifact_sha256=%s",
            self.provider_name,
            self.model_name,
            self.config.confidence_threshold,
            path.name,
            self._artifact_sha256 or "unavailable",
        )

    def _compute_artifact_sha256(self, path: Path) -> str | None:
        """Hash the local model once at initialization without retaining its path."""
        digest = hashlib.sha256()
        try:
            with path.open("rb") as artifact:
                for chunk in iter(lambda: artifact.read(1024 * 1024), b""):
                    digest.update(chunk)
        except OSError as exc:
            LOGGER.warning(
                "vision.artifact_digest_unavailable provider=%s error_type=%s",
                self.provider_name,
                type(exc).__name__,
            )
            return None
        return digest.hexdigest()

    def detect(self, frame: Frame) -> list[Detection]:
        """Run inference once for the frame and map person boxes/keypoints."""
        if self._session is None:
            raise RTMOInferenceError("RTMO-S adapter must be initialized before inference.")
        image = self._validate_frame(frame)
        padded, matrix = self._preprocess(image)
        try:
            tensor = np.ascontiguousarray(padded.transpose(2, 0, 1)[None].astype(np.float32))
            raw_detections, raw_keypoints = self._session.run(
                list(self._output_names or ()), {str(self._input_name): tensor}
            )
        except Exception as exc:
            raise RTMOInferenceError(f"RTMO-S inference failed on frame {frame.frame_number}.") from exc

        detections, poses = self.normalize_outputs(
            raw_detections,
            raw_keypoints,
            frame_width=image.shape[1],
            frame_height=image.shape[0],
            transform=matrix,
            confidence_threshold=self.config.confidence_threshold,
            keypoint_threshold=self.config.keypoint_threshold,
            model_name=self.model_name,
        )
        self._pending_poses = {(frame.frame_number, pose.detection): pose for pose in poses}
        LOGGER.debug(
            "vision.inference_complete provider=%s frame_number=%s observations=%s",
            self.provider_name,
            frame.frame_number,
            len(detections),
        )
        return detections

    def pose_for(self, frame: Frame, track: Track) -> PoseSignal:
        """Read the normalized pose from the most recent detection pass."""
        # Track and detection values are immutable vendor-neutral SHADE contracts.
        detection_key = (frame.frame_number, track.detection)
        person = self._pending_poses.pop(detection_key, None)
        if person is None:
            raise RTMOInferenceError("RTMO-S pose result is unavailable for this frame/track.")
        center = track.detection.bounding_box.center
        previous_center = self._previous_centers.get(track.track_id)
        motion_score = 0.0
        if previous_center is not None:
            diagonal = math.hypot(frame.width, frame.height)
            displacement = math.hypot(center[0] - previous_center[0], center[1] - previous_center[1])
            motion_score = min(displacement / diagonal, 1.0) if diagonal > 0.0 else 0.0
        self._previous_centers[track.track_id] = center
        if self.tracks is not None:
            active_track_ids = {track.track_id for track in self.tracks.active_tracks}
            self._previous_centers = {
                track_id: value for track_id, value in self._previous_centers.items()
                if track_id in active_track_ids
            }
        return PoseSignal(
            posture=person.posture,
            verticality=person.verticality,
            motion_score=motion_score,
            keypoints=person.keypoints,
            keypoint_confidences=person.keypoint_confidences,
            metadata={"vision_provider": self.provider_name, "model": person.model_name},
        )

    def classify(self, track: Track, pose: PoseSignal, frame: Frame) -> ActivityObservation:
        """Emit posture observations, not a learned activity/fall prediction."""
        activity = pose.posture if pose.posture in {"standing", "sitting", "lying"} else "unknown"
        return ActivityObservation(
            track_id=track.track_id,
            activity=activity,
            confidence=track.detection.confidence,
            pose=pose,
            observed_at=frame.captured_at,
            metadata={
                "vision_provider": self.provider_name,
                "model": self.model_name,
                "model_confidence": track.detection.confidence,
                "frame_number": frame.frame_number,
                "observation_type": "pose_heuristic_not_activity_model",
            },
        )

    @staticmethod
    def _validate_frame(frame: Frame) -> np.ndarray:
        image = np.asarray(frame.payload) if frame.payload is not None else None
        if image is None or image.size == 0 or image.ndim != 3 or image.shape[2] != 3:
            raise RTMOInferenceError("RTMO-S requires a non-empty HxWx3 BGR frame.")
        if image.dtype != np.uint8:
            raise RTMOInferenceError("RTMO-S requires uint8 BGR video frames.")
        height, width = image.shape[:2]
        if width < 1 or height < 1 or (frame.width and frame.width != width) or (frame.height and frame.height != height):
            raise RTMOInferenceError("RTMO-S frame dimensions are invalid or inconsistent.")
        return image

    @staticmethod
    def _preprocess(image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Faithfully apply MMPose BottomupResize fit, pad 114, BGR, and 0/1 scale."""
        height, width = image.shape[:2]
        if height < 1 or width < 1:
            raise RTMOInferenceError("RTMO-S frame dimensions are invalid.")
        ratio = width / height
        resized_width = min(640.0, 640.0 * ratio)
        resized_height = min(640.0, 640.0 / ratio)
        scale = np.array(
            [width * 640.0 / resized_width, height * 640.0 / resized_height],
            dtype=np.float32,
        )
        center = np.array([width / 2.0, height / 2.0], dtype=np.float32)
        matrix = cv2.getAffineTransform(
            np.float32([
                center,
                center + np.array([0.0, -scale[0] / 2.0], dtype=np.float32),
                center + np.array([-scale[1] / 2.0, 0.0], dtype=np.float32),
            ]),
            np.float32([
                [320.0, 320.0],
                [320.0, 0.0],
                [0.0, 320.0],
            ]),
        )
        padded = cv2.warpAffine(
            image,
            matrix,
            (640, 640),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(114, 114, 114),
        )
        return padded, matrix

    @classmethod
    def normalize_outputs(
        cls,
        raw_detections: Any,
        raw_keypoints: Any,
        *,
        frame_width: int,
        frame_height: int,
        transform: np.ndarray | None = None,
        confidence_threshold: float = 0.25,
        keypoint_threshold: float = 0.2,
        model_name: str = "RTMO-S body7 640x640 (MMPose ONNX export)",
    ) -> tuple[list[Detection], list[_PersonPose]]:
        """Validate arrays and map one-class boxes and 17 COCO-style keypoints."""
        if not isinstance(frame_width, int) or not isinstance(frame_height, int) or frame_width < 1 or frame_height < 1:
            raise RTMOInferenceError("RTMO-S frame dimensions must be positive integers.")
        detections_array = np.asarray(raw_detections)
        keypoints_array = np.asarray(raw_keypoints)
        if detections_array.ndim == 3:
            if detections_array.shape[0] != 1:
                raise RTMOInferenceError("RTMO-S adapter currently accepts batch size one only.")
            detections_array = detections_array[0]
        if keypoints_array.ndim == 4:
            if keypoints_array.shape[0] != 1:
                raise RTMOInferenceError("RTMO-S adapter currently accepts batch size one only.")
            keypoints_array = keypoints_array[0]
        if detections_array.ndim != 2 or detections_array.shape[1] != 5:
            raise RTMOInferenceError("RTMO-S detection output must have shape (N, 5).")
        if keypoints_array.ndim != 3 or keypoints_array.shape[2] != 3:
            raise RTMOInferenceError("RTMO-S keypoint output must have shape (N, 17, 3).")
        if detections_array.shape[0] != keypoints_array.shape[0] or keypoints_array.shape[1] != 17:
            raise RTMOInferenceError("RTMO-S detections and 17-keypoint outputs are incompatible.")
        if not np.issubdtype(detections_array.dtype, np.number) or not np.issubdtype(keypoints_array.dtype, np.number):
            raise RTMOInferenceError("RTMO-S outputs must contain numeric values.")
        if not np.isfinite(detections_array).all() or not np.isfinite(keypoints_array).all():
            raise RTMOInferenceError("RTMO-S outputs contain non-finite coordinates or confidence values.")

        matrix = transform if transform is not None else np.eye(2, 3, dtype=np.float32)
        if np.asarray(matrix).shape != (2, 3) or not np.isfinite(matrix).all():
            raise RTMOInferenceError("RTMO-S inverse preprocessing transform is invalid.")
        scale_x, scale_y = float(matrix[0, 0]), float(matrix[1, 1])
        offset_x, offset_y = float(matrix[0, 2]), float(matrix[1, 2])
        if scale_x <= 0 or scale_y <= 0:
            raise RTMOInferenceError("RTMO-S inverse preprocessing scale must be positive.")

        normalized_detections: list[Detection] = []
        normalized_poses: list[_PersonPose] = []
        for box_row, keypoint_row in zip(detections_array, keypoints_array, strict=True):
            left, top, right, bottom, confidence = (float(value) for value in box_row)
            if not 0.0 <= confidence <= 1.0:
                raise RTMOInferenceError("RTMO-S person confidence must be between 0 and 1.")
            if left > right or top > bottom:
                raise RTMOInferenceError("RTMO-S bounding box coordinates are inverted.")
            if confidence < confidence_threshold:
                continue
            x1 = min(max((left - offset_x) / scale_x, 0.0), float(frame_width))
            y1 = min(max((top - offset_y) / scale_y, 0.0), float(frame_height))
            x2 = min(max((right - offset_x) / scale_x, 0.0), float(frame_width))
            y2 = min(max((bottom - offset_y) / scale_y, 0.0), float(frame_height))
            if x2 <= x1 or y2 <= y1:
                continue
            keypoints: dict[str, tuple[float, float]] = {}
            keypoint_confidences: dict[str, float] = {}
            for name, values in zip(KEYPOINT_NAMES, keypoint_row, strict=True):
                x, y, score = (float(value) for value in values)
                if not 0.0 <= score <= 1.0:
                    raise RTMOInferenceError("RTMO-S keypoint confidence must be between 0 and 1.")
                if score < keypoint_threshold:
                    continue
                x = (x - offset_x) / scale_x
                y = (y - offset_y) / scale_y
                if not 0.0 <= x <= frame_width or not 0.0 <= y <= frame_height:
                    continue
                keypoints[name] = (x, y)
                keypoint_confidences[name] = score
            verticality = cls._verticality(keypoints)
            posture = cls._posture(keypoints, (x1, y1, x2, y2))
            detection = Detection(
                label="person",
                confidence=confidence,
                bounding_box=BoundingBox(x1, y1, x2, y2),
            )
            normalized_detections.append(detection)
            normalized_poses.append(
                _PersonPose(
                    detection=detection,
                    keypoints=keypoints,
                    keypoint_confidences=keypoint_confidences,
                    posture=posture,
                    verticality=verticality,
                    model_name=model_name,
                )
            )
        return normalized_detections, normalized_poses

    @staticmethod
    def _verticality(keypoints: dict[str, tuple[float, float]]) -> float:
        pairs = (("left_shoulder", "left_hip"), ("right_shoulder", "right_hip"))
        values = []
        for shoulder, hip in pairs:
            if shoulder in keypoints and hip in keypoints:
                values.append(abs(keypoints[hip][1] - keypoints[shoulder][1]))
        if not values:
            return 0.0
        return min(1.0, max(0.0, sum(values) / len(values)))

    @staticmethod
    def _posture(
        keypoints: dict[str, tuple[float, float]], box: tuple[float, float, float, float]
    ) -> str:
        left, top, right, bottom = box
        width, height = right - left, bottom - top
        if width <= 0 or height <= 0:
            return "unknown"
        # Conservative geometric cues only; this is not a learned activity classifier.
        if "left_shoulder" in keypoints and "left_hip" in keypoints:
            shoulder_y = keypoints["left_shoulder"][1]
            hip_y = keypoints["left_hip"][1]
            vertical_fraction = abs(hip_y - shoulder_y) / height
            if width / height > 1.15 and vertical_fraction < 0.28:
                return "lying"
            if vertical_fraction > 0.28 and height > width:
                return "standing"
        return "unknown"