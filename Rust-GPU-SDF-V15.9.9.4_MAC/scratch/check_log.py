import json
import traceback

path = r"e:\blender_addon\外部テスト\Rust-GPU-SDF-V15.9.7.1\agent-work-log.json"

try:
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    print("Read with utf-8 successfully. Length:", len(data))
    
    # 行ごとにパースしてみるなどして原因を特定
    try:
        json.loads(data)
        print("JSON parsed successfully with utf-8!")
    except Exception as e:
        print("JSON parse error with utf-8:")
        traceback.print_exc()
        
        # エラー発生位置の周辺を出力
        if hasattr(e, 'pos'):
            pos = e.pos
            start = max(0, pos - 100)
            end = min(len(data), pos + 100)
            print("--- Around error position ---")
            print(data[start:pos] + ">>>" + data[pos] + "<<<" + data[pos+1:end])
except Exception as e:
    traceback.print_exc()
