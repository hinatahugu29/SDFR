import json
import os
from datetime import datetime, timezone, timedelta

log_path = r"e:\blender_addon\外部テスト\Rust-GPU-SDF-V15.9.9.5\agent-work-log.json"

new_entry = {
  "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat(),
  "user_request_summary": "メッシュOFF（プレビュー動作時）において、さらに有効なパフォーマンス向上手段・施策のブレインストーミング依頼。",
  "ai_interpretation": "ユーザーはメッシュOFF時の操作体験をさらに極限まで滑らかにするための追加アイデア（フレームスキップ、ローカルドメイン、非表示化、Debounce同期など）を求めていると理解。具体的な機能設計案を整理して提示する。",
  "status": "completed",
  "duration_minutes": 10,
  "files_changed": [],
  "executed_actions": [
    "プレビュー描画間引き（Frame Skipping）、ローカルプレビュークロップ、非同期同期処理（Debounce）、ソースオブジェクト完全非表示化などの機能設計案の考察"
  ],
  "uploaded_images": [],
  "notes": "コード発行は行わず、実装難易度と体感効果のバランスを考慮した4つの追加改善案を提示した。"
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
