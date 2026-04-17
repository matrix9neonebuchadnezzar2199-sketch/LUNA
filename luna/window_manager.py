"""
Windows のウィンドウ一覧取得と選択を担当するモジュール。
"""

import win32gui

from models import WindowInfo


def _enum_callback(hwnd: int, acc: list[WindowInfo]) -> None:
    if not win32gui.IsWindowVisible(hwnd):
        return
    title = win32gui.GetWindowText(hwnd)
    if not title or not title.strip():
        return
    acc.append(WindowInfo(hwnd=int(hwnd), title=title))


def get_window_list() -> list[WindowInfo]:
    items: list[WindowInfo] = []

    def cb(hwnd, _):
        _enum_callback(hwnd, items)
        return True

    win32gui.EnumWindows(cb, None)
    return items


def get_window_rect(hwnd: int) -> tuple[int, int, int, int]:
    return win32gui.GetWindowRect(hwnd)


def window_exists(hwnd: int) -> bool:
    return bool(win32gui.IsWindow(hwnd))


def get_window_title(hwnd: int) -> str:
    return (win32gui.GetWindowText(hwnd) or "").strip()
