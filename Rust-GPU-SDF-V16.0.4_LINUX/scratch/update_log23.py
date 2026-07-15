import json
import os
from datetime import datetime, timezone, timedelta

log_path = r"g:\blender_addon\外部テスト\Rust-GPU-SDF-V15.9.8.1\agent-work-log.json"

new_entry = {
  "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat(),
  "user_request_summary": "自動アクティブ化機能についての動作確認完了。「OK、良さそうです」との報告。",
  "ai_interpretation": "先ほど実装した「複製直後のフォルダ自動アクティブ化＆即時ペアレンティング」のUX改善が問題なく動作し、ユーザーの意図通りのワークフロー（複製→即Gキー移動）が実現できたことを確認。",
  "status": "completed",
  "duration_minutes": 5,
  "files_changed": [],
  "executed_actions": [
    "動作確認完了の記録"
  ],
  "notes": "細かいUXの改善だが、使用頻度の高い複製機能において大きな操作感の向上に繋がった。"
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
