# プレビュー近似の候補を、最終メッシュと突き合わせて評価する。
#  現行 : lp.z = sqrt(z*z + mb*mb*0.25) - offset          （縮む / 消える）
#  候補 : lp.z = abs(z) - offset;  d -= k*h*(1-h),
#         h = clamp(0.5 + |z|/k, 0, 1)                     （継ぎ目だけ膨らむ）
# 候補の狙い: polynomial smin の補正項 k*h*(1-h) を、
#   「反対側コピーとの距離差 ≈ 2|z|」という近似で1回評価のまま再現する。
#   z=0 で k/4（厳密解と一致）、|z| >= k/2 で 0（継ぎ目から離れると素の形）。
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
    r = (0.0, 0.0) if len(vs) == 0 else (max(v.co.z for v in vs)-min(v.co.z for v in vs),
                                         max(v.co.x for v in vs)-min(v.co.x for v in vs))
    wipe(); return r
def sdf_now(x, y, z, mb):
    e = mb*mb*0.25
    lz = math.sqrt(z*z + e) - OFFSET if mb > 0.0001 else abs(z) - OFFSET
    return math.sqrt(x*x + y*y + lz*lz) - RADIUS
def sdf_new(x, y, z, mb):
    lz = abs(z) - OFFSET
    d = math.sqrt(x*x + y*y + lz*lz) - RADIUS
    if mb > 0.0001:
        k = mb
        L = math.sqrt(x*x + y*y + lz*lz)
        far = math.sqrt(x*x + y*y + (lz + 2.0*abs(OFFSET))**2)
        v = min(max((far - L)/k, 0.0), 1.0)
        d = L - RADIUS - k*0.25*(1.0-v)*(1.0-v)
    return d
def extents(f, mb, n=400, half=1.0):
    xs = []; zs = []
    for i in range(n+1):
        x = -half + 2.0*half*i/n
        for j in range(n+1):
            z = -half + 2.0*half*j/n
            if f(x, 0.0, z, mb) <= 0.0: xs.append(x); zs.append(z)
    if not xs: return 0.0, 0.0
    return max(zs)-min(zs), max(xs)-min(xs)

print(f"r={RADIUS} offset={OFFSET}  (z幅 / x幅)", flush=True)
print(f"{'blend':>6} | {'最終メッシュ':>18} | {'現行プレビュー':>18} | {'候補プレビュー':>18} | 誤差 現行 -> 候補", flush=True)
for mb in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.4, 2.0):
    mz, mx = mesh_extents(mb)
    oz, ox = extents(sdf_now, mb)
    nz, nx = extents(sdf_new, mb)
    eo = max(abs(mz-oz), abs(mx-ox)); en = max(abs(mz-nz), abs(mx-nx))
    print(f"{mb:6.2f} | {mz:8.4f} {mx:8.4f} | {oz:8.4f} {ox:8.4f} | {nz:8.4f} {nx:8.4f} | "
          f"{eo:.4f} -> {en:.4f}  {'改善' if en < eo else '悪化'}", flush=True)
