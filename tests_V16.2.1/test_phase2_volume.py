import bpy, bmesh, sys, os, time
TREE = sys.argv[-1]; sys.path.insert(0, TREE)
import rust_gpu_sdf_addon as A; A.register()
from rust_gpu_sdf_addon import engine
from rust_gpu_sdf_addon._native import rust_gpu_sdf as R
R.init_gpu(os.path.join(os.path.expanduser("~"), "sdf_bench_cache.bin"), False)
scene = bpy.context.scene; scene.sdf_live_update = True; scene.sdf_show_result = True
def pump(n=600):
    for _ in range(n):
        if engine.sdf_mesh_timer() is None: return
        time.sleep(0.005)
def volume(out):
    bm = bmesh.new(); bm.from_mesh(out.data); v = bm.calc_volume(signed=False); bm.free(); return v
def mesh(out):
    engine._last_state_hashes.pop(out.name, None); engine.update_sdf_mesh(out); pump(); return volume(out)

colA = bpy.data.collections.new("SDF_Collection"); scene.collection.children.link(colA)
outA = bpy.data.objects.new("SDF_Result", bpy.data.meshes.new("MA")); scene.collection.objects.link(outA)
outA.sdf_props.is_output=True; outA.sdf_props.target_collection=colA; outA.sdf_props.resolution=64
a0 = bpy.data.objects.new("A0", bpy.data.meshes.new("AM0")); colA.objects.link(a0)
a0.sdf_props.is_primitive=True; a0.sdf_props.shape_type='sphere'; a0.sdf_props.radius=1.0; a0.location=(1.0,0,0)
bpy.context.view_layer.update(); engine.sync_sdf_stack(outA)
bpy.context.view_layer.objects.active = outA
bpy.ops.sdf.add_tree()
outB = bpy.context.view_layer.objects.active; outB.sdf_props.resolution=64
colB = outB.sdf_props.target_collection
b0 = bpy.data.objects.new("B0", bpy.data.meshes.new("BM0")); colB.objects.link(b0)
b0.sdf_props.is_primitive=True; b0.sdf_props.shape_type='sphere'; b0.sdf_props.radius=1.5; b0.location=(0,0,0)
bpy.context.view_layer.update(); engine.sync_sdf_stack(outB)

v_alone = mesh(outB)
bpy.context.view_layer.objects.active = outB
bpy.ops.sdf.add_tree_ref()
proxy = bpy.context.view_layer.objects.active
proxy.sdf_props.tree_ref_mode = 'SUBTRACT'; proxy.sdf_props.smoothness = 0.0
v_sub = mesh(outB)
proxy.sdf_props.tree_ref_mode = 'BLEND'; proxy.sdf_props.smoothness = 0.01
v_blend = mesh(outB)
print(f"VOLUME alone={v_alone:.4f} subtract={v_sub:.4f} blend={v_blend:.4f}", flush=True)
ok1 = v_sub < v_alone * 0.98
ok2 = v_blend > v_alone * 1.02
print(("PASS  " if ok1 else "FAIL  ") + "Subtract removes volume", flush=True)
print(("PASS  " if ok2 else "FAIL  ") + "Blend adds volume", flush=True)
print("RESULT:", "ALL PASS" if (ok1 and ok2) else "FAILED", flush=True)
