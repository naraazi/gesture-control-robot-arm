from dataclasses import dataclass

import pytest

from gesture_robot_arm.control import (
    ControlConfig,
    clamp,
    landmarks_to_servo_angles,
    map_range,
)


@dataclass
class Point:
    x: float = 0.5
    y: float = 0.5
    z: float = 0.0


def test_clamp_limits_values() -> None:
    assert clamp(-1, 0, 10) == 0
    assert clamp(5, 0, 10) == 5
    assert clamp(11, 0, 10) == 10


def test_map_range_supports_reversed_output() -> None:
    assert map_range(0.5, 0, 1, 180, 90) == 135


def test_landmark_count_is_validated() -> None:
    with pytest.raises(ValueError, match="21"):
        landmarks_to_servo_angles([Point()] * 20)


def test_zero_sized_palm_returns_neutral_axes() -> None:
    config = ControlConfig()
    angles = landmarks_to_servo_angles([Point()] * 21, config)
    assert angles.as_tuple() == (
        config.x_mid,
        config.y_mid,
        config.z_mid,
        config.claw_open_angle,
    )


def test_angles_are_valid_serial_bytes() -> None:
    landmarks = [Point() for _ in range(21)]
    landmarks[5] = Point(x=0.5, y=0.7)
    angles = landmarks_to_servo_angles(landmarks)
    assert len(angles.as_bytes()) == 4
    assert all(0 <= angle <= 180 for angle in angles.as_tuple())
