import json
import os
from datetime import datetime, timezone, timedelta

log_path = r"e:\blender_addon\外部テスト\Rust-GPU-SDF-V15.9.9.5\agent-work-log.json"

new_entry = {
  "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat(),
  "user_request_summary": "カメラ速度低下対策として、カメラ操作中の描画負荷を削減する最適化処理の実装依頼。",
  "ai_interpretation": "ユーザーはプリミティブ増加に伴うカメラ回転時のFPS低下（カクつき）を解消したいと理解。チラツキのリスクを避けるため、カメラ操作中（ステップ数64）およびトランスフォームドラッグ中（ステップ数128）にプレビュー描画のレイマーチステップ数をダイナミックに削減し、静止時に高品質に自動復帰するロジックを handlers.py に追加実装した。",
  "status": "completed",
  "duration_minutes": 10,
  "files_changed": [
    "rust_gpu_sdf_addon/handlers.py"
  ],
  "executed_actions": [
    "handlers.py に _CAMERA_MOVING_STEP_CAP=64 および _TRANSFORM_STEP_CAP=128 定数を追加",
    "handlers.py の draw_callback_3d 内で、操作状態（interacting, view_moving）をトリガーとして maxSteps の値を動的に制限する処理を実装",
    "py -m compileall によるコンパイルチェックでエラーがないことを確認"
  ],
  "uploaded_images": [],
  "notes": "前回のプロファイラーで得られた「Python側は高速だがGPU/ビューポート全体が20FPSに落ちている」というデータに対する最適な対策（GPUのピクセルシェーダー処理負荷の動的クランプ）を適用した。"
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
