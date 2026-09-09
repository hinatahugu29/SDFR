"""書けない場所にフラグファイルを作ろうとしても、トグルが例外にならないこと。"""
import bpy, sys, os
TREE = sys.argv[-1]
sys.path.insert(0, TREE)
import rust_gpu_sdf_addon as A
A.register()
from rust_gpu_sdf_addon import properties
fail=[]
def check(l,c,d=""):
    print(("PASS  " if c else "FAIL  ")+l+("   "+d if d else ""),flush=True); c or fail.append(l)

# 書けないパスを指すよう差し替える（存在しないドライブ配下）
orig = properties._diagnostic_flag_path
properties._diagnostic_flag_path = lambda fn: os.path.join("Q:\no_such_dir_for_sdf_r", fn)

try:
    bpy.context.scene.sdf_scene_props.diagnostics_perf_log = True
    check("書けない場所でもトグルが例外にならない", True)
except Exception as e:
    check("書けない場所でもトグルが例外にならない", False, f"{type(e).__name__}: {e}")

check("戻り値で失敗を伝える",
      properties._set_diagnostic_flag_file("SDF_PERF_LOG.ON", True) is False)

properties._diagnostic_flag_path = orig
try:
    bpy.context.scene.sdf_scene_props.diagnostics_perf_log = False
    check("通常の場所では従来どおり動く", True)
except Exception as e:
    check("通常の場所では従来どおり動く", False, f"{type(e).__name__}: {e}")

print("\nRESULT: " + ("ALL PASS" if not fail else f"{len(fail)} FAILED: {fail}"), flush=True)
