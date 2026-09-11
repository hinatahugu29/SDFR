# Mirror Blend の周辺確認:
#  A) オフセットが小さい/0（コピーが重なる）ときに、ブレンドが形を余計に太らせないか
#  B) 1軸/2軸/3軸が「実体コピー + Smoothness」と一致するか（3軸は8回評価）
#  C) 軸数ごとの評価コスト（2^軸数 のはず）
import bpy, sys, os, time, math, statistics
_ARG = sys.argv[-1]
TREE = _ARG if os.path.isdir(_ARG) else r"E:\blender_addon\外部テスト\Rust-GPU-SDF-V16.2.1"
sys.path.insert(0, TREE)
import rust_gpu_sdf_addon as A; A.register()
from rust_gpu_sdf_addon import engine
from rust_gpu_sdf_addon._native import rust_gpu_sdf as R
R.init_gpu(os.path.join(os.path.expanduser("~"), "sdf_bench_cache_v1621.bin"), False)
scene = bpy.context.scene; scene.sdf_live_update = False; scene.sdf_show_result = True

RES = 160; DOMAIN = 4.0; RADIUS = 0.15; TINY = 0.0001
_n = [0]
def pump(n=3000):
    for _ in range(n):
        if engine.sdf_mesh_timer() is None: return
        time.sleep(0.005)
def wipe():
    for o in list(scene.objects): bpy.data.objects.remove(o, do_unlink=True)
    for c in list(bpy.data.collections): bpy.data.collections.remove(c)
def tree(res=RES):
    _n[0] += 1; i = _n[0]
    col = bpy.data.collections.new(f"C{i}"); scene.collection.children.link(col)
    out = bpy.data.objects.new(f"OUT{i}", bpy.data.meshes.new(f"M{i}")); scene.collection.objects.link(out)
    p = out.sdf_props
    p.is_output = True; p.target_collection = col; p.resolution = res
    p.use_weld = True; p.auto_domain = False; p.domain_size = DOMAIN
    return out, col
def sphere(col, name, loc=(0,0,0), smooth=TINY):
    o = bpy.data.objects.new(name, bpy.data.meshes.new(name+"M")); col.objects.link(o)
    p = o.sdf_props; p.is_primitive = True; p.shape_type = 'sphere'
    p.radius = RADIUS; p.smoothness = smooth
    o.location = loc; return o
def go(out, keep=False):
    bpy.context.view_layer.update(); engine.sync_sdf_stack(out); engine.sync_sdf_parents(out)
    engine._last_state_hashes.pop(out.name, None); engine.update_sdf_mesh(out); pump()
    vs = out.data.vertices
    if len(vs) == 0: r = (0, 0.0, 0.0, 0.0)
    else:
        r = (len(vs),
             max(v.co.x for v in vs)-min(v.co.x for v in vs),
             max(v.co.y for v in vs)-min(v.co.y for v in vs),
             max(v.co.z for v in vs)-min(v.co.z for v in vs))
    if not keep: wipe()
    return r
def mirror(blend, offset, axes=('z',), keep=False, res=RES):
    out, col = tree(res); s = sphere(col, "m")
    p = s.sdf_props
    p.layout_use_mirror = True; p.mirror_offset = offset; p.mirror_blend = blend
    p.mirror_x = 'x' in axes; p.mirror_y = 'y' in axes; p.mirror_z = 'z' in axes
    return (go(out, keep), out) if keep else go(out)
def copies(blend, offset, axes):
    out, col = tree()
    xs = (offset, -offset) if 'x' in axes else (0.0,)
    ys = (offset, -offset) if 'y' in axes else (0.0,)
    zs = (offset, -offset) if 'z' in axes else (0.0,)
    i = 0
    for x in xs:
        for y in ys:
            for z in zs:
                sphere(col, f"c{i}", loc=(x,y,z), smooth=max(blend, TINY)); i += 1
    return go(out)

print("=== A) オフセットが小さいとき: ブレンドが形を余計に太らせないか ===", flush=True)
print(f"半径={RADIUS} 直径={2*RADIUS:.3f}  1軸(Z) blend=1.0", flush=True)
print(f"{'offset':>7} | {'blend=0 の x幅/z幅':>22} | {'blend=1.0 の x幅/z幅':>22} | x方向の増分", flush=True)
for off in (0.0, 0.05, 0.10, 0.15, 0.25, 0.50):
    _, x0, _, z0 = mirror(0.0, off)
    _, x1, _, z1 = mirror(1.0, off)
    print(f"{off:7.2f} | {x0:10.4f} {z0:10.4f}   | {x1:10.4f} {z1:10.4f}   | {x1-x0:+.4f}", flush=True)

print("\n=== B) 軸数ごとの一致（実体コピー + Smoothness=blend との比較） ===", flush=True)
OFF = 0.25; BL = 1.0
print(f"offset={OFF} blend={BL}", flush=True)
print(f"{'axes':>6} {'copies':>7} | {'mirror x/y/z幅':>26} | {'reference x/y/z幅':>26} | 判定", flush=True)
cell = DOMAIN / RES
for axes in (('z',), ('x','z'), ('x','y','z')):
    mv, mx, my, mz = mirror(BL, OFF, axes)
    rv, rx, ry, rz = copies(BL, OFF, axes)
    d = max(abs(mx-rx), abs(my-ry), abs(mz-rz))
    ok = mv > 0 and d <= cell*3
    print(f"{''.join(axes).upper():>6} {2**len(axes):>7} | {mx:8.4f} {my:8.4f} {mz:8.4f}   | "
          f"{rx:8.4f} {ry:8.4f} {rz:8.4f}   | {'OK' if ok else 'DIFF'}  最大差={d:.4f} (cell={cell:.4f})", flush=True)

print("\n=== C) 軸数ごとの評価コスト (res=224) ===", flush=True)
def timed(axes, blend, reps=3):
    ts = []
    for _ in range(reps):
        t = time.perf_counter(); mirror(blend, OFF, axes, res=224); ts.append(time.perf_counter()-t)
    return statistics.median(ts)*1000
base = timed(('z',), 0.0)
print(f"{'axes':>6} {'評価回数':>8} | {'blend=0':>10} {'blend=1.0':>11} | 倍率", flush=True)
for axes in (('z',), ('x','z'), ('x','y','z')):
    t0 = timed(axes, 0.0); t1 = timed(axes, BL)
    print(f"{''.join(axes).upper():>6} {2**len(axes):>8} | {t0:9.1f}ms {t1:10.1f}ms | {t1/max(t0,1e-6):.2f}x", flush=True)
