"""
設定値を一元管理するモジュール。
"""

import os

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8765

MODEL_DIR = os.path.expanduser("~/.luna/models/")
os.makedirs(MODEL_DIR, exist_ok=True)

VLM_REPO_ID = "Qwen/Qwen2.5-VL-3B-Instruct-GGUF"
VLM_MODEL_GLOB = "*q4_k_m*.gguf"
VLM_MMPROJ_GLOB = "*mmproj*.gguf"

VLM_N_CTX = 2048
VLM_N_GPU_LAYERS = -1

CAPTURE_RESIZE_WIDTH = 512
CAPTURE_RESIZE_HEIGHT = 288

LOOP_MIN_INTERVAL = 0.5
LOOP_DEFAULT_INTERVAL = 2.0
VLM_TIMEOUT = 30
MAX_ACTION_LOG = 50
