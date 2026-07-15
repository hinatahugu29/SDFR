import json
import os
from datetime import datetime, timezone, timedelta

log_path = r"e:\blender_addon\外部テスト\Rust-GPU-SDF-V15.9.9.5\agent-work-log.json"

new_entry = {
  "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat(),
  "user_request_summary": "実行頻度と処理時間を計測するためのデバッグログの追加・仕込みに関する提案と可能性の確認依頼。",
  "ai_interpretation": "ユーザーは各同期処理や描画ハンドラーの実際のオーバーヘッドを正確に把握したいと考えていると理解。depsgraphハンドラー、プレビュー描画、およびスタック同期の箇所に時間計測用のログ（time.perf_counter）を仕込むアプローチを提示し、実装に着手する。",
  "status": "completed",
  "duration_minutes": 5,
  "files_changed": [],
  "executed_actions": [
    "デバッグログの挿入候補箇所（depsgraph_handler, update_sdf_mesh, draw_callback_3d）と計測指標の設計"
  ],
  "uploaded_images": [],
  "notes": "このデバッグログにより、今回の最適化がどれほど効果を上げているか、あるいはまだ隠れた高負荷処理がどこにあるかを定量的に視認できるようになる。"
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
