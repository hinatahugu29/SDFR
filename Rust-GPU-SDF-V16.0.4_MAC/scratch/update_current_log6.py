import json
import os
from datetime import datetime, timezone, timedelta

log_path = r"e:\blender_addon\外部テスト\Rust-GPU-SDF-V15.9.9.4\agent-work-log.json"

new_entry = {
  "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat(),
  "user_request_summary": "コードベース（__init__.py, handlers.py, engine.py）を詳細に精査したうえでの、メッシュOFF時も含むパフォーマンス改善策の整理・提案。",
  "ai_interpretation": "ユーザーはコードの具体的な構成を確認したうえで、どのようなボトルネックが存在し、それをどう解決すべきか（キャッシュ・差分更新の具体的な実装アプローチ）を整理したレポートを求めていると理解。詳細なコード分析結果を踏まえ、技術的に実行可能な5つの改善案を提示する。",
  "status": "completed",
  "duration_minutes": 15,
  "files_changed": [],
  "executed_actions": [
    "__init__.py における depsgraph_update_post 登録状況の精査",
    "handlers.py の sdf_depsgraph_handler 内の bpy.data.objects ループおよび relevance チェックの多重ループの特定",
    "engine.py の sync_sdf_stack/sync_sdf_parents の毎フレーム実行と API アクセス負荷の特定",
    "キャッシュ・差分検知を活用した最適化設計（トランスフォーム中抑止、ID差分同期、部分テクスチャ更新）のロードマップ整理"
  ],
  "uploaded_images": [],
  "notes": "コード発行は行わず、ボトルネックの正確な位置（行数含む）と、それを解決するための具体的設計仕様を整理して提示した。"
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
