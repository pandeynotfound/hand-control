# HandControl v4.0

**A standalone, webcam-based hand gesture controller for Windows.**

HandControl uses computer vision to track hand landmarks and translate simple gestures into mouse actions. It includes a desktop dashboard for live tracking, cursor tuning, calibration, and gesture settings.

> HandControl is an independent project. It does not integrate with or depend on any other assistant or application.

## Features

- **Live hand tracking** with MediaPipe and OpenCV
- **Cursor movement** using the index finger
- **Left click** with a thumb + index-finger pinch
- **Right click** with a thumb + middle-finger pinch
- **Double click** with a thumb + ring-finger pinch
- **Scrolling** by raising the index and middle fingers while keeping the ring and pinky fingers down
- **Cursor tuning** with smoothing, acceleration, and dead-zone controls
- **Calibration** with adjustable horizontal and vertical tracking boundaries
- **Gesture toggles** to enable or disable individual click gestures
- **Gesture lock** to avoid repeated clicks while holding a pinch
- **Settings persistence** through a local `settings.json` file
- **Live diagnostics** with gesture status and FPS

## Tech stack

- Python 3.11
- OpenCV
- MediaPipe
- PyAutoGUI
- NumPy
- Pillow
- Tkinter (included with standard Windows Python installations)

## Requirements

- Windows 10 or Windows 11
- Python 3.11
- A working webcam
- A mouse or keyboard available as a fallback

## Installation

Clone the repository:

```powershell
git clone https://github.com/pandeynotfound/HandControl.git
cd HandControl
```

Create and activate a virtual environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, allow it only for the current terminal session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run

```powershell
python handcontrol_app.py
```

## Gesture reference

| Gesture | Action |
|---|---|
| Point with index finger | Move cursor |
| Pinch thumb + index finger | Left click |
| Pinch thumb + middle finger | Right click |
| Pinch thumb + ring finger | Double click |
| Raise index + middle fingers; lower ring + pinky | Scroll |

Gesture recognition is based on webcam landmarks and may occasionally misclassify a movement. Adjust the calibration and cursor controls to suit your camera position and working space.

## Project structure

```text
HandControl/
├── handcontrol_app.py
├── requirements.txt
├── README.md
├── LICENSE
└── .gitignore
```

## Safety notes

- Use **STOP TRACKING** to release the webcam and disable gesture input.
- PyAutoGUI's emergency failsafe is enabled: moving the cursor to the top-left corner of the primary screen triggers its failsafe.
- Keep a physical mouse or keyboard nearby, especially while testing.
- Avoid using gesture control for actions where an accidental click could cause data loss or other harm.
- Camera access is used locally for hand tracking; this project does not intentionally upload camera frames.

## Current status

**v4.0 — Stable project release**

The project is intended as a learning and portfolio project demonstrating real-time computer vision, hand landmark tracking, gesture recognition, and desktop automation.

## License

MIT. See [LICENSE](LICENSE).
