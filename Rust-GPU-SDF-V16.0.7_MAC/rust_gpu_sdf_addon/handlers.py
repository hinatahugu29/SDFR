import bpy
import gpu
import mathutils
import math
import time
import os
from bpy.app.handlers import persistent
from gpu_extras.batch import batch_for_shader
from .shader import get_shader
from .engine import update_sdf_mesh, sync_sdf_stack, get_layout_matrices
from .constants import _SHAPE_MAP, _fsq_coords, _fsq_indices, FIELD_TYPE_INDEX

_batch = None

# -------------------------------------------------------------------------
# V15.9.9.4: プレビュー描画の最適化用ステート
# -------------------------------------------------------------------------
# プリミティブデータが変化したら True。視点(カメラ)移動だけの場合は False のまま
# なので、GPUテクスチャ再構築をスキップしてキャッシュを再利用する。
_preview_dirty = True
# 直近で構築したプレビュー用テクスチャとメタ情報のキャッシュ
_cached_prim_tex = None
_cached_prim_count = 0
_cached_domain_size = 0.0
_cached_sym_mask = 0
_cached_base_steps = 0
# インタラクション検出用
_last_change_time = 0.0        # 最後にプリミティブが変化した時刻
_last_view_hash = None         # 直近フレームのビュー行列ハッシュ
_restore_timer_armed = False   # フル品質復帰タイマーが予約済みか

# 視点操作/トランスフォーム中に適用するレイマーチ最大ステップ数の上限。
# プリミティブが多いほど1ステップが重くなるため、操作中はステップを抑えて
# 応答性を確保し、操作が止まったらフル品質へ復帰させる。
_INTERACTIVE_STEP_CAP = 160
_CAMERA_MOVING_STEP_CAP = 64
_TRANSFORM_STEP_CAP = 128
_INTERACTION_IDLE_SEC = 0.2
_PERF_FLAG_FILE = os.path.join(os.path.dirname(__file__), "SDF_PERF_LOG.ON")
_PERF_LOGGING = (
    os.environ.get("SDF_PERF_LOG", "").strip().lower() in {"1", "true", "yes", "on"}
    or os.path.exists(_PERF_FLAG_FILE)
)

# Performance metrics variables
_perf_last_report_time = 0.0
_perf_call_count = 0
_perf_relevant_count = 0
_perf_accum_time = 0.0

# Preview drawing metrics
_perf_draw_last_report_time = 0.0
_perf_draw_call_count = 0
_perf_draw_rebuild_count = 0
_perf_draw_accum_time = 0.0


def _perf_log(msg):
    if _PERF_LOGGING:
        print(msg)

def set_perf_logging(enabled):
    """Apply preview/depsgraph performance logging without reloading handlers."""
    global _PERF_LOGGING
    _PERF_LOGGING = bool(enabled)



def is_transforming_active():
    """現在ユーザーが移動・回転・拡大縮小操作中（ドラッグ中）であるかを判定する"""
    try:
        op = bpy.context.active_operator
        if op and op.bl_idname in {"TRANSFORM_OT_translate", "TRANSFORM_OT_rotate", "TRANSFORM_OT_resize", "TRANSFORM_OT_tweak"}:
            return True
    except Exception:
        pass
    return False


def mark_preview_dirty():
    """プレビュー用プリミティブデータの再構築を要求する。

    トランスフォーム/プロパティ変更など、プレビュー見た目に影響する変化が
    起きたときに呼ぶ。視点移動だけのときは呼ばれないため、描画側はキャッシュ
    済みテクスチャを再利用できる。"""
    global _preview_dirty, _last_change_time
    _preview_dirty = True
    _last_change_time = time.time()


def _restore_preview_quality():
    """インタラクション終了後にフル品質でプレビューを1フレーム再描画させる。"""
    global _restore_timer_armed
    _restore_timer_armed = False
    try:
        wm = bpy.context.window_manager
        for w in wm.windows:
            for area in w.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
    except Exception:
        pass
    return None  # None を返してタイマーを解除

