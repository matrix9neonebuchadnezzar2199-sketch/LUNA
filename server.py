"""
FastAPI サーバーのメインファイル。エントリーポイント。
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("PYTHONUTF8", "1")

import logging

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import config
import vlm
from engine import MonitorEngine
from models import MonitorStartRequest, StatusResponse, WindowInfo, WindowSelectRequest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("luna.server")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

engine = MonitorEngine()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("起動処理: モデルロードを開始します")
    try:
        vlm.load_model()
    except Exception as e:
        logger.exception("モデルロード中に予期しないエラー: %s", e)

    yield

    logger.info("シャットダウン: 監視停止とモデルアンロード")
    try:
        await engine.stop()
    except Exception as e:
        logger.exception("engine.stop 失敗: %s", e)
    try:
        vlm.unload_model()
    except Exception as e:
        logger.exception("vlm.unload_model 失敗: %s", e)


app = FastAPI(title="LUNA", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def root() -> FileResponse:
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/api/windows", response_model=list[WindowInfo])
async def api_windows() -> list[WindowInfo]:
    try:
        import window_manager

        return window_manager.get_window_list()
    except Exception as e:
        logger.exception("api_windows")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/windows/select")
async def api_windows_select(body: WindowSelectRequest) -> dict:
    try:
        thumb = engine.select_window(body.hwnd)
        return {"status": "ok", "thumbnail": thumb}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("api_windows_select")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/monitor/start")
async def api_monitor_start(body: MonitorStartRequest) -> dict:
    try:
        await engine.start(body.prompt)
        return {"status": "ok"}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("api_monitor_start")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/monitor/pause")
async def api_monitor_pause() -> dict:
    try:
        await engine.pause()
        return {"status": "ok"}
    except Exception as e:
        logger.exception("api_monitor_pause")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/monitor/resume")
async def api_monitor_resume() -> dict:
    try:
        await engine.resume()
        return {"status": "ok"}
    except Exception as e:
        logger.exception("api_monitor_resume")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/monitor/stop")
async def api_monitor_stop() -> dict:
    try:
        await engine.stop()
        return {"status": "ok"}
    except Exception as e:
        logger.exception("api_monitor_stop")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/status", response_model=StatusResponse)
async def api_status() -> StatusResponse:
    try:
        return engine.get_status()
    except Exception as e:
        logger.exception("api_status")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/health")
async def api_health() -> dict:
    try:
        return {"status": "ok", "model_loaded": vlm.is_model_loaded()}
    except Exception as e:
        logger.exception("api_health")
        raise HTTPException(status_code=500, detail=str(e)) from e


if __name__ == "__main__":
    uvicorn.run(app, host=config.SERVER_HOST, port=config.SERVER_PORT)
