"""プレビュー用プリミティブテクスチャの stride が3箇所で揃っているかを見る。

V16.2.0 の退行の再発防止。テクスチャ幅・1プリミティブぶんに積まれる float 数・
shader.py が texelFetch する最大 index、この3つが揃っていないと
GPUTexture のバッファ長が合わず、プリミティブが一定数を超えた時点で
ゴーストプレビューが例外で丸ごと消える。

--background では GPU コンテキストが無く GPUTexture を実際に作れないので、
「作る直前の寸法計算」を検証する。
"""
import bpy, sys, os, re

TREE = sys.argv[-1]
sys.path.insert(0, TREE)
import rust_gpu_sdf_addon as A
A.register()
from rust_gpu_sdf_addon import handlers, engine

print("TESTING TREE:", TREE, flush=True)

fail = []


def check(label, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + label + ("   " + detail if detail else ""), flush=True)
    if not cond:
        fail.append(label)


# --- 1. shader.py が読む最大 index と幅が合っているか ----------------------
shader_src = open(os.path.join(TREE, "rust_gpu_sdf_addon", "shader.py"), encoding="utf-8").read()
fetch_idx = [int(m) for m in re.findall(r"texelFetch\(primTex,\s*ivec2\((\d+)\s*,", shader_src)]
check("shader が primTex を読んでいる", bool(fetch_idx), f"{len(fetch_idx)} fetch")
check(
    "テクスチャ幅がシェーダの最大 index を満たす",
    max(fetch_idx) == handlers.PRIM_TEX_WIDTH - 1,
    f"max index={max(fetch_idx)} / PRIM_TEX_WIDTH={handlers.PRIM_TEX_WIDTH}",
)

# --- 2. 実際に積まれる float 数が幅と一致するか ----------------------------
col = bpy.data.collections.new("SDF_Collection")
bpy.context.scene.collection.children.link(col)
out = bpy.data.objects.new("SDF_Result", bpy.data.meshes.new("m"))
bpy.context.scene.collection.objects.link(out)
out.sdf_props.is_output = True
out.sdf_props.target_collection = col

N = 20  # 退行時に壊れ始めるのは 17 個目なので、それを跨ぐ数で見る
for i in range(N):
    o = bpy.data.objects.new(f"P{i}", bpy.data.meshes.new(f"pm{i}"))
    col.objects.link(o)
    o.sdf_props.is_primitive = True
    o.sdf_props.shape_type = 'sphere'
    o.location = (i * 0.3, 0, 0)
bpy.context.view_layer.update()

engine.sync_sdf_stack(out)
inv = out.matrix_world.inverted()
elements = handlers._flatten_stack_for_preview(out, inv)
check("プリミティブが展開されている", len(elements) == N, f"{len(elements)} / {N}")

prim_data = []
for el in elements:
    prim_data.extend(handlers._build_prim_data_for_element(el, out.sdf_props))

check(
    "1プリミティブあたりの float 数が PRIM_TEX_FLOATS と一致する",
    len(prim_data) == handlers.PRIM_TEX_FLOATS * N,
    f"{len(prim_data)} floats / {handlers.PRIM_TEX_FLOATS} * {N} = {handlers.PRIM_TEX_FLOATS * N}",
)
check("stride の検算関数が通る", handlers._assert_prim_tex_stride(len(prim_data)))

# --- 3. GPUTexture へ渡す寸法とバッファ長が一致するか ----------------------
# ここが V16.2.0 の退行そのもの。prim_count は実プリミティブ数と等しく、
# 幅 * 高さ * 4 がバッファ長とぴったり合う必要がある。
prim_count = len(prim_data) // handlers.PRIM_TEX_FLOATS
check("prim_count が実際のプリミティブ数と一致する", prim_count == N, f"{prim_count} / {N}")
check(
    "テクスチャの必要長とバッファ長が一致する",
    handlers.PRIM_TEX_WIDTH * prim_count * 4 == len(prim_data),
    f"tex={handlers.PRIM_TEX_WIDTH * prim_count * 4} buf={len(prim_data)}",
)

# --- 4. 壊れた stride はガードで弾かれるか --------------------------------
check("半端な長さは検算で弾かれる", not handlers._assert_prim_tex_stride(len(prim_data) - 1))

print("\nRESULT: " + ("ALL PASS" if not fail else f"{len(fail)} FAILED: {fail}"), flush=True)
