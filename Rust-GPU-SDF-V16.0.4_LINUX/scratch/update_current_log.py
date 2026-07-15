import json
import os
from datetime import datetime, timezone, timedelta

log_path = r"e:\blender_addon\外部テスト\Rust-GPU-SDF-V15.9.9.4\agent-work-log.json"

new_entry = {
  "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat(),
  "user_request_summary": "最新バージョンである V15.9.9.4 の内容と実装履歴の確認依頼を受け、フォルダ構成やソースコード、パッチファイル、各アップデートログの内容を確認した。",
  "ai_interpretation": "ユーザーは V15.9.9.4 で何が追加・修正されたのかを整理し、開発状況の全体像を把握したいと考えていると理解。これまでの機能追加（Chamfer/Shell、wgpu対策、コレクション複製機能とUX改善）の経緯を整理して報告する必要がある。",
  "status": "completed",
  "duration_minutes": 10,
  "files_changed": [],
  "executed_actions": [
    "V15.9.9.4 ディレクトリ直下のファイル一覧確認",
    "各 patch*.py および ui.py / operators.py のパッチ適用状況確認",
    "scratch 内の update_log*.py に基づく V15.9.8.1 から V15.9.9.4 にかけての開発・バグ修正履歴の調査・整理"
  ],
  "uploaded_images": [],
  "notes": "このバージョンでは、特にコレクションの一括複製バグの完全修正や、複製後の自動アクティブ化などのUXブラッシュアップが行われていることを確認した。"
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
