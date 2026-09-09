# SDF.R - Blender Add-on
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Copyright (c) 2026 hinata_hugu (Replace '2024' with the current year if different)
# All Rights Reserved.


#
# =============================================================================
# DEVELOPMENT NOTES
# =============================================================================
#
# [English]
# This add-on, SDF.R, was developed with transparency through a collaboration 
# between myself (hinata_hugu), a human developer, and an AI:
#
# - DESIGN INTENT: All design principles, policies, and instructions were 
#   entirely driven by me. This add-on was developed to make SDF modeling 
#   in Blender as lightweight and intuitive as possible. 
#   By offloading the heavy lifting to a custom Rust-based GPU engine, 
#   it eliminates the need for complex Geometry Nodes setups. 
#   Real-time "Ghost Previews" via Blender's GPU module ensure a stress-free 
#   modeling experience. Currently in Beta, striving for further evolution.
#
# - ITERATIVE DEVELOPMENT: This is unmistakably an add-on created by me, 
#   refined through hundreds of cycles of coding, testing, debugging, 
#   and improvement.
#
# - RESPONSIBILITY: All debugging, user feedback, and support are handled 
#   exclusively by the human developer.
#
# - CODE FORMATTING: AI assisted with final code organization to improve 
#   readability. This benefits GPL users who wish to learn from this codebase. 
#   The Rust source code is also prepared for release upon request, 
#   honoring the spirit of free software.
#
# [Japanese]
# SDF.R is developed by hinata_hugu with AI-assisted organization and review.
# Design intent, release decisions, support, and responsibility remain with the
# human developer. The add-on aims to make SDF modeling in Blender lightweight,
# intuitive, and suitable for iterative creative work.
#
# -----------------------------------------------------------------------------
#
# Creator's Oath
#
# In the spirit of free software and the GNU GPL:
# May Blender forever remain free under the GPL!
# This addon guarantees all users the freedom to learn from,
# modify, and share this source code forever.
# Keep Blender and SDF.R open, inspectable, and modifiable under the GPL.
# =============================================================================

bl_info = {
    "name": "SDF.R",
    "author": "hinata_hugu",
    "version": (16, 2, 1),  # V16.2.1: async mesh results routed to their owning output
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > SDF-R",
    "description": "Next-gen SDF Modeling Tool with Professional Workflow",
    "category": "Mesh",
}

if "bpy" in locals():
    import importlib
    importlib.reload(constants)
    importlib.reload(properties)
    importlib.reload(operators)
    importlib.reload(ui)
    importlib.reload(handlers)
    importlib.reload(engine)
    importlib.reload(shader)
else:
    import bpy
    import os
    from . import constants
    from . import properties
    from . import operators
    from . import ui
    from . import handlers
    from . import engine
    from . import shader

from .engine import _update_preview
from bpy.app.handlers import persistent

_LAYOUT_FLAG_FILE = os.path.join(os.path.dirname(__file__), "SDF_DEBUG_LAYOUT.ON")
_LAYOUT_DEBUG_ENV = os.environ.get("SDF_DEBUG_LAYOUT", "").strip().lower() in {"1", "true", "yes", "on"}
_LAYOUT_DEBUG_ON = _LAYOUT_DEBUG_ENV or os.path.exists(_LAYOUT_FLAG_FILE)
print(f"SDF.R: Loader Marker V16.2.1 (__init__.py loaded from: {__file__})")
if _LAYOUT_DEBUG_ON:
    print(f"SDF.R: Layout Debug Switch = {_LAYOUT_DEBUG_ON} (env={_LAYOUT_DEBUG_ENV}, flag_file={os.path.exists(_LAYOUT_FLAG_FILE)})")


_draw_handler = None
# V16.2.1: register で仕掛けた bpy.app.timers のコールバック。unregister で取り消す。
_registered_timers = []
_gpu_init_finished = False
# V15.9.9.1: Stores deferred GPU/DC initialization diagnostics.
_gpu_init_error = None

