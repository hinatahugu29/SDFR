import bpy, sys, os, time
TREE = sys.argv[-1]
sys.path.insert(0, TREE)
import rust_gpu_sdf_addon as A
assert os.path.abspath(os.path.dirname(A.__file__)).lower().startswith(os.path.abspath(TREE).lower()), A.__file__
A.register()
from rust_gpu_sdf_addon import engine
from rust_gpu_sdf_addon._native import rust_gpu_sdf as R
R.init_gpu(os.path.join(os.path.expanduser("~"), "sdf_bench_cache_v1621.bin"), False)
scene = bpy.context.scene
scene.sdf_live_update = True
scene.sdf_show_result = True
fail = []
def check(l, c, d=""):
    print(("PASS  " if c else "FAIL  ") + l + ("   " + d if d else ""), flush=True)
    if not c: fail.append(l)
def pump(n=600):
    for _ in range(n):
        if engine.sdf_mesh_timer() is None: return
        time.sleep(0.005)
def mesh(out):
    engine._last_state_hashes.pop(out.name, None)
    engine.update_sdf_mesh(out); pump()
    return len(out.data.vertices)

def make_tree(i, r):
    col = bpy.data.collections.new(f"C{i}"); scene.collection.children.link(col)
    out = bpy.data.objects.new(f"OUT{i}", bpy.data.meshes.new(f"M{i}")); scene.collection.objects.link(out)
    out.sdf_props.is_output = True; out.sdf_props.target_collection = col; out.sdf_props.resolution = 48
    o = bpy.data.objects.new(f"P{i}", bpy.data.meshes.new(f"PM{i}")); col.objects.link(o)
    o.sdf_props.is_primitive = True; o.sdf_props.shape_type = 'sphere'; o.sdf_props.radius = r
    bpy.context.view_layer.update(); engine.sync_sdf_stack(out)
    return out, col, o

outA, colA, primA = make_tree(1, 0.6)
outB, colB, primB = make_tree(2, 0.9)
vA, vB = mesh(outA), mesh(outB)
check("前提: 2本ともメッシュ化されている", vA > 0 and vB > 0, f"{vA} / {vB}")

# ツリーA を Finalize
bpy.context.view_layer.objects.active = outA
bpy.ops.sdf.finalize()

check("Live Update が切られていない（他にツリーが残っているため）",
      scene.sdf_live_update is True, f"sdf_live_update={scene.sdf_live_update}")
outputs = [o.name for o in engine.iter_sdf_outputs(scene)]
check("残ったツリーは1本だけ出力として残る", outputs == [outB.name], f"{outputs}")

# 残ったツリーが編集に追従するか
primB.location = (0.7, 0, 0)
bpy.context.view_layer.update()
vB2 = mesh(outB)
check("残ったツリーは引き続き編集できる", vB2 > 0 and vB2 != vB, f"{vB} -> {vB2}")

# パネルの解決先が生きているか
resolved = engine.resolve_active_output(bpy.context)
check("パネルは残ったツリーを指す", resolved == outB, f"{getattr(resolved,'name',None)}")
sp = scene.sdf_scene_props
check("確定済みを指した active_output が残っていない",
      sp.active_output is None or sp.active_output.sdf_props.is_output,
      f"{getattr(sp.active_output,'name',None)}")

# 最後の1本を Finalize したら Live Update は切れる（従来の挙動）
bpy.context.view_layer.objects.active = outB
bpy.ops.sdf.finalize()
check("最後の1本を確定すると Live Update が切れる（従来どおり）",
      scene.sdf_live_update is False, f"sdf_live_update={scene.sdf_live_update}")
check("出力はもう無い", list(engine.iter_sdf_outputs(scene)) == [])

print("\nRESULT:", "ALL PASS" if not fail else f"{len(fail)} FAILED: {fail}", flush=True)
