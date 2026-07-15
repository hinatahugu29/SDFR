import json
import os
from datetime import datetime, timezone, timedelta

log_path = r"e:\blender_addon\外部テスト\Rust-GPU-SDF-V15.9.9.4\agent-work-log.json"

new_entry = {
  "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat(),
  "user_request_summary": "結果メッシュ非表示（OFF）時でも発生する重さ・引っかかりの原因特定と、追加の改善施策の検討依頼。",
  "ai_interpretation": "ユーザーは「メッシュOFF（重いRust計算のスキップ）時であっても依然として引っかかりを感じる」という事実に基づき、その根本原因がPython側の同期処理やBlender APIの毎フレームアクセスによるCPUボトルネック、およびプレビュー描画負荷にあることを理解。これを解消するためのより踏み込んだ最適化戦略を提示する。",
  "status": "completed",
  "duration_minutes": 10,
  "files_changed": [],
  "executed_actions": [
    "engine.py の update_sdf_mesh 内における早期リターンの前段処理（sync_sdf_stack等）の負荷検証",
    "メッシュOFF時にも背後で動作し続ける handlers.py (draw_callback_3d) のプレビューレイマーチング負荷および重複同期の検証",
    "操作中（ドラッグ中）の不要な同期スキップや、Depsgraph構造変化時のみに同期を限定するガード戦略の構築"
  ],
  "uploaded_images": [],
  "notes": "メッシュOFF時の早期リターンが機能していても、その手前でのBlender APIへの毎フレームアクセスや、プレビュー描画コールバック側の処理がカクつきの主因になっていることを特定した。"
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