classes = (
    properties.SDF_DeformItem,
    properties.SDF_StackItem,
    properties.SDF_SceneProperties,
    properties.SDF_ObjectProperties,
    operators.SDF_OT_add_primitive,
    operators.SDF_OT_toggle_display,
    operators.SDF_OT_move_to_sdf_collection,
    operators.SDF_OT_duplicate_collection,
    operators.SDF_OT_bake_mesh,
    operators.SDF_OT_setup_material,
    operators.SDF_OT_reset_material,
    operators.SDF_OT_apply_color_all,
    operators.SDF_OT_apply_material_all,
    operators.SDF_OT_generate_mesh,
    operators.SDF_OT_add_selected,
    operators.SDF_OT_make_output,
    operators.SDF_OT_add_tree,
    operators.SDF_OT_set_active_tree,
    operators.SDF_OT_stack_move,
    operators.SDF_OT_stack_remove,
    operators.SDF_OT_add_collection_divider,
    operators.SDF_OT_add_tree_ref,
    operators.SDF_OT_add_curve_sync,
    operators.SDF_OT_edit_curve_sync_target,
    operators.SDF_OT_select_stack_obj,
    operators.SDF_OT_use_previous_as_mask,
    operators.SDF_OT_match_math_field_axis_to_scale,
    operators.SDF_OT_setup_post_process,
    operators.SDF_OT_update_normals,
    operators.SDF_OT_finalize,
    operators.SDF_OT_all_clear,
    operators.SDF_OT_set_resolution_preset,
    operators.SDF_OT_switch_algo,
    operators.SDF_OT_deform_add,
    operators.SDF_OT_deform_remove,
    operators.SDF_OT_deform_move,
    ui.SDF_UL_stack_list,
    ui.SDF_UL_deform_list,
    ui.SDF_PT_main,
)


def update_result_visibility(self, context):
    """Toggle the generated SDF_Result mesh visibility."""
    from . import engine
    for obj in context.scene.objects:
        if getattr(obj, "sdf_props", None) and obj.sdf_props.is_output:
            obj.hide_viewport = not self.sdf_show_result
            obj.hide_render = not self.sdf_show_result
            
            # Force a mesh refresh when result display is enabled.
            if self.sdf_show_result:
                if obj.name in engine._last_state_hashes:
                    del engine._last_state_hashes[obj.name]
                engine.update_sdf_mesh(obj)

@persistent
def sdf_load_post_handler(dummy):
    """開いたファイルのセッション状態を、いまのエンジンの実状へ揃える。

    ここで扱うのはどれも「そのセッションのエンジンがどうなっているか」を表す値だが、
    置き場がシーンのプロパティなので .blend に保存され、ファイルを開くと蘇ってしまう。

    V16.2.1: is_gpu_ready — 保存時に True だったファイルを開くと、エンジンの初期化が
    終わっていなくてもパネルのガードが外れていた（コンソールに Compiling ... が
    流れている最中に操作できてしまう）。

    V16.2.1: dc_last_error — こちらも同じ性質だが同期されていなかった。DC が動かない
    環境で保存した .blend を正常な環境で開くと、パネルに
    「Dual Contouring (DC) unavailable → switch Algorithm to MC」の警告が残る。
    しかも engine 側は診断文字列が空でないときしか書き戻さないため、その後 DC が
    正常に動いても表示は自然回復しない。開いた時点のエンジンの実状で上書きする。

    V16.2.1: diagnostics_* — 実体はアドオンのインストール先に置くフラグファイルで、
    シーンのトグルはその写し。register 時に一度同期するだけなので、診断ONで保存した
    .blend を開くとトグルの見た目と実際のログ出力が食い違っていた。
    """
    try:
        perf_on = properties._diagnostic_flag_enabled(
            properties._DIAGNOSTIC_FLAGS["diagnostics_perf_log"])
        mesh_on = properties._diagnostic_flag_enabled(
            properties._DIAGNOSTIC_FLAGS["diagnostics_mesh_debug"])
        layout_on = properties._diagnostic_flag_enabled(
            properties._DIAGNOSTIC_FLAGS["diagnostics_layout_debug"])
        for scene in bpy.data.scenes:
            if not hasattr(scene, "sdf_scene_props"):
                continue
            props = scene.sdf_scene_props
            props.is_gpu_ready = bool(_gpu_init_finished)
            if _gpu_init_finished:
                # ウォームアップ済みなら、その結果（多くの場合は空文字列）で上書きする。
                # まだ終わっていない場合は init_checker が終了時に書くので触らない。
                props.dc_last_error = _gpu_init_error or ""
            props.diagnostics_perf_log = perf_on
            props.diagnostics_mesh_debug = mesh_on
            props.diagnostics_layout_debug = layout_on
    except Exception as exc:
        print(f"SDF.R: load_post session flag sync skipped: {exc}")


