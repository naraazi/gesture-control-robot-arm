"""Pure hand-landmark to servo-angle conversion logic."""

from __future__ import annotations

from dataclasses import dataclass
from math import asin, degrees, dist
from typing import Protocol, Sequence


class Point3D(Protocol):
    x: float
    y: float
    z: float


@dataclass(frozen=True, slots=True)
class ServoAngles:
    x: int
    y: int
    z: int
    claw: int

    def as_bytes(self) -> bytes:
        return bytes((self.x, self.y, self.z, self.claw))

    def as_tuple(self) -> tuple[int, int, int, int]:
        return self.x, self.y, self.z, self.claw


@dataclass(frozen=True, slots=True)
class ControlConfig:
    x_min: int = 90
    x_mid: int = 130
    x_max: int = 180
    palm_angle_min: float = -50.0
    palm_angle_max: float = 20.0

    y_min: int = 50
    y_mid: int = 90
    y_max: int = 145
    wrist_y_min: float = 0.3
    wrist_y_max: float = 0.9

    z_min: int = 103
    z_mid: int = 129
    z_max: int = 180
    palm_size_min: float = 0.1
    palm_size_max: float = 0.3

    claw_open_angle: int = 110
    claw_closed_angle: int = 146
    fist_threshold: float = 7.0


FINGER_JOINT_INDICES = (7, 8, 11, 12, 15, 16, 19, 20)
WRIST_INDEX = 0
INDEX_FINGER_MCP_INDEX = 5
EPSILON = 1e-9


def clamp(value: float, minimum: float, maximum: float) -> float:
    if minimum > maximum:
        raise ValueError("minimum must not be greater than maximum")
    return max(minimum, min(maximum, value))


def map_range(
    value: float,
    input_min: float,
    input_max: float,
    output_min: float,
    output_max: float,
) -> float:
    if input_min == input_max:
        raise ValueError("input range must have a non-zero width")
    ratio = (value - input_min) / (input_max - input_min)
    return output_min + ratio * (output_max - output_min)


def _coordinates(point: Point3D) -> tuple[float, float, float]:
    return point.x, point.y, point.z


def is_fist(
    landmarks: Sequence[Point3D], palm_size: float, threshold: float
) -> bool:
    if palm_size <= EPSILON:
        return False

    wrist = landmarks[WRIST_INDEX]
    distance_sum = sum(
        dist(_coordinates(wrist), _coordinates(landmarks[index]))
        for index in FINGER_JOINT_INDICES
    )
    return distance_sum / palm_size < threshold


def landmarks_to_servo_angles(
    landmarks: Sequence[Point3D], config: ControlConfig | None = None
) -> ServoAngles:
    """Convert the 21 MediaPipe hand landmarks into four safe servo angles."""
    if len(landmarks) < 21:
        raise ValueError("expected at least 21 hand landmarks")
    if config is None:
        config = ControlConfig()

    wrist = landmarks[WRIST_INDEX]
    index_mcp = landmarks[INDEX_FINGER_MCP_INDEX]
    palm_size = dist(_coordinates(wrist), _coordinates(index_mcp))

    claw = (
        config.claw_closed_angle
        if is_fist(landmarks, palm_size, config.fist_threshold)
        else config.claw_open_angle
    )

    if palm_size <= EPSILON:
        return ServoAngles(config.x_mid, config.y_mid, config.z_mid, claw)

    # asin yields the signed palm tilt while preserving the original calibration axis.
    normalized_x = clamp((wrist.x - index_mcp.x) / palm_size, -1.0, 1.0)
    palm_angle = clamp(
        degrees(asin(normalized_x)),
        config.palm_angle_min,
        config.palm_angle_max,
    )
    x_angle = map_range(
        palm_angle,
        config.palm_angle_min,
        config.palm_angle_max,
        config.x_max,
        config.x_min,
    )

    wrist_y = clamp(wrist.y, config.wrist_y_min, config.wrist_y_max)
    y_angle = map_range(
        wrist_y,
        config.wrist_y_min,
        config.wrist_y_max,
        config.y_max,
        config.y_min,
    )

    bounded_palm_size = clamp(
        palm_size, config.palm_size_min, config.palm_size_max
    )
    z_angle = map_range(
        bounded_palm_size,
        config.palm_size_min,
        config.palm_size_max,
        config.z_max,
        config.z_min,
    )

    return ServoAngles(round(x_angle), round(y_angle), round(z_angle), claw)
