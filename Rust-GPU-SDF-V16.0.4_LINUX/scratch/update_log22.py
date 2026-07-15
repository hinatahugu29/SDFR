import json
import os
from datetime import datetime, timezone, timedelta

log_path = r"g:\blender_addon\外部テスト\Rust-GPU-SDF-V15.9.8.1\agent-work-log.json"

new_entry = {
  "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat(),
  "user_request_summary": "コレクションを複製したとき、複製された新しいコレクション（フォルダ）を動的にアクティブにする（選択状態にする）機能の追加要望",
  "ai_interpretation": "「複製する＝すぐに移動（Gキー）させる意図がある」というユーザーの視点は非常に合理的。複製直後に新しいフォルダEmptyをアクティブにすることで、ユーザーの手間（改めてフォルダを選択し直すこと）を省き、シームレスなUXを提供する。",
  "status": "completed",
  "duration_minutes": 5,
  "files_changed": [
    "rust_gpu_sdf_addon/operators.py"
  ],
  "executed_actions": [
    "operators.py の SDF_OT_duplicate_collection.execute において、複製された全てのオブジェクトを選択状態（select_set(True)）にする処理を追加",
    "複製されたアイテムのうち、EMPTY（フォルダ）オブジェクトを見つけた場合、それを context.view_layer.objects.active に設定する処理を追加",
    "複製後1フレーム遅延する delayed_sync 内で engine.sync_sdf_parents(out_obj) を呼び出し、Gキーで移動した際に内部のプリミティブが確実についてくるよう親子関係の即時再構築を追加",
    "アドオンの再ビルドとパッケージ化"
  ],
  "notes": "ユーザーのモデリングフロー（複製→即移動）に直結する素晴らしいUX改善。Blenderのオブジェクトアクティブ化とペアレンティングのタイミングを考慮して実装した。"
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