def update_primitives_visibility(self, context):
    """Switch source primitives between wire and bounds display."""
    # V16.2.1: 置き場は1つとは限らないので、全ツリーぶんを回す。
    display_mode = 'WIRE' if self.sdf_show_primitives else 'BOUNDS'
    for col in engine.iter_sdf_collections(context.scene):
        col.hide_viewport = False
        for obj in col.objects:
            obj.display_type = display_mode

def register():
    global _draw_handler, _gpu_init_finished
    _gpu_init_finished = False
    
    import bpy
    import os
    import threading
    import time
    from ._native import rust_gpu_sdf
    print("SDF.R: --- Initializing GPU Engine (V16.2.1) ---")
    
    cache_dir = os.path.join(bpy.utils.user_resource('DATAFILES'), "rust_gpu_sdf")
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, "shader_cache.bin")
    
    cache_data = None
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "rb") as f:
                cache_data = f.read()
        except Exception as e:
            print(f"SDF.R: Failed to load cache: {e}")
            
    if cache_data is None:
        print("SDF.R: No shader cache. This initial compilation may take a few minutes...")
    else:
        print(f"SDF.R: Shader cache found ({len(cache_data)} bytes).")

    def background_init():
        global _gpu_init_finished, _gpu_init_error
        start_time = time.time()
        print(f"SDF.R: --- Starting GPU Warming-up (V16.2.1) ---")
        try:
            # Initialize GPU engine in Rust.
            success = rust_gpu_sdf.init_gpu(cache_path)
            elapsed = time.time() - start_time
            if success:
                print(f"SDF.R: GPU Engine Ready! (Warming-up finished in {elapsed:.2f} seconds)")
            else:
                print(f"SDF.R: GPU Engine warming-up failed in {elapsed:.2f} seconds.")
            _gpu_init_error = rust_gpu_sdf.get_dc_last_error()
            _gpu_init_finished = True
        except BaseException as e:
            # NOTE: BaseException (not Exception) on purpose. Rust panics raised across
            # the PyO3 boundary (e.g. a wgpu validation panic from a stale/incompatible
            # pipeline cache) surface as pyo3_runtime.PanicException, which subclasses
            # BaseException, not Exception. Using `except Exception` here silently drops
            # those panics: the background thread dies without ever setting
            # _gpu_init_finished, and the sidebar panel is stuck on "Initializing..."
            # forever with no error shown.
            elapsed = time.time() - start_time
            print(f"SDF.R: GPU Engine initialization error after {elapsed:.2f}s: {e}")
            _gpu_init_error = str(e)

            if os.path.exists(cache_path):
                print("SDF.R: Removing potentially corrupted shader cache and retrying...")
                try:
                    os.remove(cache_path)
                    success = rust_gpu_sdf.init_gpu(cache_path)
                    elapsed_retry = time.time() - start_time - elapsed
                    if success:
                        print(f"SDF.R: GPU Engine Ready after retry! ({elapsed_retry:.2f} seconds)")
                        _gpu_init_error = rust_gpu_sdf.get_dc_last_error()
                    else:
                        print(f"SDF.R: GPU Engine warming-up failed after retry.")
                except BaseException as retry_e:
                    print(f"SDF.R: GPU Engine initialization error on retry: {retry_e}")
                    _gpu_init_error = str(retry_e)

            _gpu_init_finished = True

    def init_checker():
        """Check async GPU warm-up status and update scene flags."""
        global _gpu_init_finished, _gpu_init_error
        if not _gpu_init_finished:
            # V16.2.1: is_gpu_ready はシーンのプロパティなので .blend に保存される。
            # 前回のセッションで True になったファイルを開くと、エンジンがまだ
            # パイプラインをコンパイルしている最中でもパネルのガードが外れていた。
            # ウォームアップが終わるまでは毎回 False に落として打ち消す。
            try:
                for scene in bpy.data.scenes:
                    if hasattr(scene, "sdf_scene_props") and scene.sdf_scene_props.is_gpu_ready:
                        scene.sdf_scene_props.is_gpu_ready = False
            except Exception:
                pass
            return 0.1
        if _gpu_init_finished:
            try:
                scenes = list(bpy.data.scenes)
            except Exception as exc:
                print(f"SDF.R: GPU ready scene sync deferred: {exc}")
                return 0.2
            for scene in scenes:
                if hasattr(scene, "sdf_scene_props"):
                    scene.sdf_scene_props.is_gpu_ready = True
                    scene.sdf_scene_props.dc_last_error = _gpu_init_error or ""
            # Property changes made from a background timer don't trigger a UI
            # repaint on their own; without this the sidebar stays stuck showing
            # "Initializing..." until some unrelated redraw happens to fire.
            for window in bpy.context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()
            return None
        return 0.1
    def delayed_start():
        init_thread = threading.Thread(target=background_init, daemon=True)
        init_thread.start()
        bpy.app.timers.register(init_checker)
        return None
    # Delay start slightly so Blender UI setup can settle.
    bpy.app.timers.register(delayed_start, first_interval=0.5)
    # V16.2.1: unregister でタイマーを取り消せるよう控えておく。
    # 控えないと、ウォームアップ中にアドオンを無効化したとき init_checker が
    # 回り続ける（消えたプロパティを触るので、ガードが無ければ毎回エラーになる）。
    _registered_timers.extend([delayed_start, init_checker])
    print("SDF.R: Addon registered. Warming-up will start in 0.5s...")

    # 2. Register Blender classes
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Object.sdf_props = bpy.props.PointerProperty(type=properties.SDF_ObjectProperties)
    bpy.types.Scene.sdf_scene_props = bpy.props.PointerProperty(type=properties.SDF_SceneProperties)
    bpy.types.Scene.sdf_live_update = bpy.props.BoolProperty(name="Live Update", default=True)
    bpy.types.Scene.sdf_show_preview = bpy.props.BoolProperty(
        name="Show GPU Preview", default=True, update=_update_preview
    )
    bpy.types.Scene.sdf_show_result = bpy.props.BoolProperty(
        name="Show Result Mesh", default=True, update=update_result_visibility
    )
    bpy.types.Scene.sdf_show_primitives = bpy.props.BoolProperty(
        name="Show Source Primitives", default=True, update=update_primitives_visibility
    )
    bpy.app.timers.register(properties.sync_scene_diagnostic_flags, first_interval=0.1)
    _registered_timers.append(properties.sync_scene_diagnostic_flags)
    
    bpy.app.handlers.load_post.append(sdf_load_post_handler)
    bpy.app.handlers.depsgraph_update_post.append(handlers.sdf_depsgraph_handler)
    bpy.app.handlers.undo_post.append(handlers.sdf_undo_handler)
    bpy.app.handlers.redo_post.append(handlers.sdf_undo_handler)
    _draw_handler = bpy.types.SpaceView3D.draw_handler_add(
        handlers.draw_callback_3d, (None, None), 'WINDOW', 'POST_VIEW'
    )