def _get_shape_extent(p_props):
    """プリミティブのシェイプ半径を計算する（ドメイン計算用）"""
    if not p_props or not p_props.is_primitive:
        return getattr(p_props, "radius", 1.0) if p_props else 1.0
    shape = p_props.shape_type
    if shape == 'torus': return p_props.p1 + p_props.p2
    elif shape in ('cylinder', 'capsule', 'hex_prism'): return max(p_props.p1, p_props.p2)
    elif shape == 'capped_cone': return max(p_props.p1, p_props.p2, p_props.p3)
    elif shape == 'pyramid': return max(p_props.p1, p_props.p2)
    elif shape == 'ngon_prism': return max(p_props.p1, p_props.p3)
    elif shape == 'rounded_box': return max(p_props.radius, 1.0 + p_props.p1)
    elif shape == 'ellipsoid': return max(p_props.p1, p_props.p2, p_props.p3)
    elif shape == 'rounded_cylinder': return max(p_props.p1, p_props.p3 + p_props.p2)
    elif shape == 'capped_torus': return p_props.p1 + p_props.p2
    elif shape == 'octahedron': return p_props.p1
    elif shape == 'cut_sphere': return p_props.radius
    elif shape == 'math_field': return max(p_props.p4, 0.1)
    else: return p_props.radius

def _get_layout_r(p_props):
    """レイアウト展開による追加半径を計算する"""
    layout_r = 0.0
    if not p_props: return layout_r
    if p_props.layout_use_mirror:
        layout_r = max(layout_r, abs(p_props.mirror_offset))
    if p_props.layout_use_radial or p_props.layout_use_spiral:
        layout_r = max(layout_r, abs(p_props.radial_radius))
    if p_props.layout_use_grid:
        gx = (p_props.grid_count_x - 1) * p_props.grid_spacing_x
        gy = (p_props.grid_count_y - 1) * p_props.grid_spacing_y
        gz = (p_props.grid_count_z - 1) * p_props.grid_spacing_z
        layout_r = max(layout_r, math.sqrt(gx * gx + gy * gy + gz * gz) * 0.5)
    if p_props.layout_use_jitter:
        layout_r = max(layout_r, abs(p_props.jitter_strength))
    return layout_r

def _compute_preview_domain_size(output_obj, o_props, inv_world_output, flat_elements):
    """展開済み要素リストからプレビュードメインサイズを計算する"""
    base_domain = o_props.domain_size * 2.0
    if not getattr(o_props, "auto_domain", False):
        return base_domain

    max_extent = 0.001
    for el in flat_elements:
        loc = el['loc']
        sc = el['scale']
        p_props = el['p_props']
        max_s = max(abs(sc.x), abs(sc.y), abs(sc.z))
        smoothness = getattr(p_props, "smoothness", 0.2) if p_props else 0.2
        noise_strength = getattr(p_props, "noise_strength", 0.0) if p_props else 0.0
        shape_extent = _get_shape_extent(p_props)
        prim_r = (max_s * shape_extent) + (smoothness + noise_strength) * max_s
        layout_r = _get_layout_r(p_props) if (p_props and p_props.is_primitive) else 0.0
        dist_from_origin = math.sqrt(loc.x * loc.x + loc.y * loc.y + loc.z * loc.z)
        max_extent = max(max_extent, dist_from_origin + layout_r + prim_r)

    auto_domain = max_extent * 2.4
    return max(base_domain, auto_domain)

