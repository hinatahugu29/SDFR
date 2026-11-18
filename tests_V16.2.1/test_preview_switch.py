import bpy, sys, os, time
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

def make_tree(i):
    col = bpy.data.collections.new(f"C{i}"); scene.collection.children.link(col)
    out = bpy.data.objects.new(f"OUT{i}", bpy.data.meshes.new(f"M{i}")); scene.collection.objects.link(out)
    out.sdf_props.is_output = True; out.sdf_props.target_collection = col
    o = bpy.data.objects.new(f"P{i}", bpy.data.meshes.new(f"PM{i}")); col.objects.link(o)
    o.sdf_props.is_primitive = True; o.sdf_props.shape_type = 'sphere'; o.sdf_props.radius = 0.6
    bpy.context.view_layer.update(); engine.sync_sdf_stack(out)
    return out, col, o

outA, colA, primA = make_tree(1)
outB, colB, primB = make_tree(2)

if not hasattr(handlers, "preview_cache_is_stale"):
    print("RESULT: 旧版のためスキップ（preview_cache_is_stale が無い）", flush=True)
    raise SystemExit(0)

# 「ツリーAのぶんを描画済み」の状態を作る
handlers._preview_dirty = False
handlers._cached_prim_tex = object()      # 中身は問わない（None でなければよい）
handlers._cached_curve_guides = []
handlers._cached_output_name = outA.name

check("同じツリーなら作り直さない", handlers.preview_cache_is_stale(outA) is False)
check("別のツリーに切り替わったら作り直す", handlers.preview_cache_is_stale(outB) is True)

# オブジェクトを選ぶだけでアクティブツリーが変わる経路を再現する
bpy.context.view_layer.objects.active = primB
resolved = engine.resolve_active_output(bpy.context)
check("ツリーBの部品を選ぶとツリーBが解決される", resolved == outB,
      f"{getattr(resolved,'name',None)}")
check("その状態でキャッシュは stale と判定される",
      handlers.preview_cache_is_stale(resolved) is True,
      "（ここが False だと、何か動かすまでゴーストが前のツリーのまま残る）")

bpy.context.view_layer.objects.active = primA
resolved = engine.resolve_active_output(bpy.context)
check("ツリーAへ戻すと A が解決される", resolved == outA, f"{getattr(resolved,'name',None)}")
check("A のキャッシュはそのまま使える", handlers.preview_cache_is_stale(resolved) is False)

print("\nRESULT:", "ALL PASS" if not fail else f"{len(fail)} FAILED: {fail}", flush=True)
