import json
import os
from datetime import datetime, timezone, timedelta

log_path = r"e:\blender_addon\外部テスト\Rust-GPU-SDF-V15.9.9.5\agent-work-log.json"

new_entry = {
  "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat(),
  "user_request_summary": "カメラドラッグ時にシェーダーの輪郭（縁）に黒いアーティファクトが発生する現象へのフィードバックに対する回答と対策の検討。",
  "ai_interpretation": "ユーザーは「操作中に縁が少し黒ずむ」という視覚的変化に気づいている。これはレイマーチステップ数を64に制限した結果、視線が掠める縁の部分で衝突判定が上限に達してしまい、背景（黒）として処理される物理的な現象であることを理解。原因の技術的解説と、緩和策（ステップ数を80や96へ微調整する案）を提示する。",
  "status": "completed",
  "duration_minutes": 5,
  "files_changed": [],
  "executed_actions": [
    "レイマーチングにおけるステップ数制限による輪郭欠落（黒縁）の発生メカニズムの分析と対策の整理"
  ],
  "uploaded_images": [],
  "notes": "操作時のFPS（40FPS）と視覚的品質のトレードオフであるため、ステップ数を64から80/96にわずかに引き上げることで両者のベストバランスを取る提案を作成した。"
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
