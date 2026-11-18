# プレビュー用 GLSL が実際にコンパイルできるか確認する（Mirror Blend 修正の構文確認）。
# GPU が要るのでバックグラウンド (-b) では動かない。実ウィンドウで起動して、
# タイマーでコンパイルだけ試して即終了する。
#   blender --factory-startup --python tests_V16.2.1/test_preview_shader_compiles.py -- <tree>
import bpy, sys, os
_ARG = sys.argv[-1]
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _tree import default_tree
TREE = _ARG if os.path.isdir(_ARG) else default_tree()
sys.path.insert(0, TREE)
import rust_gpu_sdf_addon as A; A.register()
from rust_gpu_sdf_addon import shader

def check():
    s = shader.get_shader()
    print("SHADER:", "COMPILED" if s is not None else "FAILED", flush=True)
    try:
        b = shader.get_blit_shader()
        print("BLIT:", "COMPILED" if b is not None else "FAILED", flush=True)
    except Exception as e:
        print("BLIT: ERROR", e, flush=True)
    bpy.ops.wm.quit_blender()
    return None

bpy.app.timers.register(check, first_interval=2.0)
