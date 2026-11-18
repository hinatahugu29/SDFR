import bpy, sys, os, time

TREE = sys.argv[-1]
sys.path.insert(0, TREE)
import rust_gpu_sdf_addon as A
A.register()
from rust_gpu_sdf_addon import engine, operators, handlers
from rust_gpu_sdf_addon._native import rust_gpu_sdf as R
R.init_gpu(os.path.join(os.path.expanduser("~"), "sdf_bench_cache.bin"), False)
print("TESTING TREE:", TREE, flush=True)

scene = bpy.context.scene
fail = []


def check(label, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + label + ("   " + detail if detail else ""), flush=True)
    if not cond:
        fail.append(label)


def pump(limit=400):
    for _ in range(limit):
        if engine.sdf_mesh_timer() is None:
            return
        time.sleep(0.005)


# --- a legacy scene: SDF_Collection + SDF_Result made the old way ----------
legacy_col = bpy.data.collections.new("SDF_Collection")
scene.collection.children.link(legacy_col)
legacy_out = bpy.data.objects.new("SDF_Result", bpy.data.meshes.new("LegacyMesh"))
scene.collection.objects.link(legacy_out)
legacy_out.sdf_props.is_output = True
legacy_out.sdf_props.target_collection = legacy_col
legacy_out.sdf_props.resolution = 48
bpy.context.view_layer.objects.active = legacy_out

check("legacy scene resolves as the active tree",
      engine.resolve_active_output(bpy.context) == legacy_out)

bpy.ops.sdf.add_primitive(shape='sphere')
p_legacy = bpy.context.active_object
check("add_primitive lands in the legacy collection",
      p_legacy.name in legacy_col.objects, f"{[c.name for c in p_legacy.users_collection]}")

# --- add a second tree -----------------------------------------------------
bpy.ops.sdf.add_tree()
tree2 = bpy.context.view_layer.objects.active
col2 = tree2.sdf_props.target_collection
check("second tree gets its own collection",
      col2 is not None and col2 != legacy_col, f"{col2.name if col2 else None}")
check("legacy names are preserved, the new tree is numbered",
      legacy_col.name == "SDF_Collection" and col2.name.startswith("SDF_Collection_"),
      f"{legacy_col.name} / {col2.name if col2 else None}")

bpy.ops.sdf.add_primitive(shape='box')
p2 = bpy.context.active_object
check("add_primitive follows the active tree",
      p2.name in col2.objects and p2.name not in legacy_col.objects,
      f"{[c.name for c in p2.users_collection]}")

# --- selecting a part of a tree makes that tree the target -----------------
bpy.context.view_layer.objects.active = p_legacy
check("selecting a part resolves to its own tree",
      engine.resolve_active_output(bpy.context) == legacy_out,
      f"{getattr(engine.resolve_active_output(bpy.context), 'name', None)}")
bpy.context.view_layer.objects.active = p2
check("selecting the other tree's part switches the target",
      engine.resolve_active_output(bpy.context) == tree2,
      f"{getattr(engine.resolve_active_output(bpy.context), 'name', None)}")

# --- stack operators act on the resolved tree -----------------------------
bpy.context.view_layer.objects.active = p_legacy
before = len(legacy_out.sdf_props.sdf_stack)
bpy.ops.sdf.add_collection_divider()
after = len(legacy_out.sdf_props.sdf_stack)
check("add_collection_divider targets the resolved tree",
      after > before and len(tree2.sdf_props.sdf_stack) == 1,
      f"legacy {before}->{after}, tree2 stack={len(tree2.sdf_props.sdf_stack)}")

# --- both trees mesh independently ----------------------------------------
for o in (legacy_out, tree2):
    engine._last_state_hashes.pop(o.name, None)
    engine.update_sdf_mesh(o)
    pump()
check("both trees produce a mesh",
      len(legacy_out.data.vertices) > 0 and len(tree2.data.vertices) > 0,
      f"{len(legacy_out.data.vertices)} / {len(tree2.data.vertices)}")

# --- dividers of both trees are seen by the handler -----------------------
names = set()
for s in engine._cached_divider_names_by_output.values():
    names |= s
check("divider cache is per tree", len(engine._cached_divider_names_by_output) >= 1, f"{names}")

# --- show_primitives sweeps every tree ------------------------------------
scene.sdf_show_primitives = False
modes = {o.display_type for col in engine.iter_sdf_collections(scene) for o in col.objects}
check("show_primitives applies to every tree", modes <= {'BOUNDS'}, f"{modes}")
scene.sdf_show_primitives = True

# --- All Clear empties every tree collection ------------------------------
cols = [c.name for c in engine.iter_sdf_collections(scene)]
bpy.ops.sdf.all_clear()
left = [n for n in cols if bpy.data.collections.get(n) and len(bpy.data.collections[n].objects) > 0]
check("All Clear empties every tree collection", not left, f"left={left}")

print("\nRESULT:", "ALL PASS" if not fail else f"{len(fail)} FAILED: {fail}", flush=True)
