import bpy, bmesh, sys, os, time, math
# ツリーの場所は他のテストと同じく `-- <path>` で渡す。渡されなければ従来の場所を使う。
# ハードコードのままだと Linux/macOS のパッケージに対して回せない。
_ARG = sys.argv[-1]
TREE = _ARG if os.path.isdir(_ARG) else r"E:\blender_addon\外部テスト\Rust-GPU-SDF-V16.2.1"
sys.path.insert(0, TREE)
import rust_gpu_sdf_addon as A; A.register()
from rust_gpu_sdf_addon import engine
from rust_gpu_sdf_addon._native import rust_gpu_sdf as R
R.init_gpu(os.path.join(os.path.expanduser("~"), "sdf_bench_cache_v1621.bin"), False)
scene=bpy.context.scene; scene.sdf_live_update=True; scene.sdf_show_result=True
RES=128; OFFSET=0.4
fail=[]
def check(l,c,d=""):
    print(("PASS  " if c else "FAIL  ")+l+("   "+d if d else ""),flush=True)
    if not c: fail.append(l)
def pump(n=800):
    for _ in range(n):
        if engine.sdf_mesh_timer() is None: return
        time.sleep(0.005)
def new_tree(i,res=RES):
    col=bpy.data.collections.new(f"C{i}"); scene.collection.children.link(col)
    out=bpy.data.objects.new(f"OUT{i}",bpy.data.meshes.new(f"M{i}")); scene.collection.objects.link(out)
    out.sdf_props.is_output=True; out.sdf_props.target_collection=col
    out.sdf_props.resolution=res; out.sdf_props.use_weld=True
    return out,col
def sphere(col,name,loc=(0,0,0),r=0.6,smooth=0.3):
    o=bpy.data.objects.new(name,bpy.data.meshes.new(name+"M")); col.objects.link(o)
    p=o.sdf_props; p.is_primitive=True; p.shape_type='sphere'; p.radius=r; p.smoothness=smooth
    o.location=loc; return o
def sharp_near_plane(out,axis=2,at=0.0,tol=0.06):
    bm=bmesh.new(); bm.from_mesh(out.data); bm.normal_update()
    n=0; worst=0.0
    for e in bm.edges:
        if len(e.link_faces)!=2: continue
        a=e.calc_face_angle()
        mid=(e.verts[0].co+e.verts[1].co)*0.5
        if abs(mid[axis]-at)<=tol:
            if a>math.radians(30): n+=1
            worst=max(worst,a)
    bm.free(); return n, math.degrees(worst)
def build(out):
    bpy.context.view_layer.update(); engine.sync_sdf_stack(out); engine.sync_sdf_parents(out)
    engine._last_state_hashes.pop(out.name,None); engine.update_sdf_mesh(out); pump()

o1,c1=new_tree(1); s1=sphere(c1,"m_off")
p=s1.sdf_props; p.layout_use_mirror=True; p.mirror_z=True; p.mirror_offset=OFFSET; p.mirror_blend=0.0
build(o1); n1,w1=sharp_near_plane(o1)
print(f"Mirror Blend = 0.0   verts={len(o1.data.vertices):5d}  折れ目={n1:4d}  最大角={w1:6.1f}deg",flush=True)

o2,c2=new_tree(2); s2=sphere(c2,"m_on")
p=s2.sdf_props; p.layout_use_mirror=True; p.mirror_z=True; p.mirror_offset=OFFSET; p.mirror_blend=0.3
build(o2); n2,w2=sharp_near_plane(o2)
print(f"Mirror Blend = 0.3   verts={len(o2.data.vertices):5d}  折れ目={n2:4d}  最大角={w2:6.1f}deg",flush=True)

o3,c3=new_tree(3); sphere(c3,"a",loc=(0,0,OFFSET)); sphere(c3,"b",loc=(0,0,-OFFSET))
build(o3); n3,w3=sharp_near_plane(o3)
print(f"参考: 実体2つ+Smooth  verts={len(o3.data.vertices):5d}  折れ目={n3:4d}  最大角={w3:6.1f}deg",flush=True)

check("Blend=0 は従来どおり折れ目が残る（既存ファイル互換）", n1>0, f"{n1}本 {w1:.1f}deg")
check("Blend>0 で折れ目が消える", n2==0, f"{n2}本 {w2:.1f}deg")
check("Blend>0 の結果が実体2つの Smooth Union に近い", abs(w2-w3)<12.0, f"{w2:.1f} vs {w3:.1f}")

# X+Z 2軸
o4,c4=new_tree(4); s4=sphere(c4,"m_xz")
p=s4.sdf_props; p.layout_use_mirror=True; p.mirror_x=True; p.mirror_z=True; p.mirror_offset=OFFSET; p.mirror_blend=0.3
build(o4)
nz,wz=sharp_near_plane(o4,axis=2); nx,wx=sharp_near_plane(o4,axis=0)
print(f"2軸(X+Z) Blend=0.3   verts={len(o4.data.vertices):5d}  z面={nz}本/{wz:.1f}deg  x面={nx}本/{wx:.1f}deg",flush=True)
check("2軸でも折れ目が出ない", nz==0 and nx==0, f"z={nz} x={nx}")

# 速度
import statistics
def timed(out, blend, reps=3):
    out.sdf_props.resolution=192
    prim=[o for o in out.sdf_props.target_collection.objects][0]
    prim.sdf_props.mirror_blend=blend
    ts=[]
    for _ in range(reps):
        engine._last_state_hashes.pop(out.name,None)
        t=time.perf_counter(); engine.update_sdf_mesh(out); pump(); ts.append(time.perf_counter()-t)
    return statistics.median(ts)*1000
t_off=timed(o1,0.0); t_on=timed(o1,0.3)
print(f"評価コスト(res192, 1軸): Blend=0 {t_off:.1f} ms -> Blend=0.3 {t_on:.1f} ms  ({t_on/t_off:.2f}x)",flush=True)
print("\nRESULT:", "ALL PASS" if not fail else f"{len(fail)} FAILED: {fail}",flush=True)
