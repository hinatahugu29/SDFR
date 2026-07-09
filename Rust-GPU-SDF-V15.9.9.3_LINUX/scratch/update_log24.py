import json
import os
from datetime import datetime, timezone, timedelta

log_path = r"g:\blender_addon\外部テスト\Rust-GPU-SDF-V15.9.8.1\agent-work-log.json"

new_entry = {
  "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat(),
  "user_request_summary": "「コレクションのシンプルなルール化、複製作成は結構ユニークじゃないかな？」というUI/UX設計に対する所感の共有。",
  "ai_interpretation": "今回のアップデートで完成した「スタック上のEmptyをフォルダとして扱い、それに挟まれた領域を動的なコレクションとしてグループ複製する」というアプローチが、他のSDFツールやBlender標準の仕様と比較しても非常にユニークで強力なアプローチであるという手応えをユーザーが感じている。この設計思想が本アドオンの強力な個性（USP）になり得るという認識を共有した。",
  "status": "completed",
  "duration_minutes": 5,
  "files_changed": [],
  "executed_actions": [
    "ユーザーの所感に対する同意と、機能の特長に関する言語化（対話によるディスカッション）"
  ],
  "notes": "この「シンプルなコレクション化と動的複製」は本アドオンのコアバリューの1つとなった。今後の新機能（例えばグループごと別のSDFノードに渡すなど）の拡張の基盤としても非常に重要である。"
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
