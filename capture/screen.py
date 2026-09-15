"""Screen capture utilities with dedicated captures/ storage folder."""

import os
from datetime import datetime
from typing import Tuple
from pathlib import Path
import mss
from PIL import Image
import numpy as np
from config import BASE_DIR, CAPTURE_WIDTH, CAPTURE_HEIGHT

# Dedicated directory for storing all screen captures
CAPTURES_DIR = os.path.join(BASE_DIR, "captures")
os.makedirs(CAPTURES_DIR, exist_ok=True)

LAST_CAPTURE_PATH = os.path.join(CAPTURES_DIR, "last_capture.png")


def capture_around_cursor(
    x: int, 
    y: int, 
    width: int = 500, 
    height: int = 300,
    save_to_disk: bool = True
) -> Tuple[Image.Image, str]:
    """
    Captures a region centered directly around the mouse cursor (x, y).
    This targets the exact error or code line the user is hovering over.
    Saves the image into 'captures/' folder and returns (PIL.Image, saved_path).
    """
    img = None
    saved_path = ""

    try:
        with mss.mss() as sct:
            primary = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
            screen_left = primary["left"]
            screen_top = primary["top"]
            screen_width = primary["width"]
            screen_height = primary["height"]

            half_w = width // 2
            half_h = height // 2

            left = max(screen_left, min(x - half_w, screen_left + screen_width - width))
            top = max(screen_top, min(y - half_h, screen_top + screen_height - height))

            bbox = {
                "left": int(left),
                "top": int(top),
                "width": int(width),
                "height": int(height)
            }

            sct_img = sct.grab(bbox)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
    except Exception as e:
        # Graceful fallback: try PIL.ImageGrab
        try:
            from PIL import ImageGrab
            bbox = (x - width // 2, y - height // 2, x + width // 2, y + height // 2)
            img = ImageGrab.grab(bbox=bbox)
        except Exception as e2:
            print(f"[Screen] Grab error: {e2}")
            img = Image.new("RGB", (width, height), color=(25, 25, 35))

    # Save to disk
    if save_to_disk and img:
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"capture_cursor_{timestamp}.png"
            saved_path = os.path.join(CAPTURES_DIR, filename)
            img.save(saved_path)
            img.save(LAST_CAPTURE_PATH)
            root_last = os.path.join(BASE_DIR, "last_capture.png")
            img.save(root_last)
            print(f"[Screen] Captured {img.width}x{img.height} under cursor ({x}, {y}) -> Saved to 'captures/{filename}'")
        except Exception as e:
            print(f"[Screen] Save warning: {e}")

    return img, saved_path


def capture_entire_screen(save_to_disk: bool = True) -> Tuple[Image.Image, str]:
    """
    Captures the ENTIRE primary screen at full resolution.
    """
    img = None
    saved_path = ""

    try:
        with mss.mss() as sct:
            primary = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
            sct_img = sct.grab(primary)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
    except Exception:
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab(all_screens=False)
        except Exception:
            img = Image.new("RGB", (1920, 1080), color=(25, 25, 35))

    if save_to_disk and img:
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"capture_full_{timestamp}.png"
            saved_path = os.path.join(CAPTURES_DIR, filename)
            img.save(saved_path)
            img.save(LAST_CAPTURE_PATH)
            root_last = os.path.join(BASE_DIR, "last_capture.png")
            img.save(root_last)
            print(f"[Screen] Full screen captured ({img.width}x{img.height}) -> Saved to 'captures/{filename}'")
        except Exception as e:
            print(f"[Screen] Save warning: {e}")

    return img, saved_path
