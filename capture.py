"""
指定ウィンドウの画面をキャプチャするモジュール。
"""

import base64
import io

import mss
from PIL import Image

import config
import window_manager


def _grab_to_data_uri(hwnd: int, width: int, height: int) -> str:
    left, top, right, bottom = window_manager.get_window_rect(hwnd)
    w = max(1, right - left)
    h = max(1, bottom - top)
    region = {"left": left, "top": top, "width": w, "height": h}

    with mss.mss() as sct:
        sct_img = sct.grab(region)

    img = Image.frombytes(
        "RGB",
        (sct_img.width, sct_img.height),
        sct_img.bgra,
        "raw",
        "BGRX",
    )
    img = img.resize((width, height), Image.Resampling.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def capture_window(hwnd: int) -> str:
    return _grab_to_data_uri(
        hwnd,
        config.CAPTURE_RESIZE_WIDTH,
        config.CAPTURE_RESIZE_HEIGHT,
    )


def capture_window_thumbnail(hwnd: int) -> str:
    return _grab_to_data_uri(hwnd, 256, 144)
