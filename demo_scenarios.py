"""Demo Scenarios card window for AeroTrace testing and presentations."""

import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, 
    QFrame, QHBoxLayout
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class DemoScenariosWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AeroTrace — Interactive Demo Testing Cards")
        self.resize(650, 480)
        self.setStyleSheet("background-color: #0f172a; color: #f8fafc;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        header = QLabel("🎯 AeroTrace Demo Scenarios (Hover Cursor Over Any Box)")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #38bdf8;")
        layout.addWidget(header)

        sub = QLabel("Tip: Position mouse over an error box and press Ctrl + Shift + Space or click 'Read Screen'.")
        sub.setStyleSheet("font-size: 12px; color: #94a3b8;")
        layout.addWidget(sub)

        # Card 1: Python Error
        layout.addWidget(self._create_card(
            title="Scenario 1: Python Missing Package Error",
            text="ModuleNotFoundError: No module named 'requests'\nTraceback (most recent call last):\n  File 'app.py', line 3, in <module>",
            color="#ef4444"
        ))

        # Card 2: JavaScript Error
        layout.addWidget(self._create_card(
            title="Scenario 2: JavaScript / React TypeError",
            text="TypeError: Cannot read properties of undefined (reading 'map')\n  at UserList (components/UserList.jsx:14:21)",
            color="#f59e0b"
        ))

        # Card 3: Database & MCP Fusion Error
        layout.addWidget(self._create_card(
            title="Scenario 3: Multi-Modal MCP Fusion (Postgres Connection)",
            text="ConnectionRefusedError: [Errno 111] Couldn't connect to Postgres on port 5432\n(Click 'Sync MCP' on AeroTrace to pull container state!)",
            color="#a855f7"
        ))

        # Card 4: Normal Text
        layout.addWidget(self._create_card(
            title="Scenario 4: Normal Content (No Hallucination)",
            text="Welcome to the application dashboard. All background microservices are functioning smoothly.",
            color="#10b981"
        ))

    def _create_card(self, title: str, text: str, color: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: #1e293b;
                border-left: 4px solid {color};
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        card_layout = QVBoxLayout(frame)
        card_layout.setContentsMargins(6, 6, 6, 6)
        card_layout.setSpacing(4)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-weight: 600; font-size: 13px; color: {color};")
        card_layout.addWidget(title_lbl)

        content_lbl = QLabel(text)
        content_lbl.setStyleSheet("font-family: Consolas, monospace; font-size: 12px; color: #e2e8f0;")
        content_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        card_layout.addWidget(content_lbl)

        return frame


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = DemoScenariosWindow()
    win.show()
    sys.exit(app.exec_())
