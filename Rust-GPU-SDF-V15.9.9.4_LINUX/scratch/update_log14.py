import json
import os
from datetime import datetime, timezone, timedelta

log_path = r"g:\blender_addon\外部テスト\Rust-GPU-SDF-V15.9.8.1\agent-work-log.json"

new_entry = {
  "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat(),
  "user_request_summary": "コレクション一括複製時にオブジェクトが意図せず余分に増殖してしまうバグ（依然として修正されていなかった）の完全な修正と、今回修正した内容のリリースノート作成（和文・英文）。",
  "ai_interpretation": "前回の修正（engine._in_updateフラグ）では、オペレーター実行直後にBlenderのDepsgraphが評価された際、新しく追加したオブジェクトのPointerPropertyが一瞬無効になる（Noneを返す）Blenderの仕様に対応しきれていなかったと理解。これに対処するため、一時的にポインタが外れても名前で追跡できる堅牢な仕組みを導入する必要がある。",
  "status": "completed",
  "duration_minutes": 30,
  "files_changed": [
    "rust_gpu_sdf_addon/properties.py",
    "rust_gpu_sdf_addon/engine.py"
  ],
  "executed_actions": [
    "SDF_StackItemにobj_name（StringProperty）を追加し、オブジェクト名をキャッシュする仕組みを実装",
    "engine.pyのsync_sdf_stackにて、PointerPropertyが一時的にNoneになってもobj_nameでコレクション内の存在を確認し、重複追加や意図しない削除を防ぐようロジックを刷新",
    "修正後にスクリプトのビルドを実行し、SDF_R_15_9_8_1.zip を再生成",
    "修正版（V15.9.8.2相当）のリリースノートを作成"
  ],
  "notes": "BlenderのPointerPropertyの不安定さ（Depsgraph評価中に一時的にNoneを返す挙動）に対する非常に堅牢な回避策を実装した。これにより、SDFのスタックリストの同期が確実に行われるようになった。"
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
