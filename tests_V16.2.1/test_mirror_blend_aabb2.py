# フェーズ2: Mirror Blend を最大 (2.0) にしたうえで、
#   - 全 Blend Profile (Round/Sharp/Soft/Tight/Chamfer)
#   - 1軸ミラー / 2軸(X+Z)ミラー
#   - Marching Cubes / Dual Contouring
# の各組み合わせで「ミラー+Blend」と「実体2つ+Smoothness=Blend」が一致するか見る。
# 一致すれば、AABB/bound_radius に mirror_blend が無いことは実害として出ていない。
import bpy, bmesh, sys, os, time, math
_ARG = sys.argv[-1]
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _tree import default_tree
TREE = _ARG if os.path.isdir(_ARG) else default_tree()
sys.path.insert(0, TREE)
import rust_gpu_sdf_addon as A; A.register()
from rust_gpu_sdf_addon import engine
from rust_gpu_sdf_addon._native import rust_gpu_sdf as R
R.init_gpu(os.path.join(os.path.expanduser("~"), "sdf_bench_cache_v1621.bin"), True)
scene = bpy.context.scene; scene.sdf_live_update = False; scene.sdf_show_result = True

RES = 192; DOMAIN = 2.0; RADIUS = 0.15; OFFSET = 0.25; TINY = 0.0001
BLEND = 2.0; DECOYS = 120; BAND = 0.35
PROFILES = [('0',"Round"), ('1',"Sharp"), ('2',"Soft"), ('3',"Tight"), ('4',"Chamfer")]
_n = [0]
def pump(n=2000):
    for _ in range(n):
        if engine.sdf_mesh_timer() is None: return
        time.sleep(0.005)
def wipe():
    for o in list(scene.objects): bpy.data.objects.remove(o, do_unlink=True)
    for c in list(bpy.data.collections): bpy.data.collections.remove(c)
def new_tree(algo):
    _n[0] += 1; i = _n[0]
    col = bpy.data.collections.new(f"C{i}"); scene.collection.children.link(col)
    out = bpy.data.objects.new(f"OUT{i}", bpy.data.meshes.new(f"M{i}")); scene.collection.objects.link(out)
    p = out.sdf_props
    p.is_output = True; p.target_collection = col; p.resolution = RES
    p.use_weld = True; p.auto_domain = False; p.domain_size = DOMAIN; p.algo_type = algo
    return out, col
def sphere(col, name, loc=(0,0,0), smooth=TINY, r=RADIUS, prof='0'):
    o = bpy.data.objects.new(name, bpy.data.meshes.new(name+"M")); col.objects.link(o)
    p = o.sdf_props; p.is_primitive = True; p.shape_type = 'sphere'
    p.radius = r; p.smoothness = smooth; p.blend_profile = prof
    o.location = loc; return o
def decoys(col, tag):
    for i in range(DECOYS):
        a = 2*math.pi*i/DECOYS
        sphere(col, f"d{tag}_{i}", loc=(0.55*math.cos(a), 0.7 if i%2 else -0.7, 0.55*math.sin(a)), r=0.05)
def build(out):
    bpy.context.view_layer.update(); engine.sync_sdf_stack(out); engine.sync_sdf_parents(out)
    engine._last_state_hashes.pop(out.name, None); engine.update_sdf_mesh(out); pump()
def stats(out):
    co = [v.co for v in out.data.vertices if abs(v.co.y) < BAND]
    if not co: return (0, 0.0, 0.0)
    return (len(co), max(c.z for c in co)-min(c.z for c in co), max(c.x for c in co)-min(c.x for c in co))

def mirrored(prof, two_axis, algo):
    out, col = new_tree(algo); s = sphere(col, "m", prof=prof)
    p = s.sdf_props
    p.layout_use_mirror = True; p.mirror_z = True; p.mirror_x = two_axis
    p.mirror_offset = OFFSET; p.mirror_blend = BLEND
    decoys(col, "m")
    build(out); r = stats(out); wipe(); return r
def reference(prof, two_axis, algo):
    # ミラーを実体で置き換える（2軸なら 4 個）。全球に同じ Smoothness を与えること。
    # 先頭だけ TINY にすると accum への最初の合流の k が変わり、Chamfer で形が変わる。
    out, col = new_tree(algo)
    locs = [(0,0,OFFSET), (0,0,-OFFSET)]
    if two_axis:
        locs = [(x,0,z) for z in (OFFSET,-OFFSET) for x in (OFFSET,-OFFSET)]
    for i, l in enumerate(locs):
        sphere(col, f"r{i}", loc=l, smooth=BLEND, prof=prof)
    decoys(col, "r")
    build(out); r = stats(out); wipe(); return r

cell = DOMAIN / RES
print(f"blend={BLEND} res={RES} domain={DOMAIN} cell={cell:.4f} decoys={DECOYS}", flush=True)
print(f"{'algo':>4} {'profile':>8} {'axes':>5} | {'mirror v/z幅/x幅':>26} | {'reference v/z幅/x幅':>26} | 判定", flush=True)
fail = []
for algo in ("MC", "DC"):
    for prof, pname in PROFILES:
        for two in (False, True):
            mv, mz, mx = mirrored(prof, two, algo)
            rv, rz, rx = reference(prof, two, algo)
            dz = abs(mz-rz); dx = abs(mx-rx)
            ok = mv > 0 and dz <= cell*3 and dx <= cell*3
            label = f"{algo} {pname} {'X+Z' if two else 'Z'}"
            if not ok: fail.append(label)
            print(f"{algo:>4} {pname:>8} {'X+Z' if two else 'Z':>5} | {mv:6d} {mz:8.4f} {mx:8.4f}   | "
                  f"{rv:6d} {rz:8.4f} {rx:8.4f}   | {'OK' if ok else 'DIFF'}  dz={dz:.4f} dx={dx:.4f}", flush=True)

print("\nRESULT:", "全一致（カリング落ちは再現せず）" if not fail else f"差あり: {fail}", flush=True)
