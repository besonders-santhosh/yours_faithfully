"""Main entrypoint for AeroTrace Ambient Cursor Co-Pilot."""

import sys
import os
import signal
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from ui.overlay import AeroTraceOverlay
from capture.mouse import InputController


def main():
    # Allow Ctrl+C to terminate the application immediately
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Enable high-DPI scaling
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    app = QApplication(sys.argv)

    # Periodic timer to allow Python interpreter to process signals (Ctrl+C) on Windows
    sig_timer = QTimer()
    sig_timer.timeout.connect(lambda: None)
    sig_timer.start(300)

    overlay = AeroTraceOverlay()

    def handle_trigger(x: int, y: int):
        if overlay.is_active:
            overlay.show_and_analyze_at_cursor(x, y)


    controller = InputController(on_trigger_callback=handle_trigger)
    controller.start()

    print("=" * 60)
    print("🚀 AeroTrace Ambient Cursor Co-Pilot is running!")
    print("👉 Press [ Ctrl + Shift + Space ] at any time to summon overlay")
    print("👉 Click '👁️' (Full Screen) / '🎤' (Voice) / '🔌' (MCP) / '⚡' (Resolve)")
    print("👉 Drag the circle anywhere to reposition")
    print("👉 Press [ Ctrl + C ] in this terminal to stop AeroTrace")
    print("=" * 60)

    # Initial show near cursor so user sees it right away on startup
    overlay.show_at_cursor()

    try:
        sys.exit(app.exec_())
    finally:
        controller.stop()


if __name__ == "__main__":
    main()