def _unregister_timers():
    """register で仕掛けたタイマーを取り消す。

    bpy.app.timers はアドオンの有効/無効とは独立して動き続ける。ウォームアップ中に
    無効化されたときに init_checker が残ると、削除済みのシーンプロパティを
    参照しつづけることになる。まだ動いていないものを unregister すると例外に
    なるので、is_registered を見てから外す。
    """
    # engine 側のメッシュ監視タイマーも同じ理由で止める。
    # 次に有効化したときに二重登録しないよう、フラグも倒しておく。
    for fn in list(_registered_timers) + [engine.sdf_mesh_timer]:
        try:
            if bpy.app.timers.is_registered(fn):
                bpy.app.timers.unregister(fn)
        except Exception as exc:
            print(f"SDF.R: timer unregister skipped ({getattr(fn, '__name__', fn)}): {exc}")
    engine._is_timer_registered = False
    _registered_timers.clear()


def unregister():
    global _draw_handler
    _unregister_timers()
    if _draw_handler:
        bpy.types.SpaceView3D.draw_handler_remove(_draw_handler, 'WINDOW')
        _draw_handler = None
    
    if sdf_load_post_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(sdf_load_post_handler)
    if handlers.sdf_depsgraph_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(handlers.sdf_depsgraph_handler)
    if handlers.sdf_undo_handler in bpy.app.handlers.undo_post:
        bpy.app.handlers.undo_post.remove(handlers.sdf_undo_handler)
    if handlers.sdf_undo_handler in bpy.app.handlers.redo_post:
        bpy.app.handlers.redo_post.remove(handlers.sdf_undo_handler)
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    del bpy.types.Object.sdf_props
    del bpy.types.Scene.sdf_scene_props
    del bpy.types.Scene.sdf_live_update
    del bpy.types.Scene.sdf_show_preview
    del bpy.types.Scene.sdf_show_result
    del bpy.types.Scene.sdf_show_primitives

    handlers.clear_batch()
    shader.clear_shader()
