import bpy, sys, os, time

TREE = sys.argv[-1]
sys.path.insert(0, TREE)
import rust_gpu_sdf_addon as A
A.register()
from rust_gpu_sdf_addon import engine
from rust_gpu_sdf_addon._native import rust_gpu_sdf as R
R.init_gpu(os.path.join(os.path.expanduser("~"), "sdf_bench_cache.bin"), False)
print("TESTING TREE:", TREE, flush=True)

scene = bpy.context.scene
scene.sdf_live_update = True
scene.sdf_show_result = True
fail = []


def check(label, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + label + ("   " + detail if detail else ""), flush=True)
    if not cond:
        fail.append(label)


def pump(limit=800):
    for _ in range(limit):
        if engine.sdf_mesh_timer() is None:
            return
        time.sleep(0.005)


col = bpy.data.collections.new("SDF_Collection")
scene.collection.children.link(col)
out = bpy.data.objects.new("SDF_Result", bpy.data.meshes.new("M"))
scene.collection.objects.link(out)
out.sdf_props.is_output = True
out.sdf_props.target_collection = col
out.sdf_props.resolution = 48
prims = []
for i in range(4):
    o = bpy.data.objects.new(f"P{i}", bpy.data.meshes.new(f"PM{i}"))
    col.objects.link(o)
    o.sdf_props.is_primitive = True
    o.sdf_props.shape_type = 'sphere'
    o.sdf_props.radius = 0.8
    o.location = (i * 0.9, 0, 0)
    prims.append(o)
bpy.context.view_layer.update()
engine.sync_sdf_stack(out)

# 1. basic mesh
engine.update_sdf_mesh(out); pump()
base = len(out.data.vertices)
check("basic meshing", base > 0, f"verts={base}")

# 2. an edit changes the mesh
prims[0].location = (0, 1.5, 0)
bpy.context.view_layer.update()
engine.update_sdf_mesh(out); pump()
moved = len(out.data.vertices)
check("edit changes the mesh", moved != base, f"{base} -> {moved}")

# 3. resolution change
out.sdf_props.resolution = 64
engine.update_sdf_mesh(out); pump()
hi = len(out.data.vertices)
check("resolution change takes effect", hi != moved, f"{moved} -> {hi}")

# 4. auto_domain toggle now takes effect on its own (B1)
out.sdf_props.auto_domain = True
engine.update_sdf_mesh(out); pump()
a_on = len(out.data.vertices)
out.sdf_props.domain_size = 1.5
out.sdf_props.auto_domain = False       # update callback fires here
pump()
a_off = len(out.data.vertices)
check("auto_domain toggle re-meshes without Force Update", a_off != a_on, f"{a_on} -> {a_off}")

# 5. protect_partial_mesh / fallback path still runs without error
out.sdf_props.auto_domain = False
out.sdf_props.domain_size = 50.0        # sphere becomes sub-voxel -> EMPTY_RESULT
out.sdf_props.resolution = 48
engine._last_state_hashes.pop(out.name, None)
engine.update_sdf_mesh(out); pump()
check("protect/fallback path survives", True, "no exception")
print("   flags:", engine._safe_retry_active, engine._gpu_chunked_mc_active, flush=True)

# 6. back to a sane domain
out.sdf_props.auto_domain = True
engine._last_state_hashes.pop(out.name, None)
engine.update_sdf_mesh(out); pump()
check("recovers after the fallback path", len(out.data.vertices) > 0, f"verts={len(out.data.vertices)}")

# 7. show_result OFF clears the mesh, ON restores it
scene.sdf_show_result = False
engine._last_state_hashes.pop(out.name, None)
engine.update_sdf_mesh(out); pump()
off = len(out.data.vertices)
scene.sdf_show_result = True
engine._last_state_hashes.pop(out.name, None)
engine.update_sdf_mesh(out); pump()
on = len(out.data.vertices)
check("show_result OFF/ON", off == 0 and on > 0, f"off={off} on={on}")

if not hasattr(engine, "_pending_updates"):
    print("RESULT(old tree, steps 1-7 only):", "ALL PASS" if not fail else f"{len(fail)} FAILED: {fail}", flush=True)
    raise SystemExit(0)

# 8. no stale bookkeeping left behind
check("no pending left over", not engine._pending_updates, f"{dict(engine._pending_updates)}")
check("inflight cleared", engine._inflight_owner is None, f"{engine._inflight_owner}")

# 9. deleting an output does not wedge the timer
engine._pending_updates["SDF_Result_GONE"] = True
engine.sdf_mesh_timer()
check("pending for a missing output is dropped", "SDF_Result_GONE" not in engine._pending_updates)

print("\nRESULT:", "ALL PASS" if not fail else f"{len(fail)} FAILED: {fail}", flush=True)