def _build_prim_data_for_element(el, o_props):
    """展開済み要素辞書から64floatのテクスチャデータを構築して返す"""
    o = el['obj_orig']
    p_props = el['p_props']
    loc = el['loc']
    rot = el['rot']
    sc = el['scale']
    layer_id = float(el.get('layer_id', 0))

    if p_props and p_props.is_primitive:
        shape_type = _SHAPE_MAP.get(p_props.shape_type, 0.0)
        smoothness = p_props.smoothness
        op_type = float(int(p_props.operation))
        color = list(p_props.color)
        metallic = p_props.metallic
        roughness = p_props.roughness
        noise_strength = p_props.noise_strength
        noise_scale = p_props.noise_scale
    else:
        name_lower = o.name.lower()
        if 'sphere' in name_lower: shape_type = 0.0
        elif 'box' in name_lower or 'cube' in name_lower: shape_type = 1.0
        elif 'torus' in name_lower: shape_type = 2.0
        elif 'cylinder' in name_lower: shape_type = 3.0
        else: shape_type = 0.0
        smoothness = 0.5
        op_type = 0.0
        color = [1.0, 1.0, 1.0]
        metallic = 0.0
        roughness = 0.5
        noise_strength = 0.0
        noise_scale = 5.0

    sym_loc = [abs(loc.x) if o_props.sym_x else loc.x,
               abs(loc.y) if o_props.sym_y else loc.y,
               abs(loc.z) if o_props.sym_z else loc.z]

    # V12 Phase 2: Layout Data Stacking (16-slot Packing)
    if p_props and p_props.is_primitive:
        mode_flags = 0
        if p_props.layout_use_mirror: mode_flags |= 1
        if p_props.layout_use_radial: mode_flags |= 2
        if p_props.layout_use_spiral: mode_flags |= 4
        if p_props.layout_use_grid:   mode_flags |= 8
        if p_props.layout_use_jitter: mode_flags |= 32

        mirror_mask = (1 if p_props.mirror_x else 0) | (2 if p_props.mirror_y else 0) | (4 if p_props.mirror_z else 0)
        radial_axis = int(p_props.radial_axis)
        radial_count = max(1, p_props.radial_count)

        packed1 = float(mode_flags | (mirror_mask << 8) | (radial_count << 12) | (radial_axis << 20))
        grid_packed = float(p_props.grid_count_x + 100 * p_props.grid_count_y + 10000 * p_props.grid_count_z)

        ld1 = [packed1, p_props.mirror_offset, p_props.radial_radius, p_props.spiral_pitch]
        ld2 = [p_props.jitter_seed, p_props.jitter_strength, grid_packed, p_props.grid_spacing_x]
        ld3 = [p_props.grid_spacing_y, p_props.grid_spacing_z, p_props.instance_rot_x, p_props.instance_rot_y]
        ld4 = [p_props.instance_rot_z, p_props.step_rot_x, p_props.step_rot_y, p_props.step_rot_z]

        # --- V15: Deform Stack Packing ---
        _DEFORM_TYPE_MAP = {'ELONGATE': 1, 'BEND': 2, 'TWIST': 3, 'TAPER': 4}
        packed_meta = 0
        slot_params = [[0.0]*4, [0.0]*4, [0.0]*4, [0.0]*4]
        for si, d_item in enumerate(p_props.deform_stack):
            if si >= 4: break
            if not d_item.enabled: continue
            d_type = _DEFORM_TYPE_MAP.get(d_item.deform_type, 0)
            d_axis = int(d_item.axis)
            packed_meta |= (d_type | (d_axis << 4)) << (si * 6)
            if d_item.deform_type == 'ELONGATE':
                slot_params[si] = [d_item.elongate_x, d_item.elongate_y, d_item.elongate_z, 0.0]
            else:
                slot_params[si] = [d_item.factor, d_item.origin[0], d_item.origin[1], d_item.origin[2]]

        dd1 = [float(packed_meta), slot_params[0][0], slot_params[0][1], slot_params[0][2]]
        dd2 = [slot_params[0][3], slot_params[1][0], slot_params[1][1], slot_params[1][2]]
        dd3 = [slot_params[1][3], slot_params[2][0], slot_params[2][1], slot_params[2][2]]
        dd4 = [slot_params[2][3], slot_params[3][0], slot_params[3][1], slot_params[3][2]]
        
        blend_prof = float(int(p_props.blend_profile))
        cham_smooth = p_props.chamfer_smooth
    else:
        ld1 = [0.0] * 4
        ld2 = [0.0] * 4
        ld3 = [0.0] * 4
        ld4 = [0.0] * 4
        dd1 = [0.0] * 4
        dd2 = [0.0] * 4
        dd3 = [0.0] * 4
        dd4 = [0.0] * 4
        blend_prof = 0.0
        cham_smooth = 0.0

    data = []
    # 0: center_and_shape
    data.extend([sym_loc[0], sym_loc[1], sym_loc[2], shape_type])
    # 1: rotation
    data.extend([rot.x, rot.y, rot.z, rot.w])
    # 2: size_and_op
    radius = 0.0
    size = (sc.x, sc.y, sc.z)
    extra_p = [0.0, 0.0, 0.0, 0.0]
    gyroid_p = [0.0, 1.0, 1.0, 1.0]

    if p_props and p_props.is_primitive:
        radius = p_props.radius
        extra_p = [p_props.p1, p_props.p2, p_props.p3, p_props.p4]
        if p_props.shape_type == 'math_field':
            gyroid_p = [
                p_props.gyroid_phase,
                max(p_props.gyroid_axis_x, 0.05),
                max(p_props.gyroid_axis_y, 0.05),
                max(p_props.gyroid_axis_z, 0.05),
            ]
        if p_props.shape_type == 'ngon_prism':
            extra_p[1] = float(p_props.ngon_sides)
    else:
        if shape_type == 0.0: radius = sc.x
        elif shape_type == 2.0: radius = sc.z
        elif shape_type == 3.0: radius = sc.x

    data.extend([size[0], size[1], size[2], op_type])
    # 3: params [radius, smoothness, metallic, roughness]
    data.extend([radius, smoothness, metallic, roughness])
    # 4: noise_params [str, scale, r, g]
    data.extend([noise_strength, noise_scale, color[0], color[1]])
    # 5: color_b_and_extra [b, blend_profile, chamfer_smooth, layer_id]
    data.extend([color[2], blend_prof, cham_smooth, layer_id])
    # 6-9: layouts
    data.extend(ld1)
    data.extend(ld2)
    data.extend(ld3)
    data.extend(ld4)
    # 10: extra_params (V13)
    data.extend(extra_p)
    # 11-14: deform_data (V15)
    data.extend(dd1)
    data.extend(dd2)
    data.extend(dd3)
    data.extend(dd4)
    # 15: modifier_params (V16)
    if p_props and p_props.is_primitive:
        if p_props.shape_type == 'math_field':
            field_type_idx = float(FIELD_TYPE_INDEX.get(p_props.field_type, 0))
            data.extend([field_type_idx, p_props.shell_thickness, float(int(p_props.gyroid_mask_shape)), float(int(p_props.gyroid_boundary_mode))])
        else:
            data.extend([float(p_props.edge_profile), p_props.shell_thickness, p_props.edge_chamfer_smooth, p_props.edge_profile_size])
    else:
        data.extend([0.0, 0.0, 0.0, 0.0])
    # 16: gyroid_params [phase, axis_x, axis_y, axis_z]
    data.extend(gyroid_p)

    return data


