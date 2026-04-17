"""
ローカル VLM（Qwen2.5-VL）の管理と推論を担当するモジュール。
"""

from __future__ import annotations

import gc
import json
import logging
import os
import re
from fnmatch import fnmatch
from typing import Any

from huggingface_hub import hf_hub_download, list_repo_files

import config
from models import GameAction, VLMResponse

logger = logging.getLogger(__name__)

_llm: Any = None

SYSTEM_PROMPT = """あなたはRPGゲーム「アナザーエデン」を操作するAIアシスタント「LUNA」です。
スクリーンショットを見て現在の画面状態を判定し、次の操作を決定してください。

■ 画面状態の分類（scene）:
- "field"             : フィールド画面。キャラが立っており、移動可能
- "battle_command"    : 戦闘画面。下部にキャラアイコンが並び、右下に「攻撃」ボタンがある
- "battle_animation"  : 戦闘演出中。エフェクト表示中で操作不可
- "battle_result"     : 戦闘リザルト。経験値やドロップアイテム表示
- "dialog"            : テキストウィンドウ/ダイアログ表示中
- "loading"           : ロード中（黒画面や回転アイコン）
- "unknown"           : 上記に該当しない

■ 応答は以下のJSON形式のみで返すこと（JSON以外のテキスト禁止）:
{
  "scene": "上記のいずれか",
  "description": "画面の簡潔な説明（日本語20文字以内）",
  "action": {
    "type": "click" または "key" または "wait",
    "x": 数値（type=click時のみ、画像上の相対X座標 0-512）,
    "y": 数値（type=click時のみ、画像上の相対Y座標 0-288）,
    "key": "right" | "left" | "enter" | "space"等（type=key時のみ）,
    "reason": "操作理由（10文字以内）"
  },
  "next_wait": 秒数（推奨: field=1.5, battle_command=3.0, 演出中=2.0, リザルト=1.0）
}

■ ルール:
- 「きおく」機能ONの前提。戦闘中はスキル選択不要で「攻撃」ボタンを押すだけでよい
- 「攻撃」ボタンは画面右下付近にある
- リザルト画面は画面中央をクリックすれば閉じる
- battle_animation / loading では必ず type:"wait" を返すこと
- unknown の場合も type:"wait" を返すこと
- セーブ・終了・ガチャなど不可逆な操作は絶対にしないこと
"""


def _first_repo_file(repo_id: str, pattern: str) -> str:
    names = list_repo_files(repo_id=repo_id)
    pat = pattern.lower()
    hits = sorted(n for n in names if fnmatch(n.lower(), pat))
    if not hits:
        raise FileNotFoundError(
            f"No file matching pattern {pattern!r} in repo {repo_id}"
        )
    return hits[0]


def _download_model_file(repo_id: str, pattern: str) -> str:
    filename = _first_repo_file(repo_id, pattern)
    return hf_hub_download(
        repo_id=repo_id,
        filename=filename,
        cache_dir=config.MODEL_DIR,
    )


def _parse_json_content(raw: str) -> dict[str, Any]:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()
    return json.loads(text)


def _default_response() -> VLMResponse:
    return VLMResponse(
        scene="unknown",
        description="",
        action=GameAction(type="wait", reason="parse"),
        next_wait=config.LOOP_DEFAULT_INTERVAL,
    )


def is_model_loaded() -> bool:
    return _llm is not None


