"""Mouse dwell tracking and global hotkey listeners for AeroTrace."""

import time
import threading
from typing import Callable, Optional
from PyQt5.QtCore import QObject, pyqtSignal
from pynput import mouse, keyboard
import config


class TriggerSignaler(QObject):
    """Bridge for cross-thread signals into the PyQt event loop."""
    trigger_signal = pyqtSignal(int, int)


class InputController:
    def __init__(self, on_trigger_callback: Callable[[int, int], None]):
        self.on_trigger_callback = on_trigger_callback
        self.signaler = TriggerSignaler()
        self.signaler.trigger_signal.connect(self.on_trigger_callback)

        self.last_pos = (0, 0)
        self.last_move_time = time.time()
        self.last_triggered_pos = (-999, -999)
        self.last_trigger_time = 0
        self.is_enabled = True
        self.running = True

        # Mouse & Keyboard Listener Threads
        self.mouse_listener: Optional[mouse.Listener] = None
        self.keyboard_listener: Optional[keyboard.GlobalHotKeys] = None
        self.dwell_thread: Optional[threading.Thread] = None

    def start(self):
        # 1. Global Hotkey: Ctrl + Shift + Space
        try:
            self.keyboard_listener = keyboard.GlobalHotKeys({
                config.GLOBAL_HOTKEY: self._on_hotkey
            })
            self.keyboard_listener.daemon = True
            self.keyboard_listener.start()
            print(f"[Input] Global hotkey registered: {config.GLOBAL_HOTKEY}")
        except Exception as e:
            print(f"[Input] Hotkey setup error: {e}")

        # 2. Mouse tracker
        self.mouse_listener = mouse.Listener(
            on_move=self._on_mouse_move
        )
        self.mouse_listener.daemon = True
        self.mouse_listener.start()

        # 3. Dwell Detection Worker Thread (Only if explicitly enabled in config)
        if getattr(config, "ENABLE_AMBIENT_DWELL", False):
            self.dwell_thread = threading.Thread(target=self._dwell_check_loop, daemon=True)
            self.dwell_thread.start()
            print("[Input] Cursor Dwell ambient auto-capture (~800ms) active.")
        else:
            print("[Input] Auto background capture is OFF. Screen is only captured on demand (Ctrl+Shift+Space or click).")


    def _dwell_check_loop(self):
        """Monitors for cursor stillness over new areas to trigger ambient analysis."""
        while self.running:
            time.sleep(0.1)
            if not self.is_enabled:
                continue

            now = time.time()
            # If mouse has remained still for >= 800ms
            if (now - self.last_move_time) >= 0.8:
                # Enforce cooldown of 2.5s between ambient automatic triggers
                if (now - self.last_trigger_time) >= 2.5:
                    x, y = self.last_pos
                    # Ensure the mouse moved significantly (> 40px) from previous trigger position
                    dist = ((x - self.last_triggered_pos[0])**2 + (y - self.last_triggered_pos[1])**2)**0.5
                    if dist > 40:
                        self.last_trigger_time = now
                        self.last_triggered_pos = (x, y)
                        print(f"[Input] Ambient hover dwell detected at ({x}, {y})! Triggering...")
                        self.signaler.trigger_signal.emit(x, y)

    def _on_hotkey(self):
        """Explicit hotkey trigger (Ctrl + Shift + Space)."""
        if not self.is_enabled:
            return
        x, y = self.last_pos
        self.last_trigger_time = time.time()
        self.last_triggered_pos = (x, y)
        print(f"[Input] Hotkey pressed at cursor ({x}, {y})! Triggering...")
        self.signaler.trigger_signal.emit(x, y)

    def _on_mouse_move(self, x: int, y: int):
        # Ignore micro-jitters (< 4 pixels)
        dx = abs(x - self.last_pos[0])
        dy = abs(y - self.last_pos[1])
        if dx > 4 or dy > 4:
            self.last_pos = (x, y)
            self.last_move_time = time.time()

    def stop(self):
        self.running = False
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()
