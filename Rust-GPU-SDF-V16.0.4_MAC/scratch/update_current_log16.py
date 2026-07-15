import json
import os
from datetime import datetime, timezone, timedelta

log_path = r"e:\blender_addon\外部テスト\Rust-GPU-SDF-V15.9.9.5\agent-work-log.json"

new_entry = {
  "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat(),
  "user_request_summary": "カメラ操作中のダイナミックステップ数制限適用後のシステムコンソールログ検証依頼。",
  "ai_interpretation": "ユーザーは、先ほど実装した最適化（カメラ操作中のステップクランプ）によって実際にパフォーマンスが向上したかを確認したいと理解。ログから、カメラ回転中のFPSが20〜24FPSから38〜40FPSへと約2倍に大幅改善していることを定量的に確認し、報告する。",
  "status": "completed",
  "duration_minutes": 5,
  "files_changed": [],
  "executed_actions": [
    "改善前後のシステムコンソールログ（FPS）の比較・分析"
  ],
  "uploaded_images": [],
  "notes": "Pythonの処理時間（0.08ms）を極小に保ったまま、GPU側のレイマーチング負荷の半減（ステップ数制限）が功を奏し、FPSが2倍近くに向上したことを確認した。"
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