def load_model() -> None:
    global _llm
    _llm = None
    gc.collect()

    logger.info("モデルロード中...")
    try:
        model_path = _download_model_file(config.VLM_REPO_ID, config.VLM_MODEL_GLOB)
        mmproj_path = _download_model_file(config.VLM_REPO_ID, config.VLM_MMPROJ_GLOB)
    except Exception as e:
        logger.exception("モデルファイルの取得に失敗: %s", e)
        return

    logger.info("モデルファイル: %s", os.path.basename(model_path))
    logger.info("mmproj ファイル: %s", os.path.basename(mmproj_path))

    chat_handler = None
    handler_name = "none"

    try:
        from llama_cpp.llama_chat_format import Qwen25VLChatHandler

        chat_handler = Qwen25VLChatHandler(clip_model_path=mmproj_path)
        handler_name = "Qwen25VLChatHandler"
        logger.info("Chat handler: %s", handler_name)
    except ImportError:
        logger.warning(
            "Qwen25VLChatHandler が見つかりません（llama-cpp-python >= 0.3.10 が必要）"
        )
    except Exception as e:
        logger.warning("Qwen25VLChatHandler 初期化失敗: %s", e)

    if chat_handler is None:
        try:
            from llama_cpp.llama_chat_format import Llava15ChatHandler

            chat_handler = Llava15ChatHandler(clip_model_path=mmproj_path)
            handler_name = "Llava15ChatHandler (fallback)"
            logger.info("Chat handler: %s", handler_name)
        except Exception as e:
            logger.error(
                "Llava15ChatHandler フォールバックも失敗: %s\n"
                "→ llama-cpp-python を 0.3.13 以上に更新してください:\n"
                "  pip install --upgrade llama-cpp-python",
                e,
            )
            raise RuntimeError(
                "VLM Chat Handler を初期化できません。"
                "pip install --upgrade llama-cpp-python を実行してください。"
            ) from e

    from llama_cpp import Llama

    kwargs = dict(
        model_path=model_path,
        chat_handler=chat_handler,
        n_ctx=config.VLM_N_CTX,
        n_gpu_layers=config.VLM_N_GPU_LAYERS,
        verbose=False,
    )

    try:
        _llm = Llama(**kwargs)
    except Exception as e:
        logger.warning("n_gpu_layers=%s で失敗、0にフォールバック: %s", config.VLM_N_GPU_LAYERS, e)
        kwargs["n_gpu_layers"] = 0
        try:
            _llm = Llama(**kwargs)
        except Exception as e2:
            logger.exception("モデル初期化に失敗: %s", e2)
            _llm = None
            return

    logger.info("モデルロード完了")


def unload_model() -> None:
    global _llm
    _llm = None
    gc.collect()


def analyze_screenshot(
    screenshot_data_uri: str,
    user_prompt: str,
    action_log: list[dict],
) -> VLMResponse:
    if _llm is None:
        return _default_response()

    log_lines: list[str] = []
    for entry in action_log[-5:]:
        log_lines.append(
            f"- {entry.get('timestamp', '')} [{entry.get('scene', '')}] "
            f"{entry.get('description', '')}"
        )
    log_block = "\n".join(log_lines) if log_lines else "（なし）"

    user_text = (
        "■ ユーザー指示:\n"
        f"{user_prompt}\n\n"
        "■ 直近の行動ログ:\n"
        f"{log_block}\n"
    )

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user_text},
                {"type": "image_url", "image_url": {"url": screenshot_data_uri}},
            ],
        },
    ]

    completion_kwargs: dict[str, Any] = {
        "messages": messages,
        "max_tokens": 512,
        "temperature": 0.1,
    }
    try:
        out = _llm.create_chat_completion(
            **completion_kwargs,
            response_format={"type": "json_object"},
        )
    except TypeError:
        out = _llm.create_chat_completion(**completion_kwargs)
    except Exception:
        logger.exception("VLM create_chat_completion 失敗")
        return _default_response()

    try:
        content = out["choices"][0]["message"]["content"]
        data = _parse_json_content(content)
        action_raw = data.get("action") or {}
        action = GameAction(
            type=str(action_raw.get("type", "wait")),
            x=int(action_raw.get("x", 0) or 0),
            y=int(action_raw.get("y", 0) or 0),
            key=str(action_raw.get("key", "") or ""),
            reason=str(action_raw.get("reason", "") or ""),
        )
        return VLMResponse(
            scene=str(data.get("scene", "unknown")),
            description=str(data.get("description", "")),
            action=action,
            next_wait=float(data.get("next_wait", config.LOOP_DEFAULT_INTERVAL)),
        )
    except Exception:
        logger.exception("VLM JSON パース失敗")
        return _default_response()
