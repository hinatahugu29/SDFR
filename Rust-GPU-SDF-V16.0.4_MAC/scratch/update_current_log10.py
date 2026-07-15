import json
import os
from datetime import datetime, timezone, timedelta

log_path = r"e:\blender_addon\外部テスト\Rust-GPU-SDF-V15.9.9.5\agent-work-log.json"

new_entry = {
  "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat(),
  "user_request_summary": "提案した4つの追加最適化施策について、それぞれのリスクとコストパフォーマンス（効果 vs 実装コスト）の整理依頼。",
  "ai_interpretation": "ユーザーは、次にどの最適化施策を導入すべきかを意思決定するため、技術的難易度（リスク）と体感効果（コスパ）の比較情報を求めていると理解。4つの施策について論理的に比較・分析して提示する。",
  "status": "completed",
  "duration_minutes": 5,
  "files_changed": [],
  "executed_actions": [
    "フレームスキップ、ローカルドメイン、Debounce同期、ソース非表示化の「リスク」「実装コスト」「効果」「コスパ感」の比較・整理"
  ],
  "uploaded_images": [],
  "notes": "コード発行は行わず、マトリクス形式または整理されたテキストで開発者判断に役立つ指標を提示した。"
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
