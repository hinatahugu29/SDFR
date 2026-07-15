import json
import os
from datetime import datetime, timezone, timedelta

log_path = r"e:\blender_addon\外部テスト\Rust-GPU-SDF-V15.9.9.5\agent-work-log.json"

new_entry = {
  "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat(),
  "user_request_summary": "後からパフォーマンスや品質（ステップ数定数）をユーザー自身が調整できるようにするための指示書の作成と保存依頼。",
  "ai_interpretation": "ユーザーは操作の軽快さとアーティファクト（黒い縁）の品質調整を後から行えるよう、handlers.py内の各パラメータの説明をまとめたドキュメントの保存を求めていると理解。PERFORMANCE_TUNING_GUIDE.mdを作成し、バージョンフォルダ直下に配置した。",
  "status": "completed",
  "duration_minutes": 5,
  "files_changed": [
    "PERFORMANCE_TUNING_GUIDE.md"
  ],
  "executed_actions": [
    "PERFORMANCE_TUNING_GUIDE.md の内容執筆と artifacts フォルダへの保存",
    "PowerShell の Copy-Item を用いた V15.9.9.5 フォルダ直下へのコピー配置"
  ],
  "uploaded_images": [],
  "notes": "handlers.py の 32行目付近の定数を書き換えるだけで簡単にパラメータを再調整できる手順を網羅した。"
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
