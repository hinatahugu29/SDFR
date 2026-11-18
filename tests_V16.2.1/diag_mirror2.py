import bpy, bmesh, sys, os, time, math

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _tree import default_tree
TREE = default_tree()
sys.path.insert(0, TREE)
import rust_gpu_sdf_addon as A
A.register()
from rust_gpu_sdf_addon import engine
from rust_gpu_sdf_addon._native import rust_gpu_sdf as R
R.init_gpu(os.path.join(os.path.expanduser("~"), "sdf_bench_cache.bin"), False)

scene = bpy.context.scene
scene.sdf_live_update = True
scene.sdf_show_result = True
RES = 128
OFFSET = 0.4     # 半径0.6の球を ±0.4 に置く -> 確実に重なる


def pump(n=800):
    for _ in range(n):
        if engine.sdf_mesh_timer() is None:
            return
        time.sleep(0.005)


def new_tree(idx):
    col = bpy.data.collections.new(f"C{idx}")
    scene.collection.children.link(col)
    out = bpy.data.objects.new(f"OUT{idx}", bpy.data.meshes.new(f"M{idx}"))
    scene.collection.objects.link(out)
    out.sdf_props.is_output = True
    out.sdf_props.target_collection = col
    out.sdf_props.resolution = RES
    out.sdf_props.use_weld = True
    return out, col


def torus(col, name, loc=(0, 0, 0), smooth=0.3):
    o = bpy.data.objects.new(name, bpy.data.meshes.new(name + "M"))
    col.objects.link(o)
    p = o.sdf_props
    p.is_primitive = True
    p.shape_type = 'sphere'
    p.radius = 0.6
    p.smoothness = smooth
    o.location = loc
    return o


def crease_report(out, plane_axis=2, plane_at=0.0, tol=0.06):
    """折り返し面のあたりに、鋭い折れ目（隣接面の角度が大きい辺）がどれだけあるか。"""
    bm = bmesh.new()
    bm.from_mesh(out.data)
    bm.normal_update()
    near = sharp_near = 0
    worst = 0.0
    all_sharp = 0
    for e in bm.edges:
        if len(e.link_faces) != 2:
            continue
        try:
            ang = e.calc_face_angle()
        except Exception:
            continue
        if ang > math.radians(30):
            all_sharp += 1
        mid = (e.verts[0].co + e.verts[1].co) * 0.5
        if abs(mid[plane_axis] - plane_at) <= tol:
            near += 1
            if ang > math.radians(30):
                sharp_near += 1
            worst = max(worst, ang)
    bm.free()
    return near, sharp_near, math.degrees(worst), all_sharp


print("=" * 74)
print(f"折り返し面(z=0)まわりの折れ目を数える  res={RES}, mirror offset={OFFSET}")
print("=" * 74)

# --- 1) プリミティブ自身の Layout Mirror（WGSL の abs() 折り返し）
out1, col1 = new_tree(1)
t1 = torus(col1, "T_fold")
tp = t1.sdf_props
tp.layout_use_mirror = True
tp.mirror_z = True
tp.mirror_x = tp.mirror_y = False
tp.mirror_offset = OFFSET
bpy.context.view_layer.update()
engine.sync_sdf_stack(out1)
engine._last_state_hashes.pop(out1.name, None)
engine.update_sdf_mesh(out1)
pump()
n1, s1, w1, a1 = crease_report(out1)
print("   [stack1]", [it.item_type for it in out1.sdf_props.sdf_stack])
print(f"1) Layout Mirror (domain fold)      verts={len(out1.data.vertices):6d}  "
      f"面付近の辺={n1:5d}  うち30度超={s1:5d}  最大角={w1:6.1f}deg  全体の鋭い辺={a1}")

# --- 2) 同じ形を、実体2つの Smooth Union で作る
out2, col2 = new_tree(2)
torus(col2, "T_a", loc=(0, 0, OFFSET), smooth=0.3)
torus(col2, "T_b", loc=(0, 0, -OFFSET), smooth=0.3)
bpy.context.view_layer.update()
engine.sync_sdf_stack(out2)
engine._last_state_hashes.pop(out2.name, None)
engine.update_sdf_mesh(out2)
pump()
n2, s2, w2, a2 = crease_report(out2)
print(f"2) 実体2つ + Smooth Union           verts={len(out2.data.vertices):6d}  "
      f"面付近の辺={n2:5d}  うち30度超={s2:5d}  最大角={w2:6.1f}deg  全体の鋭い辺={a2}")

# --- 3) Collection Divider の Mirror（Python 側でコピーを実体化する経路）
out3, col3 = new_tree(3)
t3 = torus(col3, "T_div")
empty = bpy.data.objects.new("SDF_Group_Mirror", None)
col3.objects.link(empty)
ep = empty.sdf_props
ep.is_primitive = False
ep.layout_use_mirror = True
ep.mirror_z = True
ep.mirror_x = ep.mirror_y = False
ep.mirror_offset = OFFSET
bpy.context.view_layer.update()
engine.sync_sdf_stack(out3)
engine.sync_sdf_parents(out3)
engine._last_state_hashes.pop(out3.name, None)
engine.update_sdf_mesh(out3)
pump()
n3, s3, w3, a3 = crease_report(out3)
types3 = [it.item_type for it in out3.sdf_props.sdf_stack]
print(f"3) Collection Divider の Mirror     verts={len(out3.data.vertices):6d}  "
      f"面付近の辺={n3:5d}  うち30度超={s3:5d}  最大角={w3:6.1f}deg  全体の鋭い辺={a3}   stack={types3}")

print()
print("補足: 1 と 3 の頂点数がほぼ同じなら、両方とも同じ2つのコピーを作っている。")
print("      違いは『どう合成しているか』だけ。")
