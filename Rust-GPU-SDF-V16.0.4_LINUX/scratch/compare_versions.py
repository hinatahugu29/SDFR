import os
import difflib

dir3 = r"e:\blender_addon\外部テスト\Rust-GPU-SDF-V15.9.9.3"
dir4 = r"e:\blender_addon\外部テスト\Rust-GPU-SDF-V15.9.9.4"

def compare_dirs(d1, d2, subpath=""):
    path1 = os.path.join(d1, subpath)
    path2 = os.path.join(d2, subpath)
    
    for item in os.listdir(path1):
        if item in [".git", "__pycache__", "target", "bin", "scratch", "agent-work-log.json", "Cargo.lock", "SDF_R_15_9_9_4.zip", "SDF_R_15_9_9_3.zip"]:
            continue
        p1 = os.path.join(path1, item)
        p2 = os.path.join(path2, item)
        
        if os.path.isdir(p1):
            if os.path.exists(p2):
                compare_dirs(d1, d2, os.path.join(subpath, item))
        else:
            if os.path.exists(p2):
                with open(p1, "r", encoding="utf-8", errors="ignore") as f1, open(p2, "r", encoding="utf-8", errors="ignore") as f2:
                    c1 = f1.readlines()
                    c2 = f2.readlines()
                
                diff = list(difflib.unified_diff(c1, c2, fromfile=os.path.join(subpath, item) + " (V3)", tofile=os.path.join(subpath, item) + " (V4)", n=1))
                if diff:
                    print(f"--- Diff in {os.path.join(subpath, item)} ---")
                    # 表示をコンパクトにするため、変更行のみをいくつか出す
                    for line in diff[:30]:
                        print(line, end="")
                    if len(diff) > 30:
                        print(f"\n... (truncated {len(diff) - 30} lines)")
                    print("\n" + "="*50)
            else:
                print(f"File only in V3: {os.path.join(subpath, item)}")

compare_dirs(dir3, dir4)
