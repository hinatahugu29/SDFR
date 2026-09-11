# Mirror Blend が AABB / bound_radius のパディングに入っていない件の再現テスト。
#   lib.rs      extra_pad     = smoothness + noise + shell + edge   (mirror_blend なし)
#   detect.wgsl bound_radius += params.y + layer_params.x + ...     (layer_params.w=mirror_blend なし)
# 仮説: Smoothness が小さく Mirror Blend が大きいと、ブレンドで膨らんだ部分が
#       ブロックカリングの候補判定から外れて最終メッシュだけ欠ける。
# 対照: 「実体2つ + Smoothness=blend」は同じ形になるはずで、かつ smoothness が
#       パディングに入っているのでカリングでは落ちない。差が出れば仮説どおり。
# 注意: プリミティブが数個だとブロック候補リストが実質フル評価になりカリングが
#       働かないので、遠方にダミーを撒いて候補判定を実際に動かす。
import bpy, bmesh, sys, os, time, math
_ARG = sys.argv[-1]
TREE = _ARG if os.path.isdir(_ARG) else r"E:\blender_addon\外部テスト\Rust-GPU-SDF-V16.2.1"
sys.path.insert(0, TREE)
import rust_gpu_sdf_addon as A; A.register()
from rust_gpu_sdf_addon import engine
from rust_gpu_sdf_addon._native import rust_gpu_sdf as R
R.init_gpu(os.path.join(os.path.expanduser("~"), "sdf_bench_cache_v1621.bin"), False)
scene = bpy.context.scene; scene.sdf_live_update = False; scene.sdf_show_result = True

RES = 192; DOMAIN = 2.0; RADIUS = 0.15; OFFSET = 0.25; TINY = 0.0001
DECOYS = int(os.environ.get("SDF_DECOYS", "40"))
BAND = 0.35   # 計測は |y| < BAND の中央クラスタだけ（ダミーは y=±0.7 に置く）
_n = [0]
def pump(n=2000):
    for _ in range(n):
        if engine.sdf_mesh_timer() is None: return
        time.sleep(0.005)
def wipe():
    for o in list(scene.objects): bpy.data.objects.remove(o, do_unlink=True)
    for c in list(bpy.data.collections): bpy.data.collections.remove(c)
def new_tree():
    _n[0] += 1; i = _n[0]
    col = bpy.data.collections.new(f"C{i}"); scene.collection.children.link(col)
    out = bpy.data.objects.new(f"OUT{i}", bpy.data.meshes.new(f"M{i}")); scene.collection.objects.link(out)
    p = out.sdf_props
    p.is_output = True; p.target_collection = col; p.resolution = RES
    p.use_weld = True; p.auto_domain = False; p.domain_size = DOMAIN
    return out, col
def sphere(col, name, loc=(0,0,0), smooth=TINY, r=RADIUS):
    o = bpy.data.objects.new(name, bpy.data.meshes.new(name+"M")); col.objects.link(o)
    p = o.sdf_props; p.is_primitive = True; p.shape_type = 'sphere'
    p.radius = r; p.smoothness = smooth
    o.location = loc; return o
def decoys(col, tag):
    for i in range(DECOYS):
        a = 2*math.pi*i/max(DECOYS,1)
        y = 0.7 if (i % 2 == 0) else -0.7
        sphere(col, f"d{tag}_{i}", loc=(0.55*math.cos(a), y, 0.55*math.sin(a)), r=0.05)
def build(out):
    bpy.context.view_layer.update(); engine.sync_sdf_stack(out); engine.sync_sdf_parents(out)
    engine._last_state_hashes.pop(out.name, None); engine.update_sdf_mesh(out); pump()
def stats(out):
    me = out.data
    co = [v.co for v in me.vertices if abs(v.co.y) < BAND]
    if not co: return (0, 0.0, 0.0)
    zs = [c.z for c in co]; xs = [c.x for c in co]
    return (len(co), max(zs)-min(zs), max(xs)-min(xs))

def mirrored(blend):
    out, col = new_tree(); s = sphere(col, f"m{blend}")
    p = s.sdf_props
    p.layout_use_mirror = True; p.mirror_z = True
    p.mirror_offset = OFFSET; p.mirror_blend = blend
    decoys(col, f"m{blend}")
    build(out); r = stats(out); wipe(); return r
def reference(blend):
    out, col = new_tree()
    sphere(col, f"a{blend}", loc=(0,0,OFFSET))
    sphere(col, f"b{blend}", loc=(0,0,-OFFSET), smooth=max(blend, TINY))
    decoys(col, f"r{blend}")
    build(out); r = stats(out); wipe(); return r

def analytic_x_width(k):
    # 中央面 z=0 での polynomial smin: 両側の距離が等しいので d = d1 - k/4
    # d1 = sqrt(x^2 + OFFSET^2) - RADIUS  ->  sqrt(x^2+OFFSET^2) = RADIUS + k/4
    t = RADIUS + max(k, 0.0)/4.0
    if t <= OFFSET: return 2.0*0.0 if t < OFFSET else 0.0
    return 2.0*math.sqrt(t*t - OFFSET*OFFSET)

cell = DOMAIN / RES
print(f"res={RES} domain={DOMAIN} cell={cell:.4f} r={RADIUS} offset={OFFSET} smoothness={TINY} decoys={DECOYS}", flush=True)
print(f"{'blend':>6} | {'mirror  v / z幅 / x幅':>28} | {'reference  v / z幅 / x幅':>28} | {'解析解 x幅':>10} | 判定", flush=True)
fail = []
for blend in (2.0, 3.0, 4.0, 6.0, 8.0):
    mv, mz, mx = mirrored(blend)
    rv, rz, rx = reference(blend)
    ax = analytic_x_width(blend)
    dz = abs(mz - rz); dx = abs(mx - rx); da = abs(mx - ax)
    ok = dz <= cell*3 and dx <= cell*3 and da <= cell*4 and (rv == 0 or abs(mv-rv) <= rv*0.25)
    if not ok: fail.append(blend)
    print(f"{blend:6.2f} | {mv:7d} {mz:8.4f} {mx:8.4f}     | {rv:7d} {rz:8.4f} {rx:8.4f}     | "
          f"{ax:10.4f} | {'OK' if ok else 'DIFF'}  dz={dz:.4f} dx={dx:.4f} d解析={da:.4f}", flush=True)

print("\nRESULT:", "差なし（カリング落ちは再現せず）" if not fail else f"差あり blend={fail}", flush=True)
