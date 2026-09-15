"""Configuration parameters for AeroTrace Ambient Cursor Co-Pilot."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# Capture & Detection Settings
DWELL_TIME_MS = 800
MOVEMENT_THRESHOLD_PX = 5
COOLDOWN_SECONDS = 2.0
CAPTURE_WIDTH = 500
CAPTURE_HEIGHT = 300
ENABLE_AMBIENT_DWELL = False  # Set to True only if you want automatic background captures on mouse pause


# UI Overlay Settings
OVERLAY_OFFSET_X = 20
OVERLAY_OFFSET_Y = 20
AUTO_DISMISS_SECONDS = 8.0

# LLM Reasoning Behavior
AUTO_RESOLVE_ON_CAPTURE = False  # False = Only call LLM when user clicks ⚡; True = Auto-call LLM on OCR detection

# Hotkey Trigger
GLOBAL_HOTKEY = "<ctrl>+<shift>+<space>"

# AI Settings
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")

# Exa.ai Neural Search Settings
EXA_API_KEY = os.getenv("EXA_API_KEY", "")
EXA_CONFIDENCE_THRESHOLD = float(os.getenv("EXA_CONFIDENCE_THRESHOLD", "0.90"))

# External MCP Integrations
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
