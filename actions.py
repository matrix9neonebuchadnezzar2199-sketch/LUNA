"""
VLM の判断結果に基づいてゲーム操作を実行するモジュール。

キー・クリックは可能な限り PostMessage で送り、フォアグラウンドに依存しない。
失敗時のみ SetForegroundWindow + pyautogui にフォールバックする。
"""

from __future__ import annotations

import logging
import time

import pyautogui
import win32api
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

VK_MAP: dict[str, int] = {
    "left": win32con.VK_LEFT,
    "right": win32con.VK_RIGHT,
    "up": win32con.VK_UP,
    "down": win32con.VK_DOWN,
    "enter": win32con.VK_RETURN,
    "space": win32con.VK_SPACE,
    "escape": win32con.VK_ESCAPE,
}

# WM_KEYDOWN の lParam bit24（拡張キー）が必要なもの
_EXTENDED_VK = frozenset(
    {
        win32con.VK_LEFT,
        win32con.VK_RIGHT,
        win32con.VK_UP,
        win32con.VK_DOWN,
    }
)


def _key_lparam(scan: int, vk: int, *, is_up: bool) -> int:
    """KEYDOWN / KEYUP 用 lParam を組み立てる。"""
    lp = 1 | (scan << 16)
    if vk in _EXTENDED_VK:
        lp |= 1 << 24
    if is_up:
        lp |= 1 << 30
        lp |= 1 << 31
    return lp


def _send_key_to_window(hwnd: int, key: str) -> bool:
    """HWND に WM_KEYDOWN / WM_KEYUP を送る（アクティブ化不要）。"""
    vk = VK_MAP.get(key)
    if vk is None:
        logger.warning("VK コードが未定義: %s", key)
        return False
    try:
        scan = win32api.MapVirtualKey(vk, 0) & 0xFF
        lp_down = _key_lparam(scan, vk, is_up=False)
        lp_up = _key_lparam(scan, vk, is_up=True)

        win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, vk, lp_down)
        time.sleep(0.05)
        win32gui.PostMessage(hwnd, win32con.WM_KEYUP, vk, lp_up)
        return True
    except Exception as e:
        logger.warning("PostMessage キー送信失敗 (hwnd=%s, key=%s): %s", hwnd, key, e)
        return False


def _click_client(hwnd: int, client_x: int, client_y: int) -> bool:
    """クライアント座標で WM_LBUTTONDOWN / UP を送る。"""
    try:
        lp = win32api.MAKELONG(client_x & 0xFFFF, client_y & 0xFFFF)
        win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lp)
        time.sleep(0.05)
        win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lp)
        return True
    except Exception as e:
        logger.warning(
            "PostMessage クリック失敗 (hwnd=%s, cx=%s, cy=%s): %s",
            hwnd,
            client_x,
            client_y,
            e,
        )
        return False


def _activate_window(hwnd: int) -> bool:
    """フォールバック用: フォアグラウンド化を試みる。"""
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.1)
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.05)
        return True
    except Exception as e:
        logger.warning("SetForegroundWindow 失敗 (hwnd=%s): %s", hwnd, e)
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

    if action.type == "key":
        key = (action.key or "").strip().lower()
        if key not in _ALLOWED_KEYS:
            logger.warning("許可されていないキーは無視: %r", action.key)
            return

        if _send_key_to_window(hwnd, key):
            logger.info("key: %s (PostMessage)", key)
            return

        logger.info("PostMessage 失敗、pyautogui にフォールバック (key=%s)", key)
        _activate_window(hwnd)
        pyautogui.press(key)
        logger.info("key: %s (pyautogui fallback)", key)
        return

    if action.type == "click":
        left, top, right, bottom = window_manager.get_window_rect(hwnd)
        w = max(1, right - left)
        h = max(1, bottom - top)
        screen_x = left + int(action.x * (w / config.CAPTURE_RESIZE_WIDTH))
        screen_y = top + int(action.y * (h / config.CAPTURE_RESIZE_HEIGHT))

        if not (left <= screen_x < right and top <= screen_y < bottom):
            logger.warning(
                "クリック座標がウィンドウ外のためスキップ: (%s, %s) rect=(%s,%s,%s,%s)",
                screen_x,
                screen_y,
                left,
                top,
                right,
                bottom,
            )
            return

        try:
            cx, cy = win32gui.ScreenToClient(hwnd, (screen_x, screen_y))
        except Exception as e:
            logger.warning("ScreenToClient 失敗: %s", e)
            cx = cy = 0

        if _click_client(hwnd, int(cx), int(cy)):
            logger.info(
                "click 正規化(%s,%s) → screen(%s,%s) client(%s,%s) (PostMessage)",
                action.x,
                action.y,
                screen_x,
                screen_y,
                cx,
                cy,
            )
            return

        logger.info("PostMessage クリック失敗、pyautogui にフォールバック")
        _activate_window(hwnd)
        pyautogui.click(screen_x, screen_y)
        logger.info(
            "click 正規化(%s,%s) → screen(%s,%s) (pyautogui fallback)",
            action.x,
            action.y,
            screen_x,
            screen_y,
        )
        return
