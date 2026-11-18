# Mirror Blend: プレビュー(shader.py の近似) と 最終メッシュ の食い違いを数値で出す。
# プレビュー側は GLSL を回さず、shader.py と同じ式を Python で再現して等値面を測る。
#   shader.py:  e = mb*mb*0.25;  lp.z = sqrt(lp.z*lp.z + e) - offset
#   最終メッシュ: 両側を別々に評価して smooth union (common.wgsl evaluate_shape_mirrored)
import bpy, sys, os, time, math
_ARG = sys.argv[-1]
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _tree import default_tree
TREE = _ARG if os.path.isdir(_ARG) else default_tree()
sys.path.insert(0, TREE)
import rust_gpu_sdf_addon as A; A.register()
from rust_gpu_sdf_addon import engine
from rust_gpu_sdf_addon._native import rust_gpu_sdf as R
R.init_gpu(os.path.join(os.path.expanduser("~"), "sdf_bench_cache_v1621.bin"), False)
scene = bpy.context.scene; scene.sdf_live_update = False; scene.sdf_show_result = True

RES = 192; DOMAIN = 2.0; RADIUS = 0.15; OFFSET = 0.25; TINY = 0.0001
_n = [0]
def pump(n=2000):
    for _ in range(n):
        if engine.sdf_mesh_timer() is None: return
        time.sleep(0.005)
def wipe():
    for o in list(scene.objects): bpy.data.objects.remove(o, do_unlink=True)
    for c in list(bpy.data.collections): bpy.data.collections.remove(c)
def mesh_extents(blend):
    _n[0] += 1; i = _n[0]
    col = bpy.data.collections.new(f"C{i}"); scene.collection.children.link(col)
    out = bpy.data.objects.new(f"OUT{i}", bpy.data.meshes.new(f"M{i}")); scene.collection.objects.link(out)
    p = out.sdf_props
    p.is_output = True; p.target_collection = col; p.resolution = RES
    p.use_weld = True; p.auto_domain = False; p.domain_size = DOMAIN
    o = bpy.data.objects.new("m", bpy.data.meshes.new("mM")); col.objects.link(o)
    q = o.sdf_props; q.is_primitive = True; q.shape_type = 'sphere'
    q.radius = RADIUS; q.smoothness = TINY
    q.layout_use_mirror = True; q.mirror_z = True
    q.mirror_offset = OFFSET; q.mirror_blend = blend
    bpy.context.view_layer.update(); engine.sync_sdf_stack(out); engine.sync_sdf_parents(out)
    engine._last_state_hashes.pop(out.name, None); engine.update_sdf_mesh(out); pump()
    vs = out.data.vertices
    if len(vs) == 0: r = (0, 0.0, 0.0)
    else:
        r = (len(vs), max(v.co.z for v in vs)-min(v.co.z for v in vs),
                      max(v.co.x for v in vs)-min(v.co.x for v in vs))
    wipe(); return r

def preview_sdf(x, y, z, blend):
    # shader.py の Mirror ブロックそのまま（1軸 Z、fold のみ。他の演算は無し）
    e = blend * blend * 0.25
    lz = math.sqrt(z*z + e) - OFFSET if blend > 0.0001 else abs(z) - OFFSET
    return math.sqrt(x*x + y*y + lz*lz) - RADIUS
def preview_extents(blend, n=400, half=1.0):
    # y=0 の xz 平面を格子走査してバウンディングを取る（軸上走査だと z=0 に形が無く測れない）
    xs = []; zs = []
    for i in range(n+1):
        x = -half + 2.0*half*i/n
        for j in range(n+1):
            z = -half + 2.0*half*j/n
            if preview_sdf(x, 0.0, z, blend) <= 0.0:
                xs.append(x); zs.append(z)
    if not xs: return 0.0, 0.0
    return max(zs)-min(zs), max(xs)-min(xs)

print(f"res={RES} domain={DOMAIN} r={RADIUS} offset={OFFSET}", flush=True)
print(f"{'blend':>6} | {'メッシュ z幅 / x幅':>22} | {'プレビュー z幅 / x幅':>22} | 差", flush=True)
for blend in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.4, 2.0):
    mv, mz, mx = mesh_extents(blend)
    pz, px = preview_extents(blend)
    note = ""
    if mv > 0 and pz == 0.0: note = "  <-- プレビューは消滅、メッシュは存在"
    print(f"{blend:6.2f} | {mz:10.4f} {mx:10.4f}   | {pz:10.4f} {px:10.4f}   | "
          f"dz={mz-pz:+.4f} dx={mx-px:+.4f}{note}", flush=True)