def _flatten_stack_for_preview(output_obj, inv_world_output):
    """engine.pyのupdate_sdf_meshと同等のロジックでスタックを走査し、
    コレクション展開を適用した要素辞書のリストを返す（Ghost Preview用）"""
    o_props = output_obj.sdf_props
    working_group = []
    flat_elements = []
    next_layer_id = 1
    active_layer_id = 0

    for i, item in enumerate(o_props.sdf_stack):
        if not item.enabled:
            continue

        if item.item_type == 'COLLECTION':
            empty_obj = item.empty_ptr
            if not empty_obj:
                continue

            empty_props = getattr(empty_obj, "sdf_props", None)
            if not empty_props:
                continue

            layout_mats = get_layout_matrices(empty_props)
            P = empty_obj.matrix_world
            try:
                P_inv = P.inverted()
            except:
                P_inv = mathutils.Matrix.Identity(4)

            expanded_group = []
            for element in working_group:
                C = element['matrix_world']
                L = P_inv @ C
                for M in layout_mats:
                    C_new = P @ M @ L
                    local_mat = inv_world_output @ C_new
                    loc, rot, scale = local_mat.decompose()
                    copied_el = element.copy()
                    copied_el['matrix_world'] = C_new.copy()
                    copied_el['loc'] = loc
                    copied_el['rot'] = rot
                    copied_el['scale'] = scale
                    expanded_group.append(copied_el)

            if item.is_layer_boundary:
                flat_elements.extend(working_group)
                working_group = []
                active_layer_id = next_layer_id
                next_layer_id += 1
            elif item.start_new_group:
                active_layer_id = 0
                flat_elements.extend(expanded_group)
                working_group = []
            else:
                active_layer_id = 0
                working_group = expanded_group

        else:
            # プリミティブ
            obj_orig = item.object_ptr
            if not obj_orig:
                continue
            if obj_orig.name == output_obj.name:
                continue
            if o_props.use_solo and i > o_props.sdf_stack_index:
                break

            p_props = getattr(obj_orig, "sdf_props", None)
            local_mat = inv_world_output @ obj_orig.matrix_world
            loc, rot, scale = local_mat.decompose()

            element = {
                'obj_orig': obj_orig,
                'matrix_world': obj_orig.matrix_world.copy(),
                'p_props': p_props,
                'loc': loc,
                'rot': rot,
                'scale': scale,
                'layer_id': active_layer_id
            }
            working_group.append(element)

    # ループ後の残りを追加
    flat_elements.extend(working_group)
    return flat_elements


