"""ビューポートで消したツリーが Tree ドロップダウンに残らないこと。

報告: 複数ツリーを作ったあと A(全選択) → X(削除) すると、選択肢に消したはずの
ツリーが残る（ユーザー数0の表示 "0 SDF_Result_Tree_002" になる）。

Blender の削除はオブジェクトをコレクションから外すが、こちらの `active_output`
（PointerProperty）が参照を握っている間はデータブロックが bpy.data に生き残る。
`_poll_sdf_output` は `is_output` しか見ていなかったため、実体の無いツリーが
選択肢に並び、選べてしまっていた。
"""
import bpy, sys

TREE = sys.argv[-1]
sys.path.insert(0, TREE)
import rust_gpu_sdf_addon as A
A.register()
from rust_gpu_sdf_addon import properties

print("TESTING TREE:", TREE, flush=True)
fail = []


def check(label, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + label + ("   " + detail if detail else ""), flush=True)
    if not cond:
        fail.append(label)


def dropdown():
    """Tree ドロップダウンが実際に出す候補（poll をそのまま使う）。"""
    sp = bpy.context.scene.sdf_scene_props
    return [o.name for o in bpy.data.objects if properties._poll_sdf_output(sp, o)]


for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)

bpy.ops.sdf.make_output()
bpy.ops.sdf.add_primitive(shape='sphere')
bpy.ops.sdf.add_tree()
bpy.ops.sdf.add_primitive(shape='box')

before = dropdown()
check("前提: 2本のツリーが選択肢に出る", len(before) == 2, f"{before}")

# --- ビューポートの A → X 相当 --------------------------------------------
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

after = dropdown()
check("消したツリーは選択肢に残らない", after == [], f"{after}")
check("active_output も消えたツリーを指さない",
      bpy.context.scene.sdf_scene_props.active_output is None,
      f"{getattr(bpy.context.scene.sdf_scene_props.active_output, 'name', None)}")

# --- 作り直したものは、ちゃんと出る（絞り込みすぎていないか）----------------
bpy.ops.sdf.make_output()
d2 = dropdown()
check("作り直したツリーは選択肢に出る", len(d2) == 1, f"{d2}")

bpy.ops.sdf.add_tree()
d3 = dropdown()
check("2本目を足せば2本とも出る", len(d3) == 2, f"{d3}")

# --- 1本だけ消した場合、残りは残ること -------------------------------------
target = bpy.data.objects[d3[1]]
bpy.ops.object.select_all(action='DESELECT')
target.select_set(True)
bpy.context.view_layer.objects.active = target
bpy.ops.object.delete()
d4 = dropdown()
check("1本だけ消したら、残った1本は選択肢に残る", d4 == [d3[0]], f"{d4}")

print("\nRESULT: " + ("ALL PASS" if not fail else f"{len(fail)} FAILED: {fail}"), flush=True)
