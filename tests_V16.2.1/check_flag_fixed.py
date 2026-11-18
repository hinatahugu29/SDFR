import bpy, sys, os
TREE = sys.argv[-1]
sys.path.insert(0, TREE)
import rust_gpu_sdf_addon as A
assert os.path.abspath(os.path.dirname(A.__file__)).lower().startswith(os.path.abspath(TREE).lower()), f"別のアドオンを読み込んでいる: {A.__file__}"
A.register()
from rust_gpu_sdf_addon._native import rust_gpu_sdf as R
f = os.path.join(os.environ["TEMP"], "sdf_flag_test.blend")
bpy.ops.wm.open_mainfile(filepath=f)
sp = bpy.context.scene.sdf_scene_props
print(f"TREE={os.path.basename(TREE)}  開いた直後: is_gpu_ready={sp.is_gpu_ready}  実GPU={R.is_gpu_available()}  モジュール側={A._gpu_init_finished}", flush=True)
ok = (sp.is_gpu_ready == A._gpu_init_finished)
print(("PASS  " if ok else "FAIL  ") + "パネルのガードが実際のウォームアップ状況と一致", flush=True)
