import bpy, sys, os
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _tree import default_tree
sys.path.insert(0, default_tree())
import rust_gpu_sdf_addon as A; A.register()
sp = bpy.context.scene.sdf_scene_props
print("register直後の is_gpu_ready:", sp.is_gpu_ready, flush=True)
sp.is_gpu_ready = True          # 実際の使用では init_checker がこう立てる
out = os.path.join(os.environ["TEMP"], "sdf_flag_test.blend")
bpy.ops.wm.save_as_mainfile(filepath=out)
print("saved:", out, flush=True)
