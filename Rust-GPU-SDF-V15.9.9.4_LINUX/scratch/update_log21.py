import json
import os
from datetime import datetime, timezone, timedelta

log_path = r"g:\blender_addon\外部テスト\Rust-GPU-SDF-V15.9.8.1\agent-work-log.json"

new_entry = {
  "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat(),
  "user_request_summary": "バグ修正後の最終確認および、「今回のアップデートでまたかなり化けたと思うよ」という高い評価と労いの言葉をいただいた。",
  "ai_interpretation": "グループ単位での安全かつ確実な複製機能が実装・安定化したことにより、本アドオンのユーザビリティ（UI/UX）およびモデリングの効率が飛躍的に向上した（＝化けた）と評価されている。長期にわたるデバッグが実を結び、プロジェクトとして大きなマイルストーンを達成したと言える。",
  "status": "completed",
  "duration_minutes": 5,
  "files_changed": [],
  "executed_actions": [
    "ユーザーからのフィードバックの受領",
    "安定化によるプロジェクト進行の節目として記録"
  ],
  "notes": "この機能により、複雑な階層を持つSDFモデルもコンポーネント単位（グループ単位）で手軽に量産できるようになり、ツールとしての完成度と実用性が一気に引き上げられた。次なる機能開発へ向けての良い足場が完成した。"
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