def _draw_callback_3d_impl(self, context):
    global _batch, _preview_dirty
    global _cached_prim_tex, _cached_prim_count, _cached_domain_size
    global _cached_sym_mask, _cached_base_steps
    global _last_view_hash, _restore_timer_armed

    if context is None: context = bpy.context
    try:
        scene = context.scene
        if not scene.sdf_live_update or not getattr(scene, "sdf_show_preview", True):
            return False
    except Exception:
        return False
    shader = get_shader()
    if not shader: return False

    rv3d = context.region_data
    if not rv3d: return False

    output_obj = None
    target_col = None
    for o in scene.objects:
        props = getattr(o, "sdf_props", None)
        if props and props.is_output:
            output_obj = o
            target_col = props.target_collection
            break

    if not output_obj or not target_col: return False

    inv_world_output = output_obj.matrix_world.inverted()
    o_props = output_obj.sdf_props

    rebuilt = False
    need_rebuild = _preview_dirty or _cached_prim_tex is None
    if need_rebuild:
        rebuilt = True
        # V7: スタック順序に従う
        sync_sdf_stack(output_obj)

        # V15.9.8.1: コレクション展開対応 — engine.pyと同等のフラット展開
        flat_elements = _flatten_stack_for_preview(output_obj, inv_world_output)

        prim_data = []
        for el in flat_elements:
            prim_data.extend(_build_prim_data_for_element(el, o_props))

        if not prim_data:
            _cached_prim_tex = None
            return False

        # V16.0.4: 17 pixels per primitive (68 floats)
        prim_count = len(prim_data) // 68
        data_buf = gpu.types.Buffer('FLOAT', len(prim_data), prim_data)
        prim_tex = gpu.types.GPUTexture((17, prim_count), format='RGBA32F', data=data_buf)

        domain_size = _compute_preview_domain_size(output_obj, o_props, inv_world_output, flat_elements)

        # 描画品質（ステップ数）の決定
        q_map = {'LOW': 128, 'MID': 256, 'HIGH': 512}
        base_steps = q_map.get(o_props.preview_quality, 256)
        auto_steps = int(domain_size * 24.0)
        base_steps = max(base_steps, min(auto_steps, 2048))

        sym_mask = (1 if o_props.sym_x else 0) | \
                   (2 if o_props.sym_y else 0) | \
                   (4 if o_props.sym_z else 0)

        _cached_prim_tex = prim_tex
        _cached_prim_count = prim_count
        _cached_domain_size = domain_size
        _cached_base_steps = base_steps
        _cached_sym_mask = sym_mask
        _preview_dirty = False

    if _cached_prim_tex is None:
        return False

    # --- V15.9.9.4: インタラクション中はレイマーチのステップ数を抑える ---
    # 視点操作(orbit/pan/zoom は depsgraph を発火しない)はビュー行列の変化で、
    # トランスフォーム/編集は直近の変更時刻で検出する。
    now = time.time()
    try:
        pm = rv3d.perspective_matrix
        view_hash = hash(tuple(round(v, 3) for row in pm for v in row))
    except Exception:
        view_hash = None
    view_moving = (view_hash is not None and view_hash != _last_view_hash)
    _last_view_hash = view_hash
    interacting = view_moving or ((now - _last_change_time) < _INTERACTION_IDLE_SEC)

    max_steps = _cached_base_steps
    if interacting:
        if view_moving:
            max_steps = min(max_steps, _CAMERA_MOVING_STEP_CAP)
        else:
            max_steps = min(max_steps, _TRANSFORM_STEP_CAP)
            
        # 操作が止まった後にフル品質で1フレーム描き直すためのタイマーを予約
        if not _restore_timer_armed:
            _restore_timer_armed = True
            try:
                bpy.app.timers.register(_restore_preview_quality,
                                        first_interval=_INTERACTION_IDLE_SEC + 0.02)
            except Exception:
                _restore_timer_armed = False

    if _batch is None:
        _batch = batch_for_shader(shader, 'TRIS', {"pos": _fsq_coords}, indices=_fsq_indices)

    inv_proj_view_local = inv_world_output @ rv3d.perspective_matrix.inverted()

    gpu.state.blend_set('ALPHA')
    gpu.state.depth_test_set('ALWAYS')
    gpu.state.face_culling_set('NONE')
    shader.bind()
    try:
        shader.uniform_float("invProjViewLocal", inv_proj_view_local)
        shader.uniform_float("domainSize", _cached_domain_size)
        shader.uniform_int("primCount", _cached_prim_count)
        shader.uniform_int("symmetryFlags", _cached_sym_mask)
        shader.uniform_int("maxSteps", max_steps)
        shader.uniform_sampler("primTex", _cached_prim_tex)
        _batch.draw(shader)
    except Exception as e:
        print(f"SDF Draw Error: {e}")
        import traceback; traceback.print_exc()
    gpu.state.blend_set('NONE')
    gpu.state.depth_test_set('LESS_EQUAL')
    gpu.state.face_culling_set('BACK')
    return rebuilt

