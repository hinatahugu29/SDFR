import bpy, bmesh, sys, os, time, math
sys.path.insert(0, r"E:\blender_addon\外部テスト\Rust-GPU-SDF-V16.2.1")
import rust_gpu_sdf_addon as A; A.register()
from rust_gpu_sdf_addon import engine
from rust_gpu_sdf_addon._native import rust_gpu_sdf as R
R.init_gpu(os.path.join(os.path.expanduser("~"), "sdf_bench_cache.bin"), False)
scene = bpy.context.scene; scene.sdf_live_update=True; scene.sdf_show_result=True
RES=128
def pump(n=800):
    for _ in range(n):
        if engine.sdf_mesh_timer() is None: return
        time.sleep(0.005)
def new_tree(i):
    col=bpy.data.collections.new(f"C{i}"); scene.collection.children.link(col)
    out=bpy.data.objects.new(f"OUT{i}", bpy.data.meshes.new(f"M{i}")); scene.collection.objects.link(out)
    out.sdf_props.is_output=True; out.sdf_props.target_collection=col
    out.sdf_props.resolution=RES; out.sdf_props.use_weld=True
    return out,col
def sphere(col,name,loc=(0,0,0),r=0.6,smooth=0.3):
    o=bpy.data.objects.new(name,bpy.data.meshes.new(name+"M")); col.objects.link(o)
    p=o.sdf_props; p.is_primitive=True; p.shape_type='sphere'; p.radius=r; p.smoothness=smooth
    o.location=loc; return o
def sharp(out):
    bm=bmesh.new(); bm.from_mesh(out.data); bm.normal_update()
    n=0; worst=0.0
    for e in bm.edges:
        if len(e.link_faces)!=2: continue
        a=e.calc_face_angle()
        if a>math.radians(30): n+=1
        worst=max(worst,a)
    bm.free(); return n, math.degrees(worst)
def build(out):
    bpy.context.view_layer.update(); engine.sync_sdf_stack(out); engine.sync_sdf_parents(out)
    engine._last_state_hashes.pop(out.name,None); engine.update_sdf_mesh(out); pump()

# Radial: プリミティブ側（WGSL の領域繰り返し）
o1,c1=new_tree(11); s1=sphere(c1,"R_prim")
p=s1.sdf_props; p.layout_use_radial=True; p.radial_count=4; p.radial_radius=0.5; p.radial_axis='2'
build(o1); n1,w1=sharp(o1)
print(f"Radial / プリミティブ側 (領域繰り返し)   verts={len(o1.data.vertices):6d}  鋭い辺={n1:5d}  最大角={w1:6.1f}deg")

# Radial: 仕切り側（Python でコピーを実体化）
o2,c2=new_tree(12); sphere(c2,"R_div")
em=bpy.data.objects.new("SDF_Group_R",None); c2.objects.link(em)
ep=em.sdf_props; ep.is_primitive=False; ep.layout_use_radial=True; ep.radial_count=4; ep.radial_radius=0.5; ep.radial_axis='2'
build(o2); n2,w2=sharp(o2)
print(f"Radial / 仕切り側 (実体コピー)           verts={len(o2.data.vertices):6d}  鋭い辺={n2:5d}  最大角={w2:6.1f}deg")

# Grid
o3,c3=new_tree(13); s3=sphere(c3,"G_prim")
p=s3.sdf_props; p.layout_use_grid=True; p.grid_count_x=3; p.grid_count_y=1; p.grid_count_z=1
p.grid_spacing_x=0.8; p.grid_spacing_y=1.0; p.grid_spacing_z=1.0
build(o3); n3,w3=sharp(o3)
print(f"Grid   / プリミティブ側 (領域繰り返し)   verts={len(o3.data.vertices):6d}  鋭い辺={n3:5d}  最大角={w3:6.1f}deg")

o4,c4=new_tree(14); sphere(c4,"G_div")
em4=bpy.data.objects.new("SDF_Group_G",None); c4.objects.link(em4)
ep4=em4.sdf_props; ep4.is_primitive=False; ep4.layout_use_grid=True
ep4.grid_count_x=3; ep4.grid_count_y=1; ep4.grid_count_z=1
ep4.grid_spacing_x=0.8; ep4.grid_spacing_y=1.0; ep4.grid_spacing_z=1.0
build(o4); n4,w4=sharp(o4)
print(f"Grid   / 仕切り側 (実体コピー)           verts={len(o4.data.vertices):6d}  鋭い辺={n4:5d}  最大角={w4:6.1f}deg")
