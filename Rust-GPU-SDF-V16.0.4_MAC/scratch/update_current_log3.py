import json
import os
from datetime import datetime, timezone, timedelta

log_path = r"e:\blender_addon\外部テスト\Rust-GPU-SDF-V15.9.9.4\agent-work-log.json"

new_entry = {
  "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat(),
  "user_request_summary": "現状の軽量化施策（V15.9.9.4）を適用してもまだ重い・カクつく場合の、追加的な改善施策やパフォーマンス向上アイデアについての提案依頼。",
  "ai_interpretation": "ユーザーは現在の最適化の限界を見据え、さらなるパフォーマンス改善のための技術的なアプローチ（ビューポート解像度制御、トランスフォーム中の同期スキップ、Throttle処理など）を知りたいと理解。コード実装を行わず、アイデアと設計方針をわかりやすく整理して提示する。",
  "status": "completed",
  "duration_minutes": 10,
  "files_changed": [],
  "executed_actions": [
    "GPU（レイマーチ）およびCPU（Python/Blender側）のボトルネック要因の分析",
    "さらなる最適化アプローチ（ビューポート解像度スケール、トランスフォーム中の同期抑止、Depsgraph更新の間引き）の考察とドキュメント化"
  ],
  "uploaded_images": [],
  "notes": "コード発行不要との指示に従い、提案のみを論理的にまとめた。"
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