def draw_callback_3d(self, context):
    """ビューポートにレイマーチングオーバーレイを描画（プロファイララッパー）"""
    global _perf_draw_last_report_time, _perf_draw_call_count, _perf_draw_rebuild_count, _perf_draw_accum_time
    if not _PERF_LOGGING:
        _draw_callback_3d_impl(self, context)
        return

    import time
    t_start = time.perf_counter()
    _perf_draw_call_count += 1

    try:
        rebuilt = _draw_callback_3d_impl(self, context)
        if rebuilt:
            _perf_draw_rebuild_count += 1
    finally:
        t_end = time.perf_counter()
        _perf_draw_accum_time += (t_end - t_start)

        now = time.time()
        if now - _perf_draw_last_report_time >= 1.0:
            avg_time = (_perf_draw_accum_time / _perf_draw_call_count) * 1000.0 if _perf_draw_call_count > 0 else 0.0
            _perf_log(f"[SDF-PERF] Preview Draw: {_perf_draw_call_count} FPS (avg duration: {avg_time:.3f} ms), texture rebuilds: {_perf_draw_rebuild_count}")
            _perf_draw_last_report_time = now
            _perf_draw_call_count = 0
            _perf_draw_rebuild_count = 0
            _perf_draw_accum_time = 0.0

def _sync_output_stacks_from_collection(scene):
    """Keep SDF stack UI in sync when objects are deleted with Blender shortcuts."""
    from . import engine
    changed = False
    for obj in list(scene.objects):
        props = getattr(obj.original if hasattr(obj, "original") else obj, "sdf_props", None)
        if not props or not props.is_output or not props.target_collection:
            continue

        col = props.target_collection
        col_names = {col_obj.name for col_obj in col.objects if col_obj.name != obj.name}
        stack_names = set()
        stale = False
        for item in props.sdf_stack:
            if item.object_ptr:
                item.obj_name = item.object_ptr.name
                stack_names.add(item.obj_name)
                if item.obj_name not in col_names:
                    stale = True
            elif item.obj_name:
                stale = True

        if stale or col_names != stack_names:
            before_len = len(props.sdf_stack)
            engine.sync_sdf_stack(obj)
            try:
                engine.sync_sdf_parents(obj)
            except Exception as exc:
                print(f"SDF.R stack parent sync after delete failed: {exc}")
            engine._last_state_hashes.pop(obj.name, None)
            changed = True
            _perf_log(
                f"[SDF-PERF] stack synced from collection: {obj.name} "
                f"({before_len}->{len(props.sdf_stack)})"
            )
    if changed:
        mark_preview_dirty()
    return changed

