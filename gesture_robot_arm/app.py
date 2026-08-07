"""Camera, MediaPipe, and serial runtime orchestration."""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from contextlib import ExitStack
from pathlib import Path
from typing import Any

from .control import ControlConfig, ServoAngles, landmarks_to_servo_angles

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Control a four-servo robot arm with hand gestures."
    )
    parser.add_argument("--camera", default="/dev/video2", help="Camera index or path")
    parser.add_argument("--serial-port", default="/dev/ttyUSB0")
    parser.add_argument("--baud-rate", type=int, default=9600)
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run without connecting to the robot arm",
    )
    parser.add_argument("--record", type=Path, help="Optional output video path")
    parser.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING"),
        default="INFO",
    )
    return parser


def _camera_source(value: str) -> str | int:
    return int(value) if value.isdecimal() else value


def run(args: argparse.Namespace) -> int:
    # Heavy optional dependencies stay out of the pure control module and unit tests.
    import cv2
    import mediapipe as mp
    import serial

    serial_connection = None
    if not args.debug:
        try:
            serial_connection = serial.Serial(
                args.serial_port, args.baud_rate, write_timeout=1
            )
        except serial.SerialException as error:
            LOGGER.error("Could not open serial port %s: %s", args.serial_port, error)
            return 2

    capture = cv2.VideoCapture(_camera_source(args.camera))
    if not capture.isOpened():
        LOGGER.error("Could not open camera %s", args.camera)
        if serial_connection is not None:
            serial_connection.close()
        return 2

    writer: Any | None = None
    if args.record:
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
        fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
        writer = cv2.VideoWriter(
            str(args.record), cv2.VideoWriter_fourcc(*"XVID"), fps, (width, height)
        )
        if not writer.isOpened():
            LOGGER.error("Could not create video file %s", args.record)
            capture.release()
            if serial_connection is not None:
                serial_connection.close()
            return 2

    hands_api = mp.solutions.hands
    drawing = mp.solutions.drawing_utils
    drawing_styles = mp.solutions.drawing_styles
    angles = ServoAngles(130, 90, 129, 110)
    previous_angles: ServoAngles | None = None

    try:
        with ExitStack() as stack:
            hands = stack.enter_context(
                hands_api.Hands(
                    model_complexity=0,
                    max_num_hands=2,
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5,
                )
            )
            while capture.isOpened():
                success, image = capture.read()
                if not success:
                    LOGGER.warning("Camera returned an empty frame; stopping")
                    break

                image.flags.writeable = False
                results = hands.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
                image.flags.writeable = True

                detected_hands = results.multi_hand_landmarks or []
                if len(detected_hands) == 1:
                    hand = detected_hands[0]
                    angles = landmarks_to_servo_angles(hand.landmark, ControlConfig())
                    if angles != previous_angles:
                        LOGGER.info("Servo angles: %s", angles.as_tuple())
                        if serial_connection is not None:
                            serial_connection.write(angles.as_bytes())
                        previous_angles = angles
                elif len(detected_hands) > 1:
                    LOGGER.warning("Multiple hands detected; command ignored")

                for hand in detected_hands:
                    drawing.draw_landmarks(
                        image,
                        hand,
                        hands_api.HAND_CONNECTIONS,
                        drawing_styles.get_default_hand_landmarks_style(),
                        drawing_styles.get_default_hand_connections_style(),
                    )

                image = cv2.flip(image, 1)
                cv2.putText(
                    image,
                    str(angles.as_tuple()),
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 0, 255),
                    2,
                    cv2.LINE_AA,
                )
                cv2.imshow("Robot Arm Control", image)
                if writer is not None:
                    writer.write(image)
                if cv2.waitKey(5) & 0xFF == 27:
                    break
    except KeyboardInterrupt:
        LOGGER.info("Interrupted by user")
    except serial.SerialException as error:
        LOGGER.error("Serial communication failed: %s", error)
        return 2
    finally:
        capture.release()
        if writer is not None:
            writer.release()
        if serial_connection is not None:
            serial_connection.close()
        cv2.destroyAllWindows()

    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level), format="%(levelname)s: %(message)s"
    )
    return run(args)
