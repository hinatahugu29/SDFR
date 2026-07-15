import json
import os
from datetime import datetime, timezone, timedelta

log_path = r"g:\blender_addon\外部テスト\Rust-GPU-SDF-V15.9.8.1\agent-work-log.json"

new_entry = {
  "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat(),
  "user_request_summary": "Blenderアドオン有効化時に `NameError: name 'persistent' is not defined` エラーが発生する報告。",
  "ai_interpretation": "先ほどの _duplicate_cooldown フラグ追加の編集時、AIの置換処理のフォールバックによって意図せず @persistent 行が重複・あるいはインポートを消してしまったことによる構文エラーだと理解。直ちに bpy.app.handlers から persistent をインポートする記述を追加して修正する必要がある。",
  "status": "completed",
  "duration_minutes": 5,
  "files_changed": [
    "rust_gpu_sdf_addon/handlers.py"
  ],
  "executed_actions": [
    "handlers.py の先頭に `from bpy.app.handlers import persistent` を追加",
    "アドオンを再ビルド"
  ],
  "notes": "AIの自動置換による軽微なインポート漏れエラー。即座に修正し再ビルドを完了。"
}

if os.path.exists(log_path):
    with open(log_path, "r", encoding="utf-8") as f:
        try:
            logs = json.load(f)
        except json.JSONDecodeError:
            logs = []
else:
    logs = []

logs.append(new_entry)

with open(log_path, "w", encoding="utf-8") as f:
    json.dump(logs, f, ensure_ascii=False, indent=2)

print("Log appended successfully.")
