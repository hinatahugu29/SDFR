import json
import os
from datetime import datetime, timezone, timedelta

log_path = r"e:\blender_addon\外部テスト\Rust-GPU-SDF-V15.9.9.4\agent-work-log.json"

new_entry = {
  "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat(),
  "user_request_summary": "キャッシュ構築や差分計算を用いた、さらなる軽量化・高速化アプローチについての考察依頼。",
  "ai_interpretation": "ユーザーは「キャッシュ構築」や「差分更新」というアイデアが本システムにおいて効果的であるかを検証したいと理解。CPU（Python/Blender APIアクセス）とGPU（テクスチャバッファ更新）の双方における差分更新・キャッシュ戦略の有用性と具体案を整理し、論理的に回答する。",
  "status": "completed",
  "duration_minutes": 10,
  "files_changed": [],
  "executed_actions": [
    "Blender depsgraph.updates を使った差分オブジェクト検出ロジックの検討",
    "GPUへの配列転送におけるサブテクスチャ更新（部分更新）アプローチの検討",
    "オブジェクトプロパティのメモリキャッシュによる Blender API 呼び出し抑制効果の考察"
  ],
  "uploaded_images": [],
  "notes": "ユーザー提案の「キャッシュ構築・差分計算」は極めて有効な改善アプローチであり、今後の設計基盤となり得ることを確認した。"
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
