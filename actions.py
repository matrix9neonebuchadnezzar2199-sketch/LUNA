"""
VLM の判断結果に基づいてゲーム操作を実行するモジュール。
"""

from __future__ import annotations

import logging
import time

import pyautogui
import win32con
import win32gui

import config
import window_manager
from models import GameAction

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1

logger = logging.getLogger(__name__)

_ALLOWED_KEYS = frozenset(
    {"left", "right", "up", "down", "enter", "space", "escape"}
)


def _activate_window(hwnd: int) -> bool:
    """対象ウィンドウをフォアグラウンドにする（キー・クリックが届くように）。"""
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.1)

        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.05)
        return True
    except Exception as e:
        logger.warning("ウィンドウのアクティブ化に失敗 (hwnd=%s): %s", hwnd, e)
        return False


def execute_action(action: GameAction, hwnd: int) -> None:
    if not window_manager.window_exists(hwnd):
        logger.warning("対象ウィンドウが存在しません (hwnd=%s)", hwnd)
        return

    if action.type == "wait":
        return

    if action.type not in ("click", "key"):
        logger.warning("未知の action.type を無視: %r", action.type)
        return

    if not _activate_window(hwnd):
        logger.warning(
            "ウィンドウをアクティブにできないため、アクション '%s' をスキップ",
            action.type,
        )
        return

    if action.type == "click":
        left, top, right, bottom = window_manager.get_window_rect(hwnd)
        w = max(1, right - left)
        h = max(1, bottom - top)
        actual_x = left + int(
            action.x * (w / config.CAPTURE_RESIZE_WIDTH)
        )
        actual_y = top + int(
            action.y * (h / config.CAPTURE_RESIZE_HEIGHT)
        )

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
        logger.info(
            "click 正規化(%s,%s) → 実座標(%s,%s)",
            action.x,
            action.y,
            actual_x,
            actual_y,
        )
        return

    if action.type == "key":
        key = (action.key or "").strip().lower()
        if key not in _ALLOWED_KEYS:
            logger.warning("許可されていないキーは無視: %r", action.key)
            return
        pyautogui.press(key)
        logger.info("key: %s", key)
        return
