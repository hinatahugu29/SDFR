"""セッション状態のプロパティが、ファイルを開いたときに実状へ揃うかを見る。

is_gpu_ready / dc_last_error / diagnostics_* はどれも「いまのエンジンがどうか」を
表す値だが、置き場がシーンのプロパティなので .blend に保存され、開くと蘇る。
特に dc_last_error は、DC が動かない環境で保存したファイルを正常な環境で開くと
「DC unavailable → MC に切り替えて」という誤警告が残り、engine 側が空文字列を
書き戻さないため自然回復しない。
"""
import bpy, sys, os, tempfile

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


blend = os.path.join(tempfile.mkdtemp(), "saved_with_error.blend")

# --- エラーを抱えたまま保存されたファイルを作る ---------------------------
p = bpy.context.scene.sdf_scene_props
p.is_gpu_ready = True
p.dc_last_error = "DC pipeline compile failed on the other machine"
bpy.ops.wm.save_as_mainfile(filepath=blend)
check("前提: エラー入りで保存した", True, blend)

# --- 正常な（ウォームアップ済みでエラーの無い）セッションで開き直す --------
A._gpu_init_finished = True
A._gpu_init_error = None
bpy.ops.wm.open_mainfile(filepath=blend)

p = bpy.context.scene.sdf_scene_props
check("dc_last_error が実状で上書きされる", p.dc_last_error == "", f"got={p.dc_last_error!r}")
check("is_gpu_ready が実状に揃う", p.is_gpu_ready is True, f"got={p.is_gpu_ready}")

# --- ウォームアップ未完了なら、パネルのガードは閉じたままになる -----------
A._gpu_init_finished = False
bpy.ops.wm.open_mainfile(filepath=blend)
p = bpy.context.scene.sdf_scene_props
check("ウォームアップ前は is_gpu_ready が False に落ちる", p.is_gpu_ready is False, f"got={p.is_gpu_ready}")
check("ウォームアップ前は dc_last_error を触らない（保存値のまま）",
      p.dc_last_error != "", f"got={p.dc_last_error!r}")

# --- 診断トグルはフラグファイルの実状に従う -------------------------------
A._gpu_init_finished = True
flag_on = properties._diagnostic_flag_enabled(properties._DIAGNOSTIC_FLAGS["diagnostics_perf_log"])
bpy.context.scene.sdf_scene_props.diagnostics_perf_log = not flag_on
bpy.ops.wm.open_mainfile(filepath=blend)
p = bpy.context.scene.sdf_scene_props
# open 後はフラグファイルの実状（この時点の flag_on）に揃っているはず
check("diagnostics トグルがフラグファイルの実状に揃う",
      p.diagnostics_perf_log == properties._diagnostic_flag_enabled(
          properties._DIAGNOSTIC_FLAGS["diagnostics_perf_log"]),
      f"toggle={p.diagnostics_perf_log}")

print("\nRESULT: " + ("ALL PASS" if not fail else f"{len(fail)} FAILED: {fail}"), flush=True)
