"""
設定値を一元管理するモジュール。
"""

import os

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8765

MODEL_DIR = os.path.expanduser("~/.luna/models/")
os.makedirs(MODEL_DIR, exist_ok=True)

# VL GGUF は ggml-org（llama.cpp 側の変換物）。Qwen 公式の VL-GGUF リポジトリは別IDのためこちらを使用。
VLM_REPO_ID = "ggml-org/Qwen2.5-VL-3B-Instruct-GGUF"
VLM_MODEL_GLOB = "*Q4_K_M*.gguf"
VLM_MMPROJ_GLOB = "*mmproj*.gguf"

VLM_N_CTX = 2048
VLM_N_GPU_LAYERS = -1

CAPTURE_RESIZE_WIDTH = 512
CAPTURE_RESIZE_HEIGHT = 288

LOOP_MIN_INTERVAL = 0.5
LOOP_DEFAULT_INTERVAL = 2.0
VLM_TIMEOUT = 30
MAX_ACTION_LOG = 50
