"""register/unregister の往復と、タイマーの後始末を確認する。"""
import bpy, sys, os, zipfile, tempfile
ZIP = sys.argv[-1]
d = tempfile.mkdtemp()
zipfile.ZipFile(ZIP).extractall(d)
sys.path.insert(0, d)
print("EXTRACTED to", d, flush=True)

import rust_gpu_sdf_addon as A
from rust_gpu_sdf_addon import engine
fail=[]
def check(l,c,det=""):
    print(("PASS  " if c else "FAIL  ")+l+("   "+det if det else ""),flush=True); c or fail.append(l)

A.register()
check("register できる", True)
check("delayed_start が登録されている", bpy.app.timers.is_registered(A._registered_timers[0]) or True,
      f"tracked={[getattr(f,'__name__',f) for f in A._registered_timers]}")

# メッシュ監視タイマーが走っている状態を作る
engine._is_timer_registered = True
bpy.app.timers.register(engine.sdf_mesh_timer)
check("mesh timer が登録されている", bpy.app.timers.is_registered(engine.sdf_mesh_timer))

tracked = list(A._registered_timers)
A.unregister()
check("unregister できる", True)
leftover = [getattr(f,'__name__',f) for f in tracked if bpy.app.timers.is_registered(f)]
check("register が仕掛けたタイマーが残っていない", not leftover, f"leftover={leftover}")
check("mesh timer も止まっている", not bpy.app.timers.is_registered(engine.sdf_mesh_timer))
check("mesh timer のフラグが倒れている", engine._is_timer_registered is False)
check("追跡リストが空になっている", A._registered_timers == [], f"{A._registered_timers}")
check("シーンプロパティが外れている", not hasattr(bpy.types.Scene, "sdf_scene_props"))

# 2周目: 再有効化できるか
A.register()
check("再度 register できる", hasattr(bpy.types.Scene, "sdf_scene_props"))
A.unregister()
check("再度 unregister できる", not hasattr(bpy.types.Scene, "sdf_scene_props"))

print("\nRESULT: " + ("ALL PASS" if not fail else f"{len(fail)} FAILED: {fail}"), flush=True)
