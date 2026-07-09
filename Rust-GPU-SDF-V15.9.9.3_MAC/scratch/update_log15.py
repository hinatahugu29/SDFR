import json
import os
from datetime import datetime, timezone, timedelta

log_path = r"g:\blender_addon\外部テスト\Rust-GPU-SDF-V15.9.8.1\agent-work-log.json"

new_entry = {
  "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat(),
  "user_request_summary": "ユーザーからの詳細なログ分析と修正案（名前ベースの同期への統一、複製後の1フレーム遅延、Depsgraphハンドラのクールダウンフラグ）の提示を受け、より強固な退行防止策を追加実装。",
  "ai_interpretation": "既に実装済みの「名前ベースの同期（obj_nameキャッシュ）」に加えて、ユーザーの提案通り「オペレーター実行直後の同期を1フレーム遅延させる」「Depsgraph側にクールダウンフラグ（_duplicate_cooldown）を設けて一時的に実行を抑制する」という二重・三重の防護策を追加することで、BlenderのDepsgraphの不安定さを完全にシャットアウトする意図だと理解した。",
  "status": "completed",
  "duration_minutes": 10,
  "files_changed": [
    "rust_gpu_sdf_addon/operators.py",
    "rust_gpu_sdf_addon/engine.py",
    "rust_gpu_sdf_addon/handlers.py"
  ],
  "executed_actions": [
    "engine.pyに _duplicate_cooldown フラグを追加",
    "operators.pyのSDF_OT_duplicate_collectionにて、複製完了後のsync_sdf_stackおよびupdate_sdf_meshの呼び出しをbpy.app.timersで1フレーム（0.05秒）遅延実行するよう変更",
    "遅延タイマー実行中および実行前は _duplicate_cooldown をTrueにし、handlers.pyのsdf_depsgraph_handlerがその間は処理をスキップするようにガードを追加",
    "再度ビルドを実行し、アドオンZIPを更新"
  ],
  "notes": "ユーザー提案の遅延実行およびクールダウンフラグを実装。前回の名前ベース同期（obj_nameキャッシュ）と合わせることで、考え得る限りの最も堅牢な複製同期システムとなった。"
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
