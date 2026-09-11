# Soft プロファイル (exp smin) の膨張を確認する。
#   apply_profile_union: profile==2 -> -k*log2(2^(-d1/k) + 2^(-d2/k))
#   d1==d2==d のとき戻り値は d - k。つまり2つの形が完全に離れていても k だけ膨らむ。
# Mirror Blend 固有か、通常の Smoothness でも起きる既存挙動かを切り分ける。
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

RES = 160; DOMAIN = 8.0; RADIUS = 0.15; OFFSET = 0.25; TINY = 0.0001
SOFT = '2'; ROUND = '0'
_n = [0]
def pump(n=2000):
    for _ in range(n):
        if engine.sdf_mesh_timer() is None: return
        time.sleep(0.005)
def wipe():
    for o in list(scene.objects): bpy.data.objects.remove(o, do_unlink=True)
    for c in list(bpy.data.collections): bpy.data.collections.remove(c)
def tree():
    _n[0] += 1; i = _n[0]
    col = bpy.data.collections.new(f"C{i}"); scene.collection.children.link(col)
    out = bpy.data.objects.new(f"OUT{i}", bpy.data.meshes.new(f"M{i}")); scene.collection.objects.link(out)
    p = out.sdf_props
    p.is_output = True; p.target_collection = col; p.resolution = RES
    p.use_weld = True; p.auto_domain = False; p.domain_size = DOMAIN
    return out, col
def sphere(col, name, loc=(0,0,0), smooth=TINY, prof=ROUND):
    o = bpy.data.objects.new(name, bpy.data.meshes.new(name+"M")); col.objects.link(o)
    p = o.sdf_props; p.is_primitive = True; p.shape_type = 'sphere'
    p.radius = RADIUS; p.smoothness = smooth; p.blend_profile = prof
    o.location = loc; return o
def go(out):
    bpy.context.view_layer.update(); engine.sync_sdf_stack(out); engine.sync_sdf_parents(out)
    engine._last_state_hashes.pop(out.name, None); engine.update_sdf_mesh(out); pump()
    vs = out.data.vertices
    r = (0, 0.0) if len(vs) == 0 else (len(vs), max(v.co.z for v in vs)-min(v.co.z for v in vs))
    wipe(); return r

def mirror_case(k, prof):
    out, col = tree(); s = sphere(col, "m", prof=prof)
    q = s.sdf_props; q.layout_use_mirror = True; q.mirror_z = True
    q.mirror_offset = OFFSET; q.mirror_blend = k
    return go(out)
def smoothness_case(k, prof):
    out, col = tree()
    sphere(col, "a", loc=(0,0,OFFSET), smooth=k, prof=prof)
    sphere(col, "b", loc=(0,0,-OFFSET), smooth=k, prof=prof)
    return go(out)

base = 2*(OFFSET+RADIUS)
print(f"res={RES} domain={DOMAIN}(=半幅) 素の z幅={base:.3f}", flush=True)
print(f"{'k':>5} | {'Mirror Blend + Soft':>22} | {'Smoothness + Soft':>22} | {'Mirror Blend + Round':>22} | 予測(素+2k)", flush=True)
for k in (0.25, 0.5, 1.0, 2.0):
    mv, mz = mirror_case(k, SOFT)
    sv, sz = smoothness_case(k, SOFT)
    rv, rz = mirror_case(k, ROUND)
    print(f"{k:5.2f} | {mv:8d} {mz:11.4f}   | {sv:8d} {sz:11.4f}   | {rv:8d} {rz:11.4f}   | {base+2*k:11.4f}", flush=True)
