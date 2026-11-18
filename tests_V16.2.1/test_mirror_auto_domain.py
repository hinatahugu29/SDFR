# Auto Domain (既定 ON) は engine.py で prim_r = max_s*1.5 と原点距離だけから決めており、
# mirror_offset も mirror_blend も smoothness も見ていない。
# ミラーのコピーはローカル空間で ±offset に出るので、オフセットが大きいと
# 計算領域から溢れて最終メッシュが切れるはず。手動ドメインと比べて確認する。
import bpy, sys, os, time
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

RES = 160; RADIUS = 1.0; TINY = 0.0001
_n = [0]
def pump(n=3000):
    for _ in range(n):
        if engine.sdf_mesh_timer() is None: return
        time.sleep(0.005)
def wipe():
    for o in list(scene.objects): bpy.data.objects.remove(o, do_unlink=True)
    for c in list(bpy.data.collections): bpy.data.collections.remove(c)
def run(offset, blend, auto, manual_domain=40.0):
    _n[0] += 1; i = _n[0]
    col = bpy.data.collections.new(f"C{i}"); scene.collection.children.link(col)
    out = bpy.data.objects.new(f"OUT{i}", bpy.data.meshes.new(f"M{i}")); scene.collection.objects.link(out)
    p = out.sdf_props
    p.is_output = True; p.target_collection = col; p.resolution = RES; p.use_weld = True
    p.auto_domain = auto
    if not auto: p.domain_size = manual_domain
    o = bpy.data.objects.new("m", bpy.data.meshes.new("mM")); col.objects.link(o)
    q = o.sdf_props; q.is_primitive = True; q.shape_type = 'sphere'
    q.radius = RADIUS; q.smoothness = TINY
    q.layout_use_mirror = True; q.mirror_z = True
    q.mirror_offset = offset; q.mirror_blend = blend
    bpy.context.view_layer.update(); engine.sync_sdf_stack(out); engine.sync_sdf_parents(out)
    engine._last_state_hashes.pop(out.name, None); engine.update_sdf_mesh(out); pump()
    vs = out.data.vertices
    dom = out.sdf_props.domain_size
    if len(vs) == 0: r = (0, 0.0, dom)
    else: r = (len(vs), max(v.co.z for v in vs)-min(v.co.z for v in vs), dom)
    wipe(); return r

print(f"半径={RADIUS} 1軸(Z)ミラー  期待 z幅 = 2*(offset+半径) [blend=0]", flush=True)
print(f"{'offset':>7} {'blend':>6} | {'AutoDomain: 幅 / domain':>26} | {'手動 domain=40: 幅':>20} | 判定", flush=True)
for offset in (1.0, 3.0, 6.0, 12.0, 20.0):
    for blend in (0.0, 1.0):
        av, az, adom = run(offset, blend, True)
        mv, mz, _ = run(offset, blend, False)
        ok = mz > 0 and abs(az - mz) <= mz*0.02
        print(f"{offset:7.1f} {blend:6.2f} | {az:12.4f} / {adom:8.2f}   | {mz:16.4f}   | "
              f"{'OK' if ok else 'CLIPPED'}  差={az-mz:+.4f}", flush=True)
