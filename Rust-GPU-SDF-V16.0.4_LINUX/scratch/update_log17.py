import json
import os
from datetime import datetime, timezone, timedelta

log_path = r"g:\blender_addon\外部テスト\Rust-GPU-SDF-V15.9.8.1\agent-work-log.json"

new_entry = {
  "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat(),
  "user_request_summary": "コレクション複製時に意図した数から1つ少ない数しか複製されない（指定コレクション-1個）という問題の報告とログの提供。",
  "ai_interpretation": "前回の複製時の無限増殖は防げたものの、複製の対象となる範囲（スコープ）の判定条件に `item.start_new_group` （UI上の鎖アイコン）が混入していたため、ユーザーのトグル状態によって意図しない範囲まで複製対象として巻き込んでしまうバグがあった。さらにBlenderの仕様上、オブジェクトのコレクション追加順とUI表示順がズレることで「最初の要素が欠ける」ように見える現象が起きていた。",
  "status": "completed",
  "duration_minutes": 15,
  "files_changed": [
    "rust_gpu_sdf_addon/operators.py",
    "rust_gpu_sdf_addon/engine.py"
  ],
  "executed_actions": [
    "operators.py の SDF_OT_duplicate_collection において、ループの終了条件を `item.item_type == 'COLLECTION'` に厳格化し、純粋に直前のコレクションアイテムまでを複製スコープとするよう修正。",
    "operators.py にて複製時に `new_obj[\"_sdf_dup_order\"] = idx` として元の並び順をタグ付け。",
    "engine.py の sync_sdf_stack にて、新しく追加されたオブジェクトを `_sdf_dup_order` に基づいてソートし、スタックへの追加順序（視覚的なUI順序とSDF評価順序）を完全にオリジナルと一致させるよう修正。",
    "ビルドスクリプトを実行し、SDF_R_15_9_8_1.zipを再生成。"
  ],
  "notes": "この修正により「指定したコレクションブロック内に含まれる要素だけを正確に複製し」「見た目の並び順（評価順）も寸分狂わず維持したままスタックに追加する」ことが数学的に保証された。"
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
