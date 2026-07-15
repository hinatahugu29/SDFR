import json
import os
from datetime import datetime, timezone, timedelta

log_path = r"e:\blender_addon\外部テスト\Rust-GPU-SDF-V15.9.9.5\agent-work-log.json"

new_entry = {
  "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat(),
  "user_request_summary": "プリミティブ増加時のカメラ速度低下（カクつき）に関するシステムコンソールログの分析依頼。",
  "ai_interpretation": "ユーザーが提示したログ（Preview Draw FPS の低下傾向）を技術的に分析。Python側の処理時間（avg duration: 0.08ms）が極めて小さいことから、CPU側のボトルネックではなく「GPU側のレイマーチング負荷」または「Blenderのソースオブジェクト描画負荷」が主因であることを特定。前段階で提案した追加施策（ソース非表示、描画間引き）の有効性を解説する。",
  "status": "completed",
  "duration_minutes": 5,
  "files_changed": [],
  "executed_actions": [
    "システムコンソールログ（Preview Draw FPS, avg duration, texture rebuilds）の定量解析と、カメラ速度低下の根本原因の特定"
  ],
  "uploaded_images": [],
  "notes": "Python側が約0.1msという超高速で処理を終えているのに対し、ビューポート自体が20FPS付近まで落ちているデータから、GPU負荷およびBlenderの標準描画負荷がボトルネックであると断定した。"
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
