import json
import os
from datetime import datetime, timezone, timedelta

log_path = r"e:\blender_addon\外部テスト\Rust-GPU-SDF-V15.9.9.5\agent-work-log.json"

new_entry = {
  "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat(),
  "user_request_summary": "実行頻度と処理時間を計測するデバッグログ（プロファイラー）の追加実装依頼。",
  "ai_interpretation": "ユーザーはアドオン内部の各ハンドラーが実際にどれほどの頻度と処理時間で動作しているかを定量的に計測・視認したいと理解。handlers.py と engine.py に time.perf_counter を用いたロギング処理を追加した。コンソールの可読性を保つため、高頻度なイベントは1秒ごとに集計して出力するラッパー構造を設計・適用した。",
  "status": "completed",
  "duration_minutes": 10,
  "files_changed": [
    "rust_gpu_sdf_addon/handlers.py",
    "rust_gpu_sdf_addon/engine.py"
  ],
  "executed_actions": [
    "engine.py の sync_sdf_stack に処理時間計測ログを追加",
    "handlers.py に depsgraph更新ハンドラーおよびプレビュー描画（draw_callback_3d）の呼び出し頻度・平均処理時間を1秒ごとに集計表示するプロファイララッパーを追加",
    "py -m compileall によるコンパイルチェックでエラーがないことを確認"
  ],
  "uploaded_images": [],
  "notes": "高頻度で呼ばれるハンドラーの print 負荷を避けるため、1秒集計ラッパー構造にした点が技術的ポイント。"
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
