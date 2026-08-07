# Gesture-Controlled Robot Arm

Control a four-servo robot arm in real time with hand gestures. A Python application uses MediaPipe and OpenCV to convert hand landmarks into servo angles, while an Arduino sketch receives the commands over serial and drives the arm.

## Features

- Real-time, single-hand tracking
- Independent control of three axes and the claw
- Command-line configuration for camera, serial port, and recording
- Debug mode that works without connected hardware
- Arduino fail-safe that returns the arm to its neutral position after one second
- Pure, unit-tested gesture mapping logic
- Safe cleanup of camera, video writer, and serial resources

## Architecture

```text
Camera -> MediaPipe -> Gesture mapping -> 4-byte serial command -> Arduino -> Servos
```

Each serial command contains four unsigned bytes in this order:

```text
[x angle, y angle, z angle, claw angle]
```

The current calibration maps:

- Palm tilt to the `x` axis
- Wrist vertical position to the `y` axis
- Apparent palm size to the `z` axis
- A closed fist to the claw

## Repository layout

```text
.
├── gesture_robot_arm/
│   ├── app.py          # Camera, MediaPipe, UI, and serial orchestration
│   └── control.py      # Pure landmark-to-servo conversion
├── tests/
│   └── test_control.py
├── main.py             # Convenient source-tree entry point
├── main.ino            # Arduino firmware
└── pyproject.toml      # Python package and tool configuration
```

## Requirements

### Hardware

- Arduino-compatible board with support for the `Servo` library
- Four servomotors
- USB camera
- External servo power supply suitable for the expected load
- Shared ground between the servo power supply and Arduino

### Software

- Python 3.10 or newer
- Arduino IDE or Arduino CLI

## Installation

Create an isolated Python environment and install the application:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

For development tools and tests, use:

```bash
python -m pip install -e '.[dev]'
```

## Hardware setup

Upload `main.ino` to the Arduino and connect the servo signal wires as follows:

| Channel | Function | Pin | Neutral angle |
|---|---|---:|---:|
| 0 | X axis | 5 | 130° |
| 1 | Y axis | 6 | 90° |
| 2 | Z axis | 7 | 129° |
| 3 | Claw | 8 | 110° |

Power the servos from an appropriate external supply. Do not rely on the Arduino regulator for multiple loaded servos.

## Usage

Run with the default Linux devices (`/dev/video2` and `/dev/ttyUSB0`):

```bash
gesture-robot-arm
```

Or run directly from the repository:

```bash
python main.py
```

Use different devices when needed:

```bash
gesture-robot-arm --camera 0 --serial-port /dev/ttyACM0
```

Run camera tracking without opening a serial connection:

```bash
gesture-robot-arm --camera 0 --debug
```

Record the annotated video:

```bash
gesture-robot-arm --record output.avi
```

Press `Esc` to exit. Run `gesture-robot-arm --help` for every option.

## Calibration

Servo limits and landmark ranges are defined in `ControlConfig` in `gesture_robot_arm/control.py`. Tune them for the arm geometry, camera field of view, and operator distance before applying a mechanical load.

The `z` axis uses apparent palm size as a depth estimate. This is intentionally simple and can vary with hand orientation and camera perspective. For higher precision, consider a depth camera, landmark-based pose estimation, or an explicit calibration stage.

## Safety behavior

The firmware:

- Accepts only complete four-byte commands
- Constrains every received angle to the servo range of 0–180 degrees
- Updates servos only when an angle changes
- Returns all servos to their neutral angles if commands stop for more than one second

Always test new calibration values without a load and verify the arm's mechanical limits before continuous operation.

## Development

Run the test suite and lint checks:

```bash
pytest
ruff check .
```

The control module intentionally has no OpenCV, MediaPipe, or serial imports, so its behavior can be tested without camera or Arduino hardware.

## Troubleshooting

### The camera does not open

List the available video devices and pass the correct index or path through `--camera`. Check that no other process is using it.

### The serial port does not open

Confirm the device path, baud rate, and user permissions. The Python application and firmware must use the same baud rate.

### The arm moves erratically

Verify the external power supply and shared ground first. Then review the calibration ranges in `ControlConfig` and confirm that the camera produces stable landmarks.

### The claw closes at the wrong time

Adjust `fist_threshold` in `ControlConfig`. Lighting, camera angle, and partial hand occlusion can affect the gesture classifier.
