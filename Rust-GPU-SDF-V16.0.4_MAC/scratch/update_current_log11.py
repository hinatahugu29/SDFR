import json
import os
from datetime import datetime, timezone, timedelta

log_path = r"e:\blender_addon\外部テスト\Rust-GPU-SDF-V15.9.9.5\agent-work-log.json"

new_entry = {
  "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat(),
  "user_request_summary": "V15.9.9.5において実装を完了したすべてのパフォーマンス改善策の整理・説明依頼。",
  "ai_interpretation": "ユーザーは V15.9.9.5 で適用された最適化の全体像（どのようなアプローチでどこを軽量化したか）を整理して振り返りたいと理解。実装した5つの改善策の技術的内容と効果を分かりやすく整理して回答する。",
  "status": "completed",
  "duration_minutes": 5,
  "files_changed": [],
  "executed_actions": [
    "V15.9.9.5 で実装した全パフォーマンス改善策（選択状態同期の軽量化、仕切り判定ハッシュセット化、操作中同期スキップ、差分早期リターンなど）の整理"
  ],
  "uploaded_images": [],
  "notes": "コード発行は行わず、実装した改善点ごとの変更内容と具体的な体感効果（メリット）を明確に整理した。"
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