def _sdf_depsgraph_handler_impl(scene, depsgraph):
    from . import engine
    if getattr(engine, "_in_update", False): return
    if getattr(engine, "_duplicate_cooldown", False): return
    if getattr(engine, "_appearance_update_cooldown", False): return

    # 1. 選択状態の同期 (Viewport -> UI List)
    # これは Live Update の ON/OFF に関わらず実行する
    active_obj = bpy.context.active_object
    if active_obj:
        active_orig = active_obj.original if hasattr(active_obj, "original") else active_obj
        p_active = getattr(active_orig, "sdf_props", None)
        col_sdf = bpy.data.collections.get("SDF_Collection")
        is_sdf_related = (
            (p_active and (p_active.is_primitive or p_active.is_output)) or
            (col_sdf and active_orig.name in col_sdf.objects)
        )
        if is_sdf_related:
            for obj in scene.objects:
                props = getattr(obj.original if hasattr(obj, "original") else obj, "sdf_props", None)
                if props and props.is_output:
                    for i, item in enumerate(props.sdf_stack):
                        if item.object_ptr and item.object_ptr.name == active_orig.name:
                            if props.sdf_stack_index != i:
                                props.sdf_stack_index = i
                            break

    # 2. メッシュの更新判定 (Live Update が ON の場合のみ)
    stack_changed = _sync_output_stacks_from_collection(scene)
    if not scene.sdf_live_update: return

    is_relevant = stack_changed
    for update in depsgraph.updates:
        id_orig = update.id.original if hasattr(update.id, "original") else update.id
        if isinstance(id_orig, bpy.types.Object):
            # 更新されたオブジェクトがスタック内の仕切りEmptyであるか確認
            is_empty_divider = id_orig.name in engine._cached_divider_names

            p = getattr(id_orig, "sdf_props", None)
            if p and (p.is_primitive or (p.is_output and update.is_updated_transform) or is_empty_divider):
                is_relevant = True
            if not is_relevant:
                for o in scene.objects:
                    out_p = getattr(o.original, "sdf_props", None)
                    if out_p and out_p.is_output and out_p.target_collection:
                        if id_orig.name in out_p.target_collection.objects:
                            is_relevant = True; break
        if is_relevant: break

    if is_relevant:
        global _perf_relevant_count
        if _PERF_LOGGING:
            _perf_relevant_count += 1
        
        # V15.9.9.4: プレビュー用テクスチャの再構築を要求（視点移動では呼ばれない）
        mark_preview_dirty()
        
        # --- V15.9.9.5: トランスフォーム操作中は重いメッシュ同期・生成をスキップ ---
        if is_transforming_active():
            return

        sdf_depsgraph_handler._is_running = True
        try:
            # メッシュの更新
            t_mesh_start = time.perf_counter() if _PERF_LOGGING else 0.0
            for obj_orig in scene.objects:
                props = getattr(obj_orig.original, "sdf_props", None)
                if props and props.is_output and obj_orig.mode == 'OBJECT':
                    update_sdf_mesh(obj_orig, depsgraph=depsgraph)
            # 実際にメッシュ更新が走った時だけ瞬時値をログ出力
            if _PERF_LOGGING:
                _perf_log(f"[SDF-PERF] update_sdf_mesh processed in {(time.perf_counter() - t_mesh_start)*1000.0:.2f} ms")
        except Exception as e:
            print(f"SDF Handler Error: {e}")
        finally:
            sdf_depsgraph_handler._is_running = False

@persistent
def sdf_depsgraph_handler(scene, depsgraph):
    global _perf_last_report_time, _perf_call_count, _perf_relevant_count, _perf_accum_time
    if getattr(sdf_depsgraph_handler, "_is_running", False): return
    if not _PERF_LOGGING:
        _sdf_depsgraph_handler_impl(scene, depsgraph)
        return
    
    import time
    t_start = time.perf_counter()
    _perf_call_count += 1
    
    try:
        _sdf_depsgraph_handler_impl(scene, depsgraph)
    finally:
        t_end = time.perf_counter()
        _perf_accum_time += (t_end - t_start)
        
        now = time.time()
        if now - _perf_last_report_time >= 1.0:
            avg_time = (_perf_accum_time / _perf_call_count) * 1000.0 if _perf_call_count > 0 else 0.0
            _perf_log(f"[SDF-PERF] Depsgraph Calls: {_perf_call_count} Hz (avg duration: {avg_time:.3f} ms), relevant triggers: {_perf_relevant_count}")
            _perf_last_report_time = now
            _perf_call_count = 0
            _perf_relevant_count = 0
            _perf_accum_time = 0.0

def sdf_undo_handler(scene):
    """Undo/Redo 時に状態ハッシュキャッシュをクリアし、再計算を強制する"""
    from . import engine
    engine._last_state_hashes.clear()
    _sync_output_stacks_from_collection(scene)
    mark_preview_dirty()
    # V15.9.9.4: プレビューキャッシュも無効化
    mark_preview_dirty()
    # 必要に応じて即座に更新をトリガー
    for obj in scene.objects:
        if getattr(obj, "sdf_props", None) and obj.sdf_props.is_output:
            engine.update_sdf_mesh(obj)

def clear_batch():
    global _batch, _cached_prim_tex
    _batch = None
    # V15.9.9.4: プレビューキャッシュも破棄して次回描画で再構築させる
    _cached_prim_tex = None
    mark_preview_dirty()
