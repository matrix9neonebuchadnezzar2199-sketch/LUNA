# LUNA（Week 1 MVP）

ローカル VLM でゲーム画面を監視し、操作を自動化する Windows 向けツールの最小構成です。

## 前提

- Windows 10 / 11
- Python **3.11 以上**
- 初回起動時に Hugging Face から **Qwen2.5-VL-3B-Instruct（GGUF）** と **mmproj** が `~/.luna/models/` にダウンロードされます（容量・時間に注意）。

## セットアップ

```powershell
cd luna
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

`llama-cpp-python` がビルドを要求する場合は、Visual Studio Build Tools 等の C++ 環境が必要になることがあります（環境によってはホイールが使えます）。

## 起動

```powershell
cd luna
.\.venv\Scripts\Activate.ps1
python server.py
```

コンソールに「モデルロード中…」「モデルロード完了」（失敗時はエラー）のあと、`Uvicorn running on http://127.0.0.1:8765` が表示されたらブラウザで次を開きます。

- http://localhost:8765/

## 動作確認の流れ

1. 「一覧更新」でウィンドウ一覧を取得
2. 対象（例: メモ帳）を選び「選択」→ プレビュー表示・状態が **READY**
3. プロンプトを入力し「▶ 開始」→ **RUNNING**、ログが更新される
4. 「⏸ 一時停止」→ **PAUSED**、「▶ 再開」→ **RUNNING**
5. 「■ 停止」→ **IDLE**

## プロジェクト構成

- `server.py` — FastAPI エントリ
- `engine.py` — 監視ループ・状態
- `vlm.py` / `capture.py` / `actions.py` / `window_manager.py`
- `static/` — ブラウザ UI

## Week 1 スコープ外

PyInstaller、SSE/WebSocket ログ、ループ間隔の UI 変更などは含みません。
