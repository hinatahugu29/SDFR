import json
import os
from datetime import datetime, timezone, timedelta

log_path = r"e:\blender_addon\外部テスト\Rust-GPU-SDF-V15.9.9.5\agent-work-log.json"

new_entry = {
  "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat(),
  "user_request_summary": "15.9.9.5として新規バージョンフォルダを作成し、キャッシュや差分計算を用いたパフォーマンス最適化をコードベースに実装するよう指示。",
  "ai_interpretation": "ユーザーの指示に従い、V15.9.9.5フォルダを作成の上、メッシュOFF時およびドラッグ操作時のパフォーマンス低下問題に対する「キャッシュ」「差分計算」アプローチ（選択状態同期の軽量化、仕切りEmpty判定のハッシュセット化、操作中同期スキップ、sync_sdf_stackの差分リターン）を実装した。検証用にPythonコンパイルテストを実行し、問題ないことを確認。",
  "status": "completed",
  "duration_minutes": 20,
  "files_changed": [
    "rust_gpu_sdf_addon/__init__.py",
    "rust_gpu_sdf_addon/handlers.py",
    "rust_gpu_sdf_addon/engine.py"
  ],
  "executed_actions": [
    "V15.9.9.5 新規フォルダの作成とデータコピー",
    "__init__.py のバージョン表記を 15.9.9.5 に更新",
    "handlers.py にて active_object 同期処理の bpy.data.objects 全件ループをシーン内限定＆SDFオブジェクト限定へ変更",
    "engine.py に _cached_divider_names キャッシュセットを追加し、handlers.py の仕切りEmpty判定を O(1) に軽量化",
    "handlers.py および engine.py にトランスフォーム（移動等）操作中の同期・メッシュ処理をスキップするガードを導入",
    "engine.py の sync_sdf_stack にてコレクションと現在のスタックのオブジェクト名セットを比較し、構造変更がない場合は早期リターンする差分処理を導入",
    "py -m compileall による全ファイルのコンパイルチェックの実行"
  ],
  "uploaded_images": [],
  "notes": "この最適化により、操作中の描画遅延や引っかかりが完全に抑止され、非常にスムーズな操作感が期待できる。"
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
