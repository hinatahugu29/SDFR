import bpy, sys, os
TREE = sys.argv[-1]
sys.path.insert(0, TREE)
import rust_gpu_sdf_addon as A
assert os.path.abspath(os.path.dirname(A.__file__)).lower().startswith(os.path.abspath(TREE).lower()), A.__file__
A.register()
from rust_gpu_sdf_addon import engine, handlers
scene = bpy.context.scene
fail = []
def check(l, c, d=""):
    print(("PASS  " if c else "FAIL  ") + l + ("   " + d if d else ""), flush=True)
    if not c: fail.append(l)

def make_tree(i, shape):
    col = bpy.data.collections.new(f"C{i}"); scene.collection.children.link(col)
    out = bpy.data.objects.new(f"OUT{i}", bpy.data.meshes.new(f"M{i}")); scene.collection.objects.link(out)
    out.sdf_props.is_output = True; out.sdf_props.target_collection = col
    o = bpy.data.objects.new(f"P{i}", bpy.data.meshes.new(f"PM{i}")); col.objects.link(o)
    o.sdf_props.is_primitive = True; o.sdf_props.shape_type = shape; o.sdf_props.radius = 0.6
    bpy.context.view_layer.update(); engine.sync_sdf_stack(out)
    return out, col, o

outA, colA, primA = make_tree(1, 'sphere')
outB, colB, primB = make_tree(2, 'cylinder')

def panel_shows():
    """パネルが実際に表示する内容（解決されたツリー / Parts / The Stack）。"""
    out = engine.resolve_active_output(bpy.context)
    if out is None:
        return None, None, []
    col = out.sdf_props.target_collection
    return out, (col.name if col else None), [it.obj_name for it in out.sdf_props.sdf_stack]

# ツリーBの部品を選んだ状態から、ドロップダウンでツリーAに切り替える
bpy.context.view_layer.objects.active = primB
out, parts, stack = panel_shows()
check("前提: Bの部品を選ぶと B が表示される", out == outB, f"{getattr(out,'name',None)} / {parts} / {stack}")

scene.sdf_scene_props.active_output = outA      # ← UIのドロップダウン操作に相当

out, parts, stack = panel_shows()
check("ドロップダウンで A に切り替えると A が表示される", out == outA,
      f"{getattr(out,'name',None)}")
check("Parts の表示も A の置き場になる", parts == colA.name, f"{parts}")
check("The Stack の中身も A のものになる", stack == [primA.name], f"{stack}")
check("プレビューのキャッシュも作り直し対象になる",
      handlers.preview_cache_is_stale(out) is True)

# 逆向きも
scene.sdf_scene_props.active_output = outB
out, parts, stack = panel_shows()
check("B へ戻すと B が表示される", out == outB and parts == colB.name and stack == [primB.name],
      f"{getattr(out,'name',None)} / {parts} / {stack}")

# 部品の選択は引き続き効く（ドロップダウンを固定していても選択が優先）
bpy.context.view_layer.objects.active = primA
out, _, _ = panel_shows()
check("部品を選ぶ操作は従来どおり効く", out == outA, f"{getattr(out,'name',None)}")

print("\nRESULT:", "ALL PASS" if not fail else f"{len(fail)} FAILED: {fail}", flush=True)
