"""PyQt5 Circular Floating Cursor Controller and Contextual HUD for AeroTrace."""

import sys
import threading
from typing import Optional, Dict, Any
from PyQt5.QtWidgets import (
    QWidget, QPushButton, QHBoxLayout, QVBoxLayout, 
    QLabel, QFrame, QApplication, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, QPoint, QTimer, pyqtSignal
from PyQt5.QtGui import QCursor, QColor, QFont

import os
import time
from agent.models import ErrorAnalysis
from capture.screen import capture_around_cursor, capture_entire_screen, CAPTURES_DIR
from capture.ocr import extract_text_from_image
from context.mcp_context import get_active_workspace_context
from voice.audio import global_recorder
from agent.graph import run_agent_graph
import config


class CaptureTargetBox(QWidget):
    """
    A lightweight, frameless, completely click-through overlay that 
    flashes a high-tech cyan dashed reticle over the exact area (500x300)
    centered on the cursor, giving instant visual feedback.
    """
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.box_frame = QFrame(self)
        self.box_frame.setStyleSheet("""
            QFrame {
                border: 2px dashed #00f2fe;
                background-color: rgba(0, 242, 254, 0.08);
                border-radius: 8px;
            }
        """)
        label_layout = QVBoxLayout(self.box_frame)
        label_layout.setContentsMargins(8, 4, 8, 4)
        label = QLabel("🎯 AeroTrace Cursor Inspection Region", self.box_frame)
        label.setStyleSheet("color: #00f2fe; font-size: 11px; font-weight: bold; background: transparent;")
        label_layout.addWidget(label, alignment=Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(self.box_frame)

    def flash(self, x: int, y: int, width: int = 500, height: int = 300, duration_ms: int = 800):
        self.setGeometry(x - width // 2, y - height // 2, width, height)
        self.show()
        QTimer.singleShot(duration_ms, self.hide)


class AeroTraceOverlay(QWidget):
    # Signals for thread-safe UI updates
    analysis_ready = pyqtSignal(object)
    voice_recording_done = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Drag tracking state
        self._drag_active = False
        self._drag_pos = QPoint()
        self.is_enlarged = False

        # Agent In-Memory Modality States
        self.is_active = True
        self.current_screen_text = ""
        self.current_voice_text = ""
        self.current_mcp_context = {}
        self.current_analysis: Optional[ErrorAnalysis] = None

        self.analysis_ready.connect(self.display_resolution)
        self.voice_recording_done.connect(self._on_voice_recorded)

        # Visual reticle showing the exact region inspected under the cursor
        self.target_reticle = CaptureTargetBox()

        # Continuous voice recorder (toggle on click, toggle off click)
        self.voice_recorder = global_recorder

        # LangGraph Multi-Turn Conversation Memory Tracking
        self.current_thread_id = f"session_{int(time.time())}"
        self.turn_count = 0

        self._init_ui()

    def _init_ui(self):
        # Main vertical layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(8)
        self.main_layout.setAlignment(Qt.AlignHCenter)

        # -------------------------------------------------------------
        # 1. CIRCULAR CONTROL PANE (Round Wheel / Orb)
        # -------------------------------------------------------------
        self.circle_frame = QFrame(self)
        self.circle_frame.setFixedSize(130, 130)
        self.circle_frame.setCursor(Qt.SizeAllCursor)
        self.circle_frame.setStyleSheet("""
            QFrame {
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
                    stop:0 rgba(30, 30, 46, 0.98), stop:0.85 rgba(18, 18, 28, 0.98), stop:1 rgba(99, 102, 241, 0.85));
                border: 2px solid #818cf8;
                border-radius: 65px;
            }
        """)

        # Drop shadow for floating circular orb
        circle_shadow = QGraphicsDropShadowEffect(self)
        circle_shadow.setBlurRadius(24)
        circle_shadow.setColor(QColor(0, 0, 0, 200))
        circle_shadow.setOffset(0, 6)
        self.circle_frame.setGraphicsEffect(circle_shadow)

        # Center Button: ⚡ Resolve / Fuse
        self.resolve_btn = QPushButton("⚡", self.circle_frame)
        self.resolve_btn.setGeometry(44, 44, 42, 42)
        self.resolve_btn.setToolTip("Resolve: Fuse context & generate fix")
        self.resolve_btn.setCursor(Qt.PointingHandCursor)
        self.resolve_btn.setStyleSheet(self._circle_btn_style("#f59e0b", "#d97706", 21, 18))
        self.resolve_btn.clicked.connect(self.action_resolve)

        # Top Button: 👁️ Screen OCR
        self.screen_btn = QPushButton("👁️", self.circle_frame)
        self.screen_btn.setGeometry(49, 6, 32, 32)
        self.screen_btn.setToolTip("Read Screen: Crop 400x250 region under cursor")
        self.screen_btn.setCursor(Qt.PointingHandCursor)
        self.screen_btn.setStyleSheet(self._circle_btn_style("#3b82f6", "#2563eb", 16, 14))
        self.screen_btn.clicked.connect(self.action_read_screen)

        # Bottom Button: 🔌 MCP Sync
        self.mcp_btn = QPushButton("🔌", self.circle_frame)
        self.mcp_btn.setGeometry(49, 92, 32, 32)
        self.mcp_btn.setToolTip("MCP Sync: Ingest active workspace & container state")
        self.mcp_btn.setCursor(Qt.PointingHandCursor)
        self.mcp_btn.setStyleSheet(self._circle_btn_style("#06b6d4", "#0891b2", 16, 13))
        self.mcp_btn.clicked.connect(self.action_sync_mcp)

        # Left Button: 🟢 Active / Paused Toggle
        self.toggle_btn = QPushButton("🟢", self.circle_frame)
        self.toggle_btn.setGeometry(6, 49, 32, 32)
        self.toggle_btn.setToolTip("Toggle Active / Paused status")
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.setStyleSheet(self._circle_btn_style("#10b981", "#059669", 16, 13))
        self.toggle_btn.clicked.connect(self.toggle_active)

        # Right Button: 🎤 Voice Intent
        self.voice_btn = QPushButton("🎤", self.circle_frame)
        self.voice_btn.setGeometry(92, 49, 32, 32)
        self.voice_btn.setToolTip("Voice: Click to record question")
        self.voice_btn.setCursor(Qt.PointingHandCursor)
        self.voice_btn.setStyleSheet(self._circle_btn_style("#8b5cf6", "#7c3aed", 16, 13))
        self.voice_btn.clicked.connect(self.action_record_voice)

        # Small Close Button on Upper Right
        self.close_btn = QPushButton("✕", self.circle_frame)
        self.close_btn.setGeometry(96, 12, 20, 20)
        self.close_btn.setToolTip("Click: Hide | Double-click: Quit AeroTrace")
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.15);
                color: #e2e8f0;
                border-radius: 10px;
                font-size: 10px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background-color: #ef4444;
                color: white;
            }
        """)
        self.close_btn.clicked.connect(self.hide)
        self.close_btn.mouseDoubleClickEvent = lambda e: QApplication.quit()


        self.main_layout.addWidget(self.circle_frame, alignment=Qt.AlignHCenter)

        # -------------------------------------------------------------
        # 2. LIVE STATUS / SPEECH FEEDBACK BUBBLE
        # -------------------------------------------------------------
        self.status_bubble = QFrame(self)
        self.status_bubble.setFixedWidth(480)
        self.status_bubble.setStyleSheet("""
            QFrame {
                background-color: rgba(24, 24, 37, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.16);
                border-radius: 10px;
                padding: 4px;
            }
        """)
        bubble_shadow = QGraphicsDropShadowEffect(self)
        bubble_shadow.setBlurRadius(16)
        bubble_shadow.setColor(QColor(0, 0, 0, 160))
        bubble_shadow.setOffset(0, 3)
        self.status_bubble.setGraphicsEffect(bubble_shadow)

        bubble_layout = QHBoxLayout(self.status_bubble)
        bubble_layout.setContentsMargins(10, 6, 10, 6)

        self.status_label = QLabel("👉 Click 🎤 to speak, 👁️ to read screen, or ⚡ to resolve", self.status_bubble)
        self.status_label.setStyleSheet("color: #cbd5e1; font-size: 11px; font-weight: 500;")
        self.status_label.setWordWrap(True)
        bubble_layout.addWidget(self.status_label, 1)

        self.main_layout.addWidget(self.status_bubble)

        # -------------------------------------------------------------
        # 3. EXPANDABLE RESULT CARD (Shows when resolved)
        # -------------------------------------------------------------
        self.result_card = QFrame(self)
        self.result_card.setFixedWidth(480)
        self.result_card.setStyleSheet("""
            QFrame {
                background-color: rgba(24, 24, 37, 0.96);
                border: 1px solid rgba(255, 255, 255, 0.16);
                border-radius: 12px;
            }
        """)
        result_shadow = QGraphicsDropShadowEffect(self)
        result_shadow.setBlurRadius(20)
        result_shadow.setColor(QColor(0, 0, 0, 180))
        result_shadow.setOffset(0, 4)
        self.result_card.setGraphicsEffect(result_shadow)

        self.card_layout = QVBoxLayout(self.result_card)
        self.card_layout.setContentsMargins(14, 12, 14, 12)
        self.card_layout.setSpacing(8)

        # Header row with title, memory turn badge, new chat, zoom button & hide button
        header_row = QHBoxLayout()
        header_row.setSpacing(6)

        header_lbl = QLabel("⚡ AeroTrace")
        header_lbl.setStyleSheet("color: #38bdf8; font-size: 13px; font-weight: bold;")
        header_row.addWidget(header_lbl)

        # Multi-turn memory badge
        self.memory_badge = QLabel("💬 Turn 1")
        self.memory_badge.setStyleSheet("""
            color: #38bdf8; 
            background-color: rgba(56, 189, 248, 0.15); 
            border: 1px solid rgba(56, 189, 248, 0.3);
            border-radius: 4px; 
            padding: 1px 6px; 
            font-size: 10px; 
            font-weight: 600;
        """)
        header_row.addWidget(self.memory_badge)
        header_row.addStretch(1)

        # New chat / reset memory button
        self.new_chat_btn = QPushButton("🔄 New Chat")
        self.new_chat_btn.setFixedHeight(22)
        self.new_chat_btn.setToolTip("Start a new topic and reset conversation memory")
        self.new_chat_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                color: #cbd5e1;
                border-radius: 4px;
                padding: 2px 7px;
                font-size: 10px;
                font-weight: 600;
                border: 1px solid rgba(255, 255, 255, 0.12);
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.2);
                color: #f87171;
                border: 1px solid #ef4444;
            }
        """)
        self.new_chat_btn.clicked.connect(self.reset_chat_session)
        header_row.addWidget(self.new_chat_btn)

        self.zoom_btn = QPushButton("🔍+ Enlarge")
        self.zoom_btn.setFixedHeight(22)
        self.zoom_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                color: #38bdf8;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 600;
                border: none;
            }
            QPushButton:hover { background-color: rgba(56, 189, 248, 0.2); }
        """)
        self.zoom_btn.clicked.connect(self.toggle_card_size)
        header_row.addWidget(self.zoom_btn)

        hide_card_btn = QPushButton("✕")
        hide_card_btn.setFixedSize(20, 20)
        hide_card_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #94a3b8;
                border: none;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { color: white; }
        """)
        hide_card_btn.clicked.connect(self.hide_result_card)
        header_row.addWidget(hide_card_btn)
        self.card_layout.addLayout(header_row)

        # Voice Query Banner (if voice was used)
        self.voice_query_label = QLabel("")
        self.voice_query_label.setStyleSheet("""
            background-color: rgba(139, 92, 246, 0.2);
            color: #c4b5fd;
            border: 1px solid rgba(139, 92, 246, 0.4);
            border-radius: 6px;
            padding: 4px 8px;
            font-size: 11px;
            font-weight: 600;
        """)
        self.voice_query_label.setWordWrap(True)
        self.card_layout.addWidget(self.voice_query_label)
        self.voice_query_label.hide()

        # Tags label
        self.tags_label = QLabel("")
        self.tags_label.setStyleSheet("color: #94a3b8; font-size: 10px;")
        self.tags_label.setWordWrap(True)
        self.card_layout.addWidget(self.tags_label)

        # Summary label
        self.summary_label = QLabel("Analyzing hovered context...")
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet("color: #f1f5f9; font-size: 13px; font-weight: 500;")
        self.card_layout.addWidget(self.summary_label)

        # Fix Box
        self.fix_box = QFrame()
        self.fix_box.setStyleSheet("""
            QFrame {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 6px;
            }
        """)
        self.fix_box_layout = QHBoxLayout(self.fix_box)
        self.fix_box_layout.setContentsMargins(8, 6, 8, 6)

        self.fix_label = QLabel("...")
        self.fix_label.setStyleSheet("color: #38bdf8; font-family: Consolas, monospace; font-size: 12px;")
        self.fix_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.fix_label.setWordWrap(True)
        self.fix_box_layout.addWidget(self.fix_label, 1)

        self.copy_btn = QPushButton("📋 Copy")
        self.copy_btn.setFixedHeight(24)
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: white;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 600;
                border: none;
            }
            QPushButton:hover { background-color: #475569; }
        """)
        self.copy_btn.clicked.connect(self.copy_fix_to_clipboard)
        self.fix_box_layout.addWidget(self.copy_btn)

        self.card_layout.addWidget(self.fix_box)

        # -------------------------------------------------------------
        # QUICK MCP DISPATCH ROW: [🐱 GitHub Issue] [💬 Share to Slack]
        # -------------------------------------------------------------
        mcp_row = QHBoxLayout()
        mcp_row.setSpacing(8)

        self.github_btn = QPushButton("🐱 GitHub Issue")
        self.github_btn.setFixedHeight(24)
        self.github_btn.setToolTip("File or draft a GitHub Issue with this traceback via GitHub MCP")
        self.github_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                color: #e2e8f0;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 600;
                border: 1px solid rgba(255, 255, 255, 0.15);
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.18);
                color: white;
            }
        """)
        self.github_btn.clicked.connect(self.action_github_mcp)
        mcp_row.addWidget(self.github_btn)

        self.slack_btn = QPushButton("💬 Share to Slack")
        self.slack_btn.setFixedHeight(24)
        self.slack_btn.setToolTip("Share diagnosis & fix to your team Slack channel via Slack MCP")
        self.slack_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(74, 21, 75, 0.4);
                color: #e9d5ff;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 600;
                border: 1px solid rgba(168, 85, 247, 0.3);
            }
            QPushButton:hover {
                background-color: rgba(74, 21, 75, 0.8);
                color: white;
            }
        """)
        self.slack_btn.clicked.connect(self.action_slack_mcp)
        mcp_row.addWidget(self.slack_btn)

        self.card_layout.addLayout(mcp_row)
        self.main_layout.addWidget(self.result_card)

        # Start with result card collapsed
        self.result_card.hide()
        self.adjustSize()

    def _circle_btn_style(self, bg_color: str, hover_color: str, radius: int, font_size: int) -> str:
        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: white;
                border-radius: {radius}px;
                font-size: {font_size}px;
                font-weight: bold;
                border: 1px solid rgba(255, 255, 255, 0.25);
            }}
            QPushButton:hover {{
                background-color: {hover_color};
                border: 1px solid white;
            }}
        """

    # -------------------------------------------------------------
    # DRAG & MOVE SUPPORT: Move anywhere on screen
    # -------------------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_active = True
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_active and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_active = False
        event.accept()

    def hide_result_card(self):
        self.result_card.hide()
        self.adjustSize()

    def toggle_card_size(self):
        self.is_enlarged = not self.is_enlarged
        if self.is_enlarged:
            self.result_card.setFixedWidth(640)
            self.status_bubble.setFixedWidth(640)
            self.summary_label.setStyleSheet("color: #f1f5f9; font-size: 15px; font-weight: 500;")
            self.fix_label.setStyleSheet("color: #38bdf8; font-family: Consolas, monospace; font-size: 13px;")
            self.zoom_btn.setText("🔍- Compact")
        else:
            self.result_card.setFixedWidth(480)
            self.status_bubble.setFixedWidth(480)
            self.summary_label.setStyleSheet("color: #f1f5f9; font-size: 13px; font-weight: 500;")
            self.fix_label.setStyleSheet("color: #38bdf8; font-family: Consolas, monospace; font-size: 12px;")
            self.zoom_btn.setText("🔍+ Enlarge")
        self.adjustSize()


    def toggle_active(self):
        self.is_active = not self.is_active
        if self.is_active:
            self.toggle_btn.setText("🟢")
            self.toggle_btn.setStyleSheet(self._circle_btn_style("#10b981", "#059669", 16, 13))
            self.status_label.setText("🟢 AeroTrace active. Hover & press Ctrl+Shift+Space.")
            self.status_label.setStyleSheet("color: #10b981; font-size: 11px;")
        else:
            self.toggle_btn.setText("⏸️")
            self.toggle_btn.setStyleSheet(self._circle_btn_style("#64748b", "#475569", 16, 13))
            self.status_label.setText("⏸️ Monitoring paused.")
            self.status_label.setStyleSheet("color: #94a3b8; font-size: 11px;")

    def show_at_cursor(self, x: Optional[int] = None, y: Optional[int] = None):
        """Positions the round control pane beside the cursor, clamped to screen."""
        if x is None or y is None:
            pos = QCursor.pos()
            x, y = pos.x(), pos.y()

        screen = QApplication.primaryScreen().geometry()
        # Offset to the right and slightly below cursor, safely within screen bounds
        target_x = max(10, min(x + config.OVERLAY_OFFSET_X + 15, screen.width() - 530))
        target_y = max(10, min(y + config.OVERLAY_OFFSET_Y + 15, screen.height() - 520))

        self.move(target_x, target_y)
        self.show()
        self.raise_()

    def show_and_analyze_at_cursor(self, x: int, y: int):
        """
        Called when user presses Ctrl+Shift+Space or hovers.
        1. Queries live OS cursor position.
        2. Hides overlay first so screenshot NEVER captures the overlay itself.
        3. Captures the clean 500x300 area directly under the cursor.
        4. Shows overlay beside the cursor and analyzes.
        """
        cur_pos = QCursor.pos()
        target_x = cur_pos.x() if cur_pos.x() > 0 else x
        target_y = cur_pos.y() if cur_pos.y() > 0 else y

        # 1. Hide overlay to guarantee pristine capture without overlay occlusion
        was_visible = self.isVisible()
        if was_visible:
            self.hide()
            QApplication.processEvents()

        # 2. Capture clean screen directly under cursor
        img, saved_path = capture_around_cursor(target_x, target_y, width=500, height=300, save_to_disk=True)

        # 3. Flash visual reticle to show the user the exact 500x300 focus area
        self.target_reticle.flash(target_x, target_y, width=500, height=300, duration_ms=800)

        # 4. Show overlay beside cursor
        self.show_at_cursor(target_x, target_y)

        # 5. Extract text & run LangGraph
        self._process_cursor_capture(img, saved_path)

    def _process_cursor_capture(self, img, saved_path: str):
        filename = os.path.basename(saved_path) if saved_path else "capture.png"

        text = extract_text_from_image(img)
        self.current_screen_text = text
        self.screen_btn.setText("✅" if text else "👁️")
        QTimer.singleShot(1200, lambda: self.screen_btn.setText("👁️"))

        clean = text.replace('\n', ' ').strip()
        print(f"[Screen] Under-cursor OCR ({len(clean)} chars): '{clean}'")

        if text:
            display_snippet = clean[:42]
            # Check if user enabled auto-resolve in config (Default: OFF, user must click ⚡)
            if getattr(config, "AUTO_RESOLVE_ON_CAPTURE", False):
                self.status_label.setText(f'👁️ Read under cursor: "{display_snippet}..."')
                self.status_label.setStyleSheet("color: #60a5fa; font-size: 11px; font-weight: 500;")
                self.action_resolve()
            else:
                self.status_label.setText(f'👁️ Screen context ready: "{display_snippet}..." 👉 Click ⚡ to solve!')
                self.status_label.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: bold;")
        else:
            self.status_label.setText(f"👁️ Saved to captures/{filename} (No text under cursor).")
            self.status_label.setStyleSheet("color: #94a3b8; font-size: 11px;")

        self._update_tags()
        self.adjustSize()

    def action_read_screen(self):
        """Triggered from 👁️ button on circle."""
        cur_pos = QCursor.pos()
        self.show_and_analyze_at_cursor(cur_pos.x(), cur_pos.y())

    def action_record_voice(self):
        """
        Toggle voice recording with manual on/off:
        - 1st Click: Start recording continuous audio (no timeout). Button turns ⏹️.
        - 2nd Click: Stop recording and transcribe with Google Speech API.
        """
        if not self.voice_recorder.is_recording:
            # START RECORDING
            started = self.voice_recorder.start_recording()
            if started:
                self.voice_btn.setText("⏹️")
                self.voice_btn.setToolTip("Click to STOP recording")
                self.voice_btn.setStyleSheet(self._circle_btn_style("#ef4444", "#dc2626", 16, 13))
                self.status_label.setText("🔴 Recording voice... Click ⏹️ when you finish speaking!")
                self.status_label.setStyleSheet("color: #f43f5e; font-size: 11px; font-weight: bold;")
                self.adjustSize()
        else:
            # STOP RECORDING & TRANSCRIBE
            self.voice_btn.setText("⏳")
            self.voice_btn.setToolTip("Transcribing audio...")
            self.voice_btn.setStyleSheet(self._circle_btn_style("#8b5cf6", "#7c3aed", 16, 13))
            self.status_label.setText("⏳ Transcribing speech to text...")
            self.status_label.setStyleSheet("color: #a78bfa; font-size: 11px; font-weight: bold;")
            self.adjustSize()

            def worker():
                text = self.voice_recorder.stop_and_transcribe()
                self.voice_recording_done.emit(text)

            threading.Thread(target=worker, daemon=True).start()

    def _on_voice_recorded(self, text: Optional[str]):
        """Callback invoked when voice recording & transcription completes."""
        self.current_voice_text = text or ""
        self.voice_btn.setText("🎤")
        self.voice_btn.setToolTip("Voice: Click to record (click again to stop)")
        self.voice_btn.setStyleSheet(self._circle_btn_style("#8b5cf6", "#7c3aed", 16, 13))

        if text:
            self.status_label.setText(f'🎤 Recorded: "{text}". Click ⚡ to solve!')
            self.status_label.setStyleSheet("color: #a78bfa; font-size: 11px; font-weight: bold;")
            self.voice_query_label.setText(f'🎤 Voice Query: "{text}"')
            self.voice_query_label.show()
        else:
            self.status_label.setText("⚠️ No speech recognized. Click 🎤 and speak clearly.")
            self.status_label.setStyleSheet("color: #fbbf24; font-size: 11px;")
            self.voice_query_label.hide()

        self._update_tags()
        self.adjustSize()

    def action_sync_mcp(self):
        """Syncs workspace / developer environment context."""
        ctx = get_active_workspace_context()
        self.current_mcp_context = ctx
        branch = ctx.get("git_branch", "main")
        self.mcp_btn.setText("✅")
        QTimer.singleShot(1200, lambda: self.mcp_btn.setText("🔌"))
        
        self.status_label.setText(f"🔌 MCP synced: Git '{branch}' | Postgres (stopped)")
        self.status_label.setStyleSheet("color: #22d3ee; font-size: 11px; font-weight: 500;")
        self._update_tags()
        self.adjustSize()

    def action_resolve(self):
        """
        Fuses ALL 3 context inputs (Screen OCR + Voice Intent + MCP Context)
        and calls the LangGraph agent in a non-blocking background thread.
        Triggered ONLY when user clicks the middle ⚡ button (or hotkey if enabled).
        """
        if not self.current_mcp_context:
            self.action_sync_mcp()

        self.status_label.setText("⚡ Fusing Screen + Voice + MCP ➔ Sending to Groq...")
        self.status_label.setStyleSheet("color: #f59e0b; font-size: 11px; font-weight: bold;")
        self.summary_label.setText("⚡ Running LangGraph StateGraph pipeline...")
        self.fix_label.setText("Analyzing hovered screen text, voice question, and local MCP environment...")
        self.result_card.show()
        self.adjustSize()

        def worker():
            analysis = run_agent_graph(
                screen_text=self.current_screen_text,
                voice_text=self.current_voice_text,
                mcp_context=self.current_mcp_context,
                thread_id=self.current_thread_id
            )
            self.analysis_ready.emit(analysis)

        threading.Thread(target=worker, daemon=True).start()

    def reset_chat_session(self):
        """Starts a new chat session and resets LangGraph memory checkpoint."""
        self.current_thread_id = f"session_{int(time.time())}"
        self.turn_count = 0
        self.current_screen_text = ""
        self.current_voice_text = ""
        self.memory_badge.setText("💬 New Chat")
        self.memory_badge.setStyleSheet("""
            color: #10b981; 
            background-color: rgba(16, 185, 129, 0.15); 
            border: 1px solid rgba(16, 185, 129, 0.3);
            border-radius: 4px; 
            padding: 1px 6px; 
            font-size: 10px; 
            font-weight: 600;
        """)
        self.status_label.setText("✨ Started new chat session. LangGraph memory reset.")
        self.status_label.setStyleSheet("color: #10b981; font-size: 11px; font-weight: bold;")
        self._update_tags()
        self.hide_result_card()

    def _update_tags(self):
        tags = []
        if self.current_screen_text:
            tags.append(f"👁️ '{self.current_screen_text.replace(chr(10), ' ')[:18]}...'")
        if self.current_voice_text:
            tags.append(f"🎤 '{self.current_voice_text}'")
        if self.current_mcp_context:
            tags.append(f"🔌 {self.current_mcp_context.get('git_branch', 'synced')}")
        self.tags_label.setText(" | ".join(tags))

    def display_resolution(self, analysis: ErrorAnalysis):
        self.current_analysis = analysis
        self.turn_count = analysis.turn_count

        if self.turn_count > 1:
            self.memory_badge.setText(f"💬 Turn {self.turn_count} (Memory Active)")
            self.memory_badge.setStyleSheet("""
                color: #c084fc; 
                background-color: rgba(192, 132, 252, 0.18); 
                border: 1px solid rgba(192, 132, 252, 0.4);
                border-radius: 4px; 
                padding: 1px 6px; 
                font-size: 10px; 
                font-weight: bold;
            """)
        else:
            self.memory_badge.setText(f"💬 Turn {self.turn_count}")
            self.memory_badge.setStyleSheet("""
                color: #38bdf8; 
                background-color: rgba(56, 189, 248, 0.15); 
                border: 1px solid rgba(56, 189, 248, 0.3);
                border-radius: 4px; 
                padding: 1px 6px; 
                font-size: 10px; 
                font-weight: 600;
            """)

        self._update_tags()
        self.summary_label.setText(analysis.issue_summary)
        self.fix_label.setText(analysis.suggested_fix)

        if self.current_voice_text:
            self.voice_query_label.setText(f'🎤 Voice Query: "{self.current_voice_text}"')
            self.voice_query_label.show()
        else:
            self.voice_query_label.hide()

        self.status_label.setText(f"✅ Solution ready (Turn {self.turn_count}) | Click 📋 Copy or 🎤 for follow-up")
        self.status_label.setStyleSheet("color: #34d399; font-size: 11px; font-weight: 500;")
        self.result_card.show()
        self.adjustSize()

    def copy_fix_to_clipboard(self):
        if self.current_analysis:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.current_analysis.suggested_fix)
            self.copy_btn.setText("✅ Copied!")
            QTimer.singleShot(1500, lambda: self.copy_btn.setText("📋 Copy"))

    def action_github_mcp(self):
        """Dispatches incident traceback to GitHub MCP to open or draft an issue."""
        if not self.current_analysis:
            return
        from context.mcp_context import GitHubMCPClient
        import webbrowser
        client = GitHubMCPClient()
        res = client.create_or_open_issue(
            title=self.current_analysis.issue_summary,
            traceback_text=self.current_screen_text,
            fix=self.current_analysis.suggested_fix
        )
        url = res.get("url", "")
        if url:
            try:
                webbrowser.open(url)
            except Exception:
                pass
        self.github_btn.setText("✅ Drafted!")
        self.status_label.setText("🐱 GitHub MCP: Incident issue drafted & opened!")
        self.status_label.setStyleSheet("color: #60a5fa; font-size: 11px; font-weight: bold;")
        QTimer.singleShot(2000, lambda: self.github_btn.setText("🐱 GitHub Issue"))

    def action_slack_mcp(self):
        """Dispatches incident resolution to team Slack via Slack MCP."""
        if not self.current_analysis:
            return
        from context.mcp_context import SlackMCPClient
        client = SlackMCPClient()
        res = client.post_resolution(
            summary=self.current_analysis.issue_summary,
            fix=self.current_analysis.suggested_fix,
            voice_query=self.current_voice_text
        )
        mode = res.get("mode", "simulated")
        self.slack_btn.setText("✅ Shared!")
        self.status_label.setText(f"💬 Slack MCP: Resolution dispatched to team ({mode})!")
        self.status_label.setStyleSheet("color: #c084fc; font-size: 11px; font-weight: bold;")
        QTimer.singleShot(2000, lambda: self.slack_btn.setText("💬 Share to Slack"))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            if self.result_card.isVisible():
                self.result_card.hide()
                self.adjustSize()
            else:
                self.hide()
        super().keyPressEvent(event)

    def contextMenuEvent(self, event):
        from PyQt5.QtWidgets import QMenu
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item:selected {
                background-color: #ef4444;
                color: white;
            }
        """)
        quit_action = menu.addAction("🚪 Quit AeroTrace")
        quit_action.triggered.connect(QApplication.quit)
        menu.exec_(event.globalPos())

