# LUNA（Week 1 MVP）

ローカル VLM でゲーム画面を監視し、操作を自動化する Windows 向けツールの最小構成です。

## 前提

- Windows 10 / 11
- Python **3.11 以上**（**3.14** でも可。古い `Pillow==11.x` / `pydantic==2.11.x` 固定だとビルドに失敗するため、本リポジトリの `requirements.txt` は **Pillow 12+ / pydantic 2.12+** に合わせています）
- 初回起動時に Hugging Face の **`ggml-org/Qwen2.5-VL-3B-Instruct-GGUF`** から **メイン GGUF** と **mmproj** が `~/.luna/models/` にダウンロードされます（容量・時間に注意）

**`ModuleNotFoundError`（例: pyautogui）のときは、必ず次を実行してから `python server.py` してください。**

```powershell
python -m pip install -r requirements.txt
```

## セットアップ

リポジトリのルート（本 README があるディレクトリ）で実行します。

```powershell
git clone https://github.com/matrix9neonebuchadnezzar2199-sketch/LUNA.git
cd LUNA
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

`llama-cpp-python` がビルドを要求する場合は、Visual Studio Build Tools 等の C++ 環境が必要になることがあります（環境によってはホイールが使えます）。

## 起動

仮想環境を有効化したうえで、リポジトリルートで実行します。

```powershell
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
