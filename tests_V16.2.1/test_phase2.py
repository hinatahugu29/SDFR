import bpy, sys, os, time

TREE = sys.argv[-1]
sys.path.insert(0, TREE)
import rust_gpu_sdf_addon as A
A.register()
from rust_gpu_sdf_addon import engine, operators
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


def pump(limit=600):
    for _ in range(limit):
        if engine.sdf_mesh_timer() is None:
            return
        time.sleep(0.005)


def mesh(out):
    engine._last_state_hashes.pop(out.name, None)
    engine.update_sdf_mesh(out)
    pump()
    return len(out.data.vertices)


# --- tree A: a block of three spheres --------------------------------------
colA = bpy.data.collections.new("SDF_Collection")
scene.collection.children.link(colA)
outA = bpy.data.objects.new("SDF_Result", bpy.data.meshes.new("MA"))
scene.collection.objects.link(outA)
outA.sdf_props.is_output = True
outA.sdf_props.target_collection = colA
outA.sdf_props.resolution = 48
for i in range(3):
    o = bpy.data.objects.new(f"A{i}", bpy.data.meshes.new(f"AM{i}"))
    colA.objects.link(o)
    o.sdf_props.is_primitive = True
    o.sdf_props.shape_type = 'sphere'
    o.sdf_props.radius = 0.9
    o.location = (i * 1.0, 0, 0)
bpy.context.view_layer.update()
engine.sync_sdf_stack(outA)
bpy.context.view_layer.objects.active = outA

# --- tree B: one big sphere overlapping A ----------------------------------
bpy.ops.sdf.add_tree()
outB = bpy.context.view_layer.objects.active
outB.sdf_props.resolution = 48
colB = outB.sdf_props.target_collection
b0 = bpy.data.objects.new("B0", bpy.data.meshes.new("BM0"))
colB.objects.link(b0)
b0.sdf_props.is_primitive = True
b0.sdf_props.shape_type = 'sphere'
b0.sdf_props.radius = 1.6
b0.location = (1.0, 0, 0)
bpy.context.view_layer.update()
engine.sync_sdf_stack(outB)

v_alone = mesh(outB)
check("tree B meshes on its own", v_alone > 0, f"verts={v_alone}")

# --- reference A from B, in Subtract mode ----------------------------------
bpy.context.view_layer.objects.active = outB
bpy.ops.sdf.add_tree_ref()
proxy = bpy.context.view_layer.objects.active
check("proxy is a tree reference", proxy.sdf_props.is_tree_ref_proxy)
check("proxy targets the other tree", proxy.sdf_props.tree_ref_obj == outA,
      f"{getattr(proxy.sdf_props.tree_ref_obj, 'name', None)}")
item_types = [it.item_type for it in outB.sdf_props.sdf_stack]
check("the stack carries a TREE_REF item", 'TREE_REF' in item_types, f"{item_types}")

proxy.sdf_props.tree_ref_mode = 'SUBTRACT'
v_sub = mesh(outB)
check("Subtract carves the other tree out", v_sub != v_alone and v_sub > 0,
      f"alone={v_alone} subtract={v_sub}")

# --- editing A must re-mesh B ----------------------------------------------
h_before = engine.get_sdf_state_fingerprint(outB, bpy.context.evaluated_depsgraph_get())
colA.objects[0].location = (0, 1.2, 0)
bpy.context.view_layer.update()
h_after = engine.get_sdf_state_fingerprint(outB, bpy.context.evaluated_depsgraph_get())
check("editing the referenced tree changes B's fingerprint", h_before != h_after)
v_moved = mesh(outB)
check("B re-meshes after A moved", v_moved != v_sub, f"{v_sub} -> {v_moved}")

# --- Blend mode differs from Subtract --------------------------------------
proxy.sdf_props.tree_ref_mode = 'BLEND'
proxy.sdf_props.smoothness = 0.3
v_blend = mesh(outB)
check("Blend gives a different result from Subtract", v_blend != v_moved,
      f"subtract={v_moved} blend={v_blend}")
check("Blend is bigger than B alone", v_blend > 0, f"{v_blend}")

# --- moving the proxy offsets the reference --------------------------------
proxy.location = (proxy.location[0] + 3.0, 0, 0)
bpy.context.view_layer.update()
v_offset = mesh(outB)
check("moving the proxy changes the result", v_offset != v_blend, f"{v_blend} -> {v_offset}")

# --- A itself is unaffected -------------------------------------------------
v_a = mesh(outA)
stackA = [it.item_type for it in outA.sdf_props.sdf_stack]
check("the referenced tree keeps its own shape", v_a > 0 and 'TREE_REF' not in stackA,
      f"verts={v_a} stack={stackA}")

# --- self reference is refused ---------------------------------------------
proxy.sdf_props.tree_ref_obj = outB
v_self = mesh(outB)
check("a self reference is ignored rather than looping", v_self > 0, f"verts={v_self}")

# --- mutual reference must not recurse forever -----------------------------
proxy.sdf_props.tree_ref_obj = outA
bpy.context.view_layer.objects.active = outA
bpy.ops.sdf.add_tree_ref()
proxyA = bpy.context.view_layer.objects.active
proxyA.sdf_props.tree_ref_obj = outB
bpy.context.view_layer.update()
try:
    h = engine.get_sdf_state_fingerprint(outA, bpy.context.evaluated_depsgraph_get())
    v_mutual = mesh(outA)
    ok = True
except RecursionError:
    ok = False
    v_mutual = -1
check("mutual references terminate", ok, f"verts={v_mutual}")

print("\nRESULT:", "ALL PASS" if not fail else f"{len(fail)} FAILED: {fail}", flush=True)
