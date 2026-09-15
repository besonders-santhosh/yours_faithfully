"""OCR extraction engine for AeroTrace with fast WinOCR and EasyOCR support."""

import os
import sys
import asyncio
from typing import Optional
from PIL import Image

os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUTF8"] = "1"

_easyocr_reader = None


def get_easyocr_reader():
    global _easyocr_reader
    if _easyocr_reader is None:
        try:
            import easyocr
            _easyocr_reader = easyocr.Reader(['en'], gpu=False)
        except Exception as e:
            print(f"[OCR] EasyOCR initialization notice: {e}")
            _easyocr_reader = False
    return _easyocr_reader


def extract_text_from_image(image: Image.Image) -> str:
    """
    Extracts text from PIL Image using Windows Native Media OCR (ultra-fast)
    with EasyOCR fallback.
    Returns cleaned text string.
    """
    if image is None:
        return ""

    # 1. Primary: Try native Windows Media OCR (WinOCR) - sub-100ms latency
    try:
        import winocr
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(winocr.recognize_pil(image, "en"))
        loop.close()
        text = result.text.strip()
        if text:
            return text
    except Exception as e:
        pass

    # 2. Secondary: Try EasyOCR if WinOCR didn't catch text
    reader = get_easyocr_reader()
    if reader:
        try:
            import numpy as np
            np_img = np.array(image)
            results = reader.readtext(np_img, detail=0)
            text = " ".join(results).strip()
            if text:
                return text
        except Exception as e:
            print(f"[OCR] EasyOCR error: {e}")

    return ""
