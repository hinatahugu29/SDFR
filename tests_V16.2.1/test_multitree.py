import bpy, sys, os, time

TREE = sys.argv[-1]
sys.path.insert(0, TREE)
import rust_gpu_sdf_addon as A
A.register()
from rust_gpu_sdf_addon import engine, handlers
from rust_gpu_sdf_addon._native import rust_gpu_sdf as R
R.init_gpu(os.path.join(os.path.expanduser("~"), "sdf_bench_cache.bin"), False)
print("TESTING TREE:", TREE, flush=True)

scene = bpy.context.scene
scene.sdf_live_update = True
scene.sdf_show_result = True


def make_tree(idx, n_prims, radius=0.8, step=1.0, origin=(0, 0, 0)):
    col = bpy.data.collections.new(f"SDF_Collection_{idx:03}")
    scene.collection.children.link(col)
    out = bpy.data.objects.new(f"SDF_Result_{idx:03}", bpy.data.meshes.new(f"M{idx}"))
    scene.collection.objects.link(out)
    out.sdf_props.is_output = True
    out.sdf_props.target_collection = col
    out.sdf_props.resolution = 48
    out.location = origin
    prims = []
    for i in range(n_prims):
        o = bpy.data.objects.new(f"P_{idx}_{i}", bpy.data.meshes.new(f"PM_{idx}_{i}"))
        col.objects.link(o)
        o.sdf_props.is_primitive = True
        o.sdf_props.shape_type = 'sphere'
        o.sdf_props.radius = radius
        o.location = (origin[0] + i * step, origin[1], origin[2])
        prims.append(o)
    bpy.context.view_layer.update()
    engine.sync_sdf_stack(out)
    return out, col, prims


def pump(limit=600):
    for _ in range(limit):
        if engine.sdf_mesh_timer() is None:
            return
        time.sleep(0.005)


fail = []


def check(label, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + label + ("   " + detail if detail else ""), flush=True)
    if not cond:
        fail.append(label)


# --- two trees with deliberately different shapes -------------------------
t0, c0, p0 = make_tree(0, 5, radius=0.8, step=1.0)
t1, c1, p1 = make_tree(1, 1, radius=0.4, origin=(30, 0, 0))

for o in (t0, t1):
    engine._last_state_hashes.pop(o.name, None)
    engine.update_sdf_mesh(o)
    pump()
v0, v1 = len(t0.data.vertices), len(t1.data.vertices)
print(f"  tree0 verts={v0}  tree1 verts={v1}", flush=True)
check("B2: two trees produce different meshes", v0 != v1 and v0 > 0 and v1 > 0, f"{v0} vs {v1}")

# --- both trees requested back to back (2nd one must not be lost) --------
p0[0].location = (0, 0.5, 0)
p1[0].location = (30, 0.5, 0)
bpy.context.view_layer.update()
d = bpy.context.evaluated_depsgraph_get()
engine.update_sdf_mesh(t0, depsgraph=d)
engine.update_sdf_mesh(t1, depsgraph=d)
queued = t1.name in engine._pending_updates or engine._inflight_owner == t1.name
print(f"  pending={dict(engine._pending_updates)} inflight={engine._inflight_owner}", flush=True)
pump()
h1 = engine.get_sdf_state_fingerprint(t1, bpy.context.evaluated_depsgraph_get())
check("B3/B5: 2nd tree's update is queued and eventually applied",
      queued and engine._last_state_hashes.get(t1.name) == h1,
      f"queued={queued} hash_match={engine._last_state_hashes.get(t1.name) == h1}")

# --- auto_domain toggle must change the fingerprint ----------------------
d = bpy.context.evaluated_depsgraph_get()
t0.sdf_props.auto_domain = True
ha = engine.get_sdf_state_fingerprint(t0, d)
t0.sdf_props.auto_domain = False
hb = engine.get_sdf_state_fingerprint(t0, d)
check("B1: auto_domain is part of the state fingerprint", ha != hb)
t0.sdf_props.use_live_normals = True
hc = engine.get_sdf_state_fingerprint(t0, d)
check("B1: use_live_normals is part of the state fingerprint", hb != hc)

# --- divider cache must cover every tree ---------------------------------
e0 = bpy.data.objects.new("SDF_Group_T0", None)
c0.objects.link(e0)
e1 = bpy.data.objects.new("SDF_Group_T1", None)
c1.objects.link(e1)
bpy.context.view_layer.update()
engine.sync_sdf_stack(t0)
engine.sync_sdf_stack(t1)
check("B4: dividers of both trees are recognised",
      engine.is_cached_divider("SDF_Group_T0") and engine.is_cached_divider("SDF_Group_T1"),
      f"t0={engine.is_cached_divider('SDF_Group_T0')} t1={engine.is_cached_divider('SDF_Group_T1')}")

# --- single tree regression ---------------------------------------------
t1.sdf_props.is_output = False
engine._last_state_hashes.pop(t0.name, None)
p0[1].location = (1.0, 0, 0.6)
bpy.context.view_layer.update()
engine.update_sdf_mesh(t0)
pump()
check("single-tree still meshes", len(t0.data.vertices) > 0, f"verts={len(t0.data.vertices)}")

print("\nRESULT:", "ALL PASS" if not fail else f"{len(fail)} FAILED: {fail}", flush=True)
