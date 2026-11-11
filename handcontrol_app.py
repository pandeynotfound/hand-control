import json
import os
import time
import tkinter as tk
from tkinter import messagebox, ttk

import cv2
import mediapipe as mp
import numpy as np
import pyautogui
from PIL import Image, ImageTk

# HandControl is a standalone application. It has no connection to other projects.
APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(APP_DIR, "settings.json")

DEFAULTS = {
    "smoothing": 5.0,
    "acceleration": 1.0,
    "dead_zone": 0.012,
    "left_click": True,
    "right_click": True,
    "double_click": True,
    "gesture_lock": True,
    "x_min": 0.12,
    "x_max": 0.88,
    "y_min": 0.12,
    "y_max": 0.88
}

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0


class HandControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("HANDCONTROL // Precision Suite")
        self.root.geometry("1180x820")
        self.root.minsize(980, 700)
        self.root.configure(bg="#080f18")

        self.screen_w, self.screen_h = pyautogui.size()
        self.settings = self.load_settings()

        self.cap = None
        self.hands = None
        self.running = False
        self.paused = False
        self.prev_x = self.prev_y = None
        self.prev_hand_point = None
        self.prev_scroll_y = None
        self.active_gesture = None
        self.fps = 0.0
        self.last_frame_time = time.time()
        self.frame_photo = None

        self.smoothing = tk.DoubleVar(value=self.settings["smoothing"])
        self.acceleration = tk.DoubleVar(value=self.settings["acceleration"])
        self.dead_zone = tk.DoubleVar(value=self.settings["dead_zone"])
        self.gesture_lock = tk.BooleanVar(value=self.settings["gesture_lock"])
        self.left_enabled = tk.BooleanVar(value=self.settings["left_click"])
        self.right_enabled = tk.BooleanVar(value=self.settings["right_click"])
        self.double_enabled = tk.BooleanVar(value=self.settings["double_click"])
        self.x_inset = tk.DoubleVar(value=self.settings["x_min"])
        self.y_inset = tk.DoubleVar(value=self.settings["y_min"])

        self.status = tk.StringVar(value="STANDBY")
        self.gesture_status = tk.StringVar(value="No gesture detected")
        self.fps_status = tk.StringVar(value="0 FPS")
        self.calibration_status = tk.StringVar(value="Active area: 12% – 88%")

        self.build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def load_settings(self):
        data = DEFAULTS.copy()
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            for key in DEFAULTS:
                if key in saved:
                    data[key] = saved[key]
        except (OSError, json.JSONDecodeError):
            pass
        return data

    def save_settings(self):
        self.settings.update({
            "smoothing": self.smoothing.get(),
            "acceleration": self.acceleration.get(),
            "dead_zone": self.dead_zone.get(),
            "left_click": self.left_enabled.get(),
            "right_click": self.right_enabled.get(),
            "double_click": self.double_enabled.get(),
            "gesture_lock": self.gesture_lock.get(),
            "x_min": self.x_inset.get(),
            "x_max": 1.0 - self.x_inset.get(),
            "y_min": self.y_inset.get(),
            "y_max": 1.0 - self.y_inset.get()
        })
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, indent=4)
        self.gesture_status.set("Settings saved to settings.json")

    def build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TScale", background="#101d2b", troughcolor="#244257")
        style.configure("TCheckbutton", background="#101d2b", foreground="#dceef7")
        style.map("TCheckbutton", background=[("active", "#101d2b")])

        header = tk.Frame(self.root, bg="#080f18")
        header.pack(fill="x", padx=26, pady=(20, 12))
        tk.Label(header, text="HANDCONTROL", fg="#55dfff", bg="#080f18",
                 font=("Segoe UI", 25, "bold")).pack(side="left")
        tk.Label(header, text="PRECISION SUITE  /  V4.0", fg="#7893a8",
                 bg="#080f18", font=("Consolas", 10)).pack(side="left", padx=15, pady=(10, 0))
        tk.Label(header, textvariable=self.status, fg="#b8f4ff", bg="#123044",
                 padx=14, pady=7, font=("Consolas", 10, "bold")).pack(side="right")

        body = tk.Frame(self.root, bg="#080f18")
        body.pack(fill="both", expand=True, padx=26, pady=6)

        camera_panel = tk.Frame(body, bg="#101d2b", highlightbackground="#1b3a50",
                                highlightthickness=1)
        camera_panel.pack(side="left", fill="both", expand=True, padx=(0, 14))
        tk.Label(camera_panel, text="LIVE TRACKING / CALIBRATION AREA",
                 fg="#9cb7c9", bg="#101d2b", font=("Consolas", 10, "bold")
                 ).pack(anchor="w", padx=15, pady=(13, 8))
        self.video = tk.Label(camera_panel, text="Camera is stopped",
                              fg="#7893a8", bg="#07111b", font=("Segoe UI", 14))
        self.video.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        tk.Label(camera_panel, textvariable=self.calibration_status,
                 fg="#55dfff", bg="#101d2b", font=("Consolas", 9)
                 ).pack(anchor="w", padx=15, pady=(0, 12))

        side = tk.Frame(body, bg="#101d2b", width=310,
                        highlightbackground="#1b3a50", highlightthickness=1)
        side.pack(side="right", fill="y")
        side.pack_propagate(False)

        tk.Label(side, text="CONTROL DECK", fg="#55dfff", bg="#101d2b",
                 font=("Consolas", 12, "bold")).pack(anchor="w", padx=16, pady=(15, 10))
        self.button(side, "START TRACKING", self.start, "#0e5268").pack(fill="x", padx=14, pady=4)
        self.button(side, "STOP TRACKING", self.stop, "#512b3b").pack(fill="x", padx=14, pady=4)
        self.button(side, "PAUSE / RESUME", self.toggle_pause, "#203c52").pack(fill="x", padx=14, pady=4)

        self.section(side, "CURSOR TUNING")
        self.slider(side, "Smoothing", self.smoothing, 1, 12, "{:.1f}")
        self.slider(side, "Acceleration", self.acceleration, 0.5, 2.5, "{:.1f}x")
        self.slider(side, "Dead zone", self.dead_zone, 0.0, 0.05, "{:.3f}")

        self.section(side, "CALIBRATION")
        self.slider(side, "Horizontal inset", self.x_inset, 0.05, 0.30, "{:.2f}")
        self.slider(side, "Vertical inset", self.y_inset, 0.05, 0.30, "{:.2f}")
        self.button(side, "RESET CALIBRATION", self.reset_calibration, "#203c52").pack(fill="x", padx=14, pady=(5, 3))

        self.section(side, "GESTURE OPTIONS")
        for label, variable in [
            ("Left click · thumb + index", self.left_enabled),
            ("Right click · thumb + middle", self.right_enabled),
            ("Double click · thumb + ring", self.double_enabled),
            ("Gesture lock · one action per pinch", self.gesture_lock)
        ]:
            ttk.Checkbutton(side, text=label, variable=variable).pack(anchor="w", padx=14, pady=2)

        self.button(side, "SAVE SETTINGS", self.save_settings, "#0e5268").pack(fill="x", padx=14, pady=(12, 5))
        self.section(side, "LIVE DIAGNOSTICS")
        tk.Label(side, textvariable=self.gesture_status, fg="#e2f4ff",
                 bg="#101d2b", wraplength=270, justify="left",
                 font=("Segoe UI", 10)).pack(anchor="w", padx=16, pady=(3, 5))
        tk.Label(side, textvariable=self.fps_status, fg="#55dfff",
                 bg="#101d2b", font=("Consolas", 16, "bold")).pack(anchor="w", padx=16)

        footer = tk.Frame(self.root, bg="#080f18")
        footer.pack(fill="x", padx=26, pady=(8, 17))
        tk.Label(footer, text="INDEX: MOVE   |   THUMB+INDEX: LEFT   |   THUMB+MIDDLE: RIGHT   |   THUMB+RING: DOUBLE   |   TWO FINGERS: SCROLL",
                 fg="#7893a8", bg="#080f18", font=("Consolas", 8)).pack(anchor="w")
        tk.Label(footer, text="STOP TRACKING disables camera control. PyAutoGUI emergency failsafe: move cursor to top-left corner.",
                 fg="#587488", bg="#080f18", font=("Segoe UI", 9)).pack(anchor="w", pady=(5, 0))

    def _var(self, name, default):
        if not hasattr(self, "_extra_vars"):
            self._extra_vars = {}
        if name not in self._extra_vars:
            self._extra_vars[name] = tk.DoubleVar(value=default)
        return self._extra_vars[name]

    def section(self, parent, title):
        tk.Label(parent, text=title, fg="#55dfff", bg="#101d2b",
                 font=("Consolas", 9, "bold")).pack(anchor="w", padx=15, pady=(13, 4))

    def slider(self, parent, label, variable, low, high, fmt):
        row = tk.Frame(parent, bg="#101d2b")
        row.pack(fill="x", padx=14, pady=2)
        tk.Label(row, text=label, fg="#9cb7c9", bg="#101d2b",
                 font=("Segoe UI", 9)).pack(side="left")
        value = tk.Label(row, text=fmt.format(variable.get()), fg="#55dfff",
                         bg="#101d2b", font=("Consolas", 8))
        value.pack(side="right")
        variable.trace_add("write", lambda *_: value.config(text=fmt.format(variable.get())))
        ttk.Scale(parent, from_=low, to=high, variable=variable,
                  orient="horizontal").pack(fill="x", padx=15, pady=(0, 3))

    def button(self, parent, text, command, color):
        return tk.Button(parent, text=text, command=command, bg=color, fg="#e8faff",
                         activebackground="#28617a", activeforeground="white",
                         relief="flat", bd=0, font=("Consolas", 9, "bold"),
                         pady=9, cursor="hand2")

    def reset_calibration(self):
        self.x_inset.set(0.12)
        self.y_inset.set(0.12)
        self.gesture_status.set("Calibration reset to default boundaries.")

    def start(self):
        if self.running:
            return
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                raise RuntimeError("Could not open webcam. Check Windows camera permissions and close other camera apps.")
            self.hands = mp.solutions.hands.Hands(
                max_num_hands=1,
                min_detection_confidence=0.7,
                min_tracking_confidence=0.7
            )
        except Exception as exc:
            if self.cap:
                self.cap.release()
                self.cap = None
            messagebox.showerror("HandControl", str(exc))
            return
        self.running = True
        self.paused = False
        self.prev_x = self.prev_y = None
        self.prev_hand_point = None
        self.prev_scroll_y = None
        self.active_gesture = None
        self.status.set("TRACKING")
        self.last_frame_time = time.time()
        self._tick()

    def stop(self):
        self.running = False
        self.paused = False
        if self.cap:
            self.cap.release()
            self.cap = None
        if self.hands:
            self.hands.close()
            self.hands = None
        self.video.config(image="", text="Camera is stopped")
        self.frame_photo = None
        self.status.set("STANDBY")
        self.gesture_status.set("No gesture detected")
        self.fps_status.set("0 FPS")
        self.prev_x = self.prev_y = self.prev_hand_point = None
        self.prev_scroll_y = self.active_gesture = None

    def toggle_pause(self):
        if not self.running:
            self.gesture_status.set("Start tracking before pausing.")
            return
        self.paused = not self.paused
        self.status.set("PAUSED" if self.paused else "TRACKING")
        self.gesture_status.set("Controls paused" if self.paused else "Tracking resumed")
        self.active_gesture = None
        self.prev_scroll_y = None

    @staticmethod
    def dist(a, b):
        return float(np.hypot(a.x - b.x, a.y - b.y))

    def trigger_gesture(self, name):
        if self.active_gesture == name and self.gesture_lock.get():
            return
        if name == "LEFT CLICK" and self.left_enabled.get():
            pyautogui.click()
        elif name == "RIGHT CLICK" and self.right_enabled.get():
            pyautogui.rightClick()
        elif name == "DOUBLE CLICK" and self.double_enabled.get():
            pyautogui.doubleClick(interval=0.10)
        self.active_gesture = name

    def process_hand(self, frame, hand):
        lm = hand.landmark
        h, w, _ = frame.shape
        index, middle, ring, thumb = lm[8], lm[12], lm[16], lm[4]
        index_up = lm[8].y < lm[6].y
        middle_up = lm[12].y < lm[10].y
        ring_up = lm[16].y < lm[14].y
        pinky_up = lm[20].y < lm[18].y
        scrolling = index_up and middle_up and not ring_up and not pinky_up

        pinch_candidates = [
            ("LEFT CLICK", self.dist(thumb, index), self.left_enabled.get()),
            ("RIGHT CLICK", self.dist(thumb, middle), self.right_enabled.get()),
            ("DOUBLE CLICK", self.dist(thumb, ring), self.double_enabled.get())
        ]
        pinch_candidates = [item for item in pinch_candidates if item[2]]
        pinch = min(pinch_candidates, key=lambda item: item[1]) if pinch_candidates else None
        is_pinching = pinch is not None and pinch[1] < 0.042

        if not self.paused:
            if scrolling:
                self.gesture_status.set("Two-finger scrolling")
                scroll_y = (index.y + middle.y) / 2
                if self.prev_scroll_y is not None:
                    delta = self.prev_scroll_y - scroll_y
                    if abs(delta) > 0.005:
                        pyautogui.scroll(int(np.clip(delta * 1100, -12, 12)))
                self.prev_scroll_y = scroll_y
                self.active_gesture = None

            elif is_pinching:
                self.prev_scroll_y = None
                name = pinch[0]
                self.gesture_status.set(name.title())
                self.trigger_gesture(name)

            else:
                self.active_gesture = None
                self.prev_scroll_y = None
                if index_up:
                    self.gesture_status.set("Index-finger cursor control")
                    x_inset = self.x_inset.get()
                    y_inset = self.y_inset.get()
                    x = np.interp(index.x, [x_inset, 1 - x_inset], [0, self.screen_w])
                    y = np.interp(index.y, [y_inset, 1 - y_inset], [0, self.screen_h])
                    point = (index.x, index.y)

                    if self.prev_hand_point is not None:
                        movement = np.hypot(point[0] - self.prev_hand_point[0],
                                            point[1] - self.prev_hand_point[1])
                        if movement < self.dead_zone.get():
                            x = self.prev_x if self.prev_x is not None else x
                            y = self.prev_y if self.prev_y is not None else y
                        else:
                            x = self.screen_w / 2 + (x - self.screen_w / 2) * self.acceleration.get()
                            y = self.screen_h / 2 + (y - self.screen_h / 2) * self.acceleration.get()

                    smoothing = max(1.0, self.smoothing.get())
                    if self.prev_x is None:
                        self.prev_x, self.prev_y = x, y
                    curr_x = self.prev_x + (x - self.prev_x) / smoothing
                    curr_y = self.prev_y + (y - self.prev_y) / smoothing
                    pyautogui.moveTo(int(np.clip(curr_x, 0, self.screen_w - 1)),
                                     int(np.clip(curr_y, 0, self.screen_h - 1)))
                    self.prev_x, self.prev_y = curr_x, curr_y
                    self.prev_hand_point = point
                else:
                    self.gesture_status.set("Hand detected · point index finger to move")
                    self.prev_hand_point = None
        else:
            self.gesture_status.set("Controls paused")

        # Draw calibrated region on preview.
        x0 = int(self.x_inset.get() * w)
        x1 = int((1 - self.x_inset.get()) * w)
        y0 = int(self.y_inset.get() * h)
        y1 = int((1 - self.y_inset.get()) * h)
        cv2.rectangle(frame, (x0, y0), (x1, y1), (70, 210, 245), 1)
        mp.solutions.drawing_utils.draw_landmarks(
            frame, hand, mp.solutions.hands.HAND_CONNECTIONS
        )

    def tick(self):
        if not self.running or not self.cap:
            return
        ok, frame = self.cap.read()
        if ok:
            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(rgb)
            if results.multi_hand_landmarks:
                self.process_hand(frame, results.multi_hand_landmarks[0])
            elif not self.paused:
                self.gesture_status.set("No hand detected")
                self.prev_scroll_y = self.active_gesture = None
                self.prev_hand_point = None

            now = time.time()
            elapsed = now - self.last_frame_time
            if elapsed > 0:
                current_fps = 1.0 / elapsed
                self.fps = current_fps if not self.fps else 0.85 * self.fps + 0.15 * current_fps
            self.last_frame_time = now
            self.fps_status.set(f"{self.fps:.0f} FPS")

            view = cv2.resize(frame, (720, 480), interpolation=cv2.INTER_AREA)
            view = cv2.cvtColor(view, cv2.COLOR_BGR2RGB)
            photo = ImageTk.PhotoImage(Image.fromarray(view))
            self.video.config(image=photo, text="")
            self.video.image = photo
        self.root.after(15, self.tick)

    def _tick(self):
        self.tick()

    def close(self):
        try:
            self.save_settings()
        except OSError:
            pass
        self.stop()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = HandControlApp(root)
    root.mainloop()
