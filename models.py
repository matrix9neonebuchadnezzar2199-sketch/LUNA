"""
Pydantic データモデル定義。
"""

from enum import Enum

from pydantic import BaseModel, Field


class AppState(str, Enum):
    IDLE = "idle"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


class WindowInfo(BaseModel):
    hwnd: int
    title: str


class GameAction(BaseModel):
    type: str
    x: int = 0
    y: int = 0
    key: str = ""
    reason: str = ""


class VLMResponse(BaseModel):
    scene: str
    description: str
    action: GameAction
    next_wait: float = 2.0


class LogEntry(BaseModel):
    timestamp: str
    scene: str
    action_type: str
    description: str


class WindowSelectRequest(BaseModel):
    hwnd: int


class MonitorStartRequest(BaseModel):
    prompt: str


class StatusResponse(BaseModel):
    state: AppState
    target_window: str | None = None
    logs: list[LogEntry] = Field(default_factory=list)
    stats: dict = Field(default_factory=dict)
