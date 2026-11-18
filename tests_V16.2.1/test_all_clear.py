"""All Clear の取りこぼしを見る。

1. 「Show Result Mesh」を OFF にすると出力オブジェクトは hide_viewport=True になる。
   旧実装は select_set() → bpy.ops.object.delete() だったので、選択できない
   非表示オブジェクトが静かに削除対象から漏れていた。
2. 履歴オブジェクトの判定が部分一致だったため、ユーザーが自分で付けた
   "My_SDF_Backup" のような名前まで巻き込んでいた。
"""
import bpy, sys

TREE = sys.argv[-1]
sys.path.insert(0, TREE)
import rust_gpu_sdf_addon as A
A.register()

print("TESTING TREE:", TREE, flush=True)
fail = []


def check(label, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + label + ("   " + detail if detail else ""), flush=True)
    if not cond:
        fail.append(label)


def build_tree():
    col = bpy.data.collections.new("SDF_Collection")
    bpy.context.scene.collection.children.link(col)
    out = bpy.data.objects.new("SDF_Result", bpy.data.meshes.new("m"))
    bpy.context.scene.collection.objects.link(out)
    out.sdf_props.is_output = True
    out.sdf_props.target_collection = col
    for i in range(2):
        o = bpy.data.objects.new(f"P{i}", bpy.data.meshes.new(f"pm{i}"))
        col.objects.link(o)
        o.sdf_props.is_primitive = True
        o.sdf_props.shape_type = 'sphere'
    return out, col


# --- 1. 非表示の出力も消えるか -------------------------------------------
out, col = build_tree()
# ユーザーが自分で付けた、紛らわしいが無関係な名前のオブジェクト
mine = bpy.data.objects.new("My_SDF_Backup_reference", bpy.data.meshes.new("mine"))
bpy.context.scene.collection.objects.link(mine)

bpy.context.scene.sdf_show_result = False   # ここで out.hide_viewport = True になる
check("前提: 出力が非表示になっている", out.hide_viewport, f"hide_viewport={out.hide_viewport}")

bpy.ops.sdf.all_clear()

left = [o.name for o in bpy.context.scene.objects]
check("非表示の出力も削除される", "SDF_Result" not in left, f"left={left}")
check("プリミティブも削除される", not any(n.startswith("P") for n in left), f"left={left}")
check("無関係な自作オブジェクトは残る", "My_SDF_Backup_reference" in left, f"left={left}")

# --- 2. 表示状態でも従来どおり消えるか -----------------------------------
bpy.context.scene.sdf_show_result = True
out2, col2 = build_tree()
check("前提: 出力は表示されている", not out2.hide_viewport)
bpy.ops.sdf.all_clear()
left2 = [o.name for o in bpy.context.scene.objects]
check("表示中の出力も従来どおり削除される",
      not any(o.name.startswith("SDF_Result") for o in bpy.context.scene.objects), f"left={left2}")

print("\nRESULT: " + ("ALL PASS" if not fail else f"{len(fail)} FAILED: {fail}"), flush=True)
