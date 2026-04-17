"""
監視ループの制御と状態管理を行うコアモジュール。
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

import actions
import capture
import config
import vlm
import window_manager
from models import AppState, LogEntry, StatusResponse

logger = logging.getLogger(__name__)


class MonitorEngine:
    def __init__(self) -> None:
        self.state: AppState = AppState.IDLE
        self.target_hwnd: int | None = None
        self.target_title: str | None = None
        self.prompt: str = ""
        self.logs: list[LogEntry] = []
        self.stats: dict = {"start_time": None, "battle_count": 0, "error_count": 0}
        self._task: asyncio.Task | None = None
        self._pause_event = asyncio.Event()
        self._pause_event.set()
        self._stop_flag: bool = False

    def select_window(self, hwnd: int) -> str:
        if self.state not in (AppState.IDLE, AppState.READY):
            raise RuntimeError(f"Cannot select window from state {self.state}")

        if not window_manager.window_exists(hwnd):
            raise RuntimeError("ウィンドウが存在しません")

        self.target_hwnd = hwnd
        self.target_title = window_manager.get_window_title(hwnd) or None

        thumb = capture.capture_window_thumbnail(hwnd)
        self.state = AppState.READY
        return thumb

    async def start(self, prompt: str) -> None:
        if self.state is not AppState.READY:
            raise RuntimeError(f"Cannot start from state {self.state}")

        self.prompt = prompt
        self._stop_flag = False
        self._pause_event.set()
        self.stats = {
            "start_time": datetime.now(),
            "battle_count": 0,
            "error_count": 0,
        }
        self.state = AppState.RUNNING
        self._task = asyncio.create_task(self._monitor_loop())

    async def pause(self) -> None:
        if self.state is not AppState.RUNNING:
            return
        self._pause_event.clear()
        self.state = AppState.PAUSED

    async def resume(self) -> None:
        if self.state is not AppState.PAUSED:
            return
        self._pause_event.set()
        self.state = AppState.RUNNING

    async def stop(self) -> None:
        self._stop_flag = True
        self._pause_event.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self.state = AppState.IDLE

    async def _monitor_loop(self) -> None:
        while not self._stop_flag:
            await self._pause_event.wait()
            if self._stop_flag:
                break

            try:
                if self.target_hwnd is None or not window_manager.window_exists(
                    self.target_hwnd
                ):
                    self._add_log("error", "wait", "対象ウィンドウが見つかりません")
                    self.stats["error_count"] += 1
                    self.state = AppState.ERROR
                    break

                screenshot_uri = capture.capture_window(self.target_hwnd)

                loop = asyncio.get_running_loop()
                vlm_result = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        vlm.analyze_screenshot,
                        screenshot_uri,
                        self.prompt,
                        [log.model_dump() for log in self.logs[-5:]],
                    ),
                    timeout=config.VLM_TIMEOUT,
                )

                if vlm_result.action.type != "wait":
                    actions.execute_action(vlm_result.action, self.target_hwnd)

                if vlm_result.scene == "battle_command":
                    self.stats["battle_count"] += 1

                self._add_log(
                    vlm_result.scene,
                    vlm_result.action.type,
                    vlm_result.description,
                )

                wait_time = max(vlm_result.next_wait, config.LOOP_MIN_INTERVAL)
                await self._interruptible_sleep(wait_time)

            except asyncio.TimeoutError:
                self._add_log("error", "wait", "VLM推論タイムアウト")
                self.stats["error_count"] += 1
                await self._interruptible_sleep(3.0)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self._add_log("error", "wait", str(e)[:50])
                self.stats["error_count"] += 1
                await self._interruptible_sleep(3.0)

    async def _interruptible_sleep(self, seconds: float) -> None:
        elapsed = 0.0
        while elapsed < seconds and not self._stop_flag:
            chunk = min(0.5, seconds - elapsed)
            await asyncio.sleep(chunk)
            elapsed += chunk

    def _add_log(self, scene: str, action_type: str, description: str) -> None:
        entry = LogEntry(
            timestamp=datetime.now().isoformat(timespec="seconds"),
            scene=scene,
            action_type=action_type,
            description=description,
        )
        self.logs.append(entry)
        if len(self.logs) > config.MAX_ACTION_LOG:
            self.logs = self.logs[-config.MAX_ACTION_LOG :]

    def get_status(self) -> StatusResponse:
        uptime = ""
        st = self.stats.get("start_time")
        if st and self.state in (AppState.RUNNING, AppState.PAUSED):
            delta = datetime.now() - st
            total = int(delta.total_seconds())
            hours, remainder = divmod(total, 3600)
            minutes, secs = divmod(remainder, 60)
            uptime = f"{hours:02d}:{minutes:02d}:{secs:02d}"

        return StatusResponse(
            state=self.state,
            target_window=self.target_title,
            logs=self.logs[-20:],
            stats={
                "uptime": uptime,
                "battle_count": self.stats.get("battle_count", 0),
                "error_count": self.stats.get("error_count", 0),
            },
        )
