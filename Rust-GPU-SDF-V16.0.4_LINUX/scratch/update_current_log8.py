import json
import os
from datetime import datetime, timezone, timedelta

log_path = r"e:\blender_addon\外部テスト\Rust-GPU-SDF-V15.9.9.5\agent-work-log.json"

new_entry = {
  "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat(),
  "user_request_summary": "最適化においてRust（GPUエンジン）側への変更・テコ入れが必要であるかどうかの質問。",
  "ai_interpretation": "ユーザーは、今回のパフォーマンス最適化でRust側の改修が必要かどうかを技術的に整理したいと理解。メッシュOFF時のボトルネックがPython側（APIアクセスと同期オーバーヘッド）に完全に閉じていたため、今回の改修範囲ではRust側の変更が不要である理由を論理的に解説する。",
  "status": "completed",
  "duration_minutes": 5,
  "files_changed": [],
  "executed_actions": [
    "Rust側（メッシュ生成、GPU/WGSLレイマーチング）の関与度の整理と、改修の必要性に関する技術的分析"
  ],
  "uploaded_images": [],
  "notes": "今回はアドオン側（Python層）のボトルネック解消がメインであるためRust側は不要であることを確認。将来的な空間分割などの極限最適化案についても考察した。"
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
