"""
VLM の判断結果に基づいてゲーム操作を実行するモジュール。
"""

from __future__ import annotations

import logging

import pyautogui

import window_manager
from models import GameAction

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1

logger = logging.getLogger(__name__)

_ALLOWED_KEYS = frozenset(
    {"left", "right", "up", "down", "enter", "space", "escape"}
)


def execute_action(action: GameAction, hwnd: int) -> None:
    if action.type == "click":
        left, top, right, bottom = window_manager.get_window_rect(hwnd)
        w = max(1, right - left)
        h = max(1, bottom - top)
        actual_x = left + int(action.x * (w / 512))
        actual_y = top + int(action.y * (h / 288))

        if not (left <= actual_x < right and top <= actual_y < bottom):
            logger.warning(
                "クリック座標がウィンドウ外のためスキップ: (%s, %s) rect=(%s,%s,%s,%s)",
                actual_x,
                actual_y,
                left,
                top,
                right,
                bottom,
            )
            return

        pyautogui.click(actual_x, actual_y)
        return

    if action.type == "key":
        key = (action.key or "").strip().lower()
        if key not in _ALLOWED_KEYS:
            logger.warning("許可されていないキーは無視: %r", action.key)
            return
        pyautogui.press(key)
        return

    if action.type == "wait":
        return

    logger.warning("未知の action.type を無視: %r", action.type)
