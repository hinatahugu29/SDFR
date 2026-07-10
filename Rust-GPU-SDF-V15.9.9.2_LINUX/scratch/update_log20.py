import json
import os
from datetime import datetime, timezone, timedelta

log_path = r"g:\blender_addon\外部テスト\Rust-GPU-SDF-V15.9.8.1\agent-work-log.json"

new_entry = {
  "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat(),
  "user_request_summary": "修正版のテスト結果として、「出来てると思う！」との報告と、完璧に複製されたスタックのスクリーンショットの提示",
  "ai_interpretation": "前回のオブジェクト参照およびDeduplicationロジックの修正により、増殖・欠落バグが完全に解消され、ユーザーが意図した通りの完全なグループ複製（プリミティブ群＋フォルダ）が実現できたことを確認。長らく悩まされていた複製バグの完全な解決に至った。",
  "status": "completed",
  "duration_minutes": 5,
  "files_changed": [],
  "executed_actions": [
    "ユーザーからの成功報告の確認",
    "提供されたスクリーンショットにて、キューブ・シリンダー2つ・フォルダの構成が、正確にナンバリング付き（.001など）で複製されていることを視覚的に確認",
    "問題のクローズ処理"
  ],
  "uploaded_images": [
    {
      "description": "修正後のSDFスタック画面のスクリーンショット。元のグループと全く同じ構成（3つのプリミティブと1つのフォルダ）が、欠落も増殖もなく完璧に複製されている状態。",
      "context": "複製バグ修正の最終確認用エビデンス"
    }
  ],
  "notes": "Blender特有のオブジェクト参照の挙動（同一オブジェクトでも別ラッパーになる問題）に対する知見が得られた。今後の開発においても `set(objects)` ではなく名前等のユニークキーでのDeduplicationを基本とする。"
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
