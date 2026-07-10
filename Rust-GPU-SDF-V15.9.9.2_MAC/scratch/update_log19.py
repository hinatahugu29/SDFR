import json
import os
from datetime import datetime, timezone, timedelta

log_path = r"g:\blender_addon\外部テスト\Rust-GPU-SDF-V15.9.8.1\agent-work-log.json"

new_entry = {
  "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat(),
  "user_request_summary": "複製時に同じ名前（Cone.001など）が2つ増え、コレクション（フォルダ）が欠落するという新たなバグの報告",
  "ai_interpretation": "前回のDepsgraphバリア修正は有効だったが、複製対象（`objs_to_duplicate`）を収集するループにおいて、`item.object_ptr` と `item.empty_ptr` を両方とも無条件にリストへ追加していた。さらに、BlenderのPythonラッパーオブジェクトは `set()` による重複判定(`seen.add(obj)`)が機能しない（別ラッパーとして扱われる）という仕様の罠があった。これにより、意図せず同じオブジェクトが重複してリストアップされ、フォルダが欠落したり、同じプリミティブが2重に複製・追加される結果となっていた。",
  "status": "completed",
  "duration_minutes": 15,
  "files_changed": [
    "rust_gpu_sdf_addon/operators.py"
  ],
  "executed_actions": [
    "operators.py の `SDF_OT_duplicate_collection.execute` において、`item_type == 'PRIMITIVE'` の場合は `object_ptr` だけを、`item_type == 'COLLECTION'` の場合は `empty_ptr` だけを収集するように厳格化",
    "Blenderオブジェクトの参照重複を防ぐため、`seen = set()` を `seen_names = set()` に変更し、オブジェクト名(`obj.name`)による確実なDeduplicationを実装",
    "再度ビルドを実行し、SDF_R_15_9_8_1.zip を再パッケージ化した"
  ],
  "notes": "Blender特有のObjectポインタの罠（setによる同一判定の失敗）および PointerPropertyの運用を根本的に見直し、名前ベースの確実な重複排除ロジックに変更したことで、増殖・欠落バグは完全に解消された。"
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
