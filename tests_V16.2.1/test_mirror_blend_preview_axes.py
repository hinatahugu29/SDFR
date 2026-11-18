# 多軸ミラーでの プレビュー近似 (max を取る) の誤差を最終メッシュと比べる。
# 軸ごとの seam_cut を合計する版。厳密解でも、原点では軸数 n に対して n*k/4 だけ
# 内側に寄る（同値の smin を n 回重ねる）ので、max より合計の方が理屈に合う。
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

RES = 192; DOMAIN = 6.0; RADIUS = 0.15; OFFSET = 0.25; TINY = 0.0001
_n = [0]
def pump(n=2000):
    for _ in range(n):
        if engine.sdf_mesh_timer() is None: return
        time.sleep(0.005)
def wipe():
    for o in list(scene.objects): bpy.data.objects.remove(o, do_unlink=True)
    for c in list(bpy.data.collections): bpy.data.collections.remove(c)
def mesh_extents(blend, axes):
    _n[0] += 1; i = _n[0]
    col = bpy.data.collections.new(f"C{i}"); scene.collection.children.link(col)
    out = bpy.data.objects.new(f"OUT{i}", bpy.data.meshes.new(f"M{i}")); scene.collection.objects.link(out)
    p = out.sdf_props
    p.is_output = True; p.target_collection = col; p.resolution = RES
    p.use_weld = True; p.auto_domain = False; p.domain_size = DOMAIN
    o = bpy.data.objects.new("m", bpy.data.meshes.new("mM")); col.objects.link(o)
    q = o.sdf_props; q.is_primitive = True; q.shape_type = 'sphere'
    q.radius = RADIUS; q.smoothness = TINY
    q.layout_use_mirror = True
    q.mirror_x = 'x' in axes; q.mirror_y = 'y' in axes; q.mirror_z = 'z' in axes
    q.mirror_offset = OFFSET; q.mirror_blend = blend
    bpy.context.view_layer.update(); engine.sync_sdf_stack(out); engine.sync_sdf_parents(out)
    engine._last_state_hashes.pop(out.name, None); engine.update_sdf_mesh(out); pump()
    vs = out.data.vertices
    r = (0.0, 0.0) if len(vs) == 0 else (max(v.co.x for v in vs)-min(v.co.x for v in vs),
                                         max(v.co.z for v in vs)-min(v.co.z for v in vs))
    wipe(); return r
def seam_cut(lp, disp, k):
    near = math.sqrt(sum(t*t for t in lp))
    far = math.sqrt(sum((t+d)**2 for t, d in zip(lp, disp)))
    v = min(max((far-near)/k, 0.0), 1.0)
    return k * 0.25 * (1.0-v) * (1.0-v)
def preview(x, y, z, mb, axes):
    # shader.py と同じ順序: 先に折り返し、その位置から距離差を採る。
    lx = abs(x) - OFFSET if 'x' in axes else x
    ly = abs(y) - OFFSET if 'y' in axes else y
    lz = abs(z) - OFFSET if 'z' in axes else z
    lp = (lx, ly, lz)
    L = math.sqrt(lx*lx + ly*ly + lz*lz)
    cut = 0.0
    if mb > 0.0001:
        span = 2.0*abs(OFFSET)
        if "x" in axes: cut += seam_cut(lp, (span, 0.0, 0.0), mb)
        if "y" in axes: cut += seam_cut(lp, (0.0, span, 0.0), mb)
        if "z" in axes: cut += seam_cut(lp, (0.0, 0.0, span), mb)
    return L - RADIUS - cut
def preview_extents(mb, axes, n=500, half=2.5):
    xs = []; zs = []
    for i in range(n+1):
        x = -half + 2.0*half*i/n
        for j in range(n+1):
            z = -half + 2.0*half*j/n
            if preview(x, 0.0, z, mb, axes) <= 0.0: xs.append(x); zs.append(z)
    if not xs: return 0.0, 0.0
    return max(xs)-min(xs), max(zs)-min(zs)

print(f"r={RADIUS} offset={OFFSET}  y=0 断面の x幅 / z幅", flush=True)
print(f"{'axes':>5} {'blend':>6} | {'最終メッシュ':>18} | {'プレビュー(新)':>18} | 誤差", flush=True)
for axes in ('z', 'xz', 'xyz'):
    for mb in (0.5, 1.0, 2.0):
        mx, mz = mesh_extents(mb, axes)
        px, pz = preview_extents(mb, axes)
        print(f"{axes.upper():>5} {mb:6.2f} | {mx:8.4f} {mz:8.4f} | {px:8.4f} {pz:8.4f} | "
              f"{max(abs(mx-px), abs(mz-pz)):.4f}", flush=True)
