import bpy
import gpu
import mathutils
import math
import time
import os
from bpy.app.handlers import persistent
from gpu_extras.batch import batch_for_shader
from .shader import get_shader, get_blit_shader
from .engine import update_sdf_mesh, sync_sdf_stack, get_layout_matrices, _curve_polylines, _resolve_curve_sync_target
from .constants import _SHAPE_MAP, _fsq_coords, _fsq_indices, FIELD_TYPE_INDEX, PROFILE_2D_INDEX

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
# Curve Sync のガイド線（レイマーチ非対応の軽量プレビュー）。None=未計算、[]=計算済みで0本
_cached_curve_guides = None
_guide_shader = None
# V16.1.1: 操作中の低解像度レンダリング用オフスクリーンと、それを画面へ貼るためのシェーダ
# オフスクリーンはサイズごとに持つ。3Dビューを分割していると各ビューポートの
# サイズが異なるため、1個だけ持つと交互の描画で毎フレーム作り直しになる。
_offscreens = {}               # {(width, height): GPUOffScreen}
_MAX_OFFSCREENS = 4            # 分割数の実用上限。超えたら古いものから捨てる
_blit_shader = None
_blit_batch = None
# インタラクション検出用
_last_change_time = 0.0        # 最後にプリミティブが変化した時刻
# 直近フレームのビュー行列ハッシュ。3Dビューを複数開いていると各ビューポートで
# ビュー行列が異なるため、リージョンごとに保持する。1個の変数で共有すると、
# 描画が別ビューポートへ移るたびにハッシュが変わり、静止中でも「視点移動中」と
# 誤判定されて低解像度描画のままになる。
_last_view_hashes = {}         # {region_pointer: view_hash}
_restore_timer_armed = False   # フル品質復帰タイマーが予約済みか

# 視点操作/トランスフォーム中に適用するレイマーチ最大ステップ数の上限。
# プリミティブが多いほど1ステップが重くなるため、操作中はステップを抑えて
# 応答性を確保し、操作が止まったらフル品質へ復帰させる。
_INTERACTIVE_STEP_CAP = 160
_CAMERA_MOVING_STEP_CAP = 64
_TRANSFORM_STEP_CAP = 128
_INTERACTION_IDLE_SEC = 0.2

# V16.1.1: 操作中にレイマーチを描く解像度の倍率。
# レイマーチのコストは「ピクセル数 × ステップ数 × プリミティブ数」で決まるため、
# ピクセル数を落とすのはシーンの複雑さに関係なく効く。0.5 なら画素数は 1/4 になる。
# 操作をやめた瞬間にフル解像度で描き直されるので、静止画の品質は変わらない。
_CAMERA_MOVING_RES_SCALE = 0.5
_TRANSFORM_RES_SCALE = 0.65
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
    elif shape == 'extrude': return max(p_props.p1, p_props.p2, p_props.extrude_depth)
    elif shape == 'lathe': return p_props.lathe_offset + max(p_props.p1, p_props.p2)
    elif shape == 'bezier_curve':
        b_dist = math.sqrt(p_props.bezier_pt_b[0]**2 + p_props.bezier_pt_b[1]**2 + p_props.bezier_pt_b[2]**2)
        c_dist = math.sqrt(p_props.bezier_pt_c[0]**2 + p_props.bezier_pt_c[1]**2 + p_props.bezier_pt_c[2]**2)
        return max(b_dist, c_dist) + max(p_props.bezier_start_radius, p_props.bezier_end_radius)
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
        elif p_props.shape_type == 'extrude':
            extra_p = [p_props.p1, p_props.p2, p_props.extrude_depth, p_props.profile_corner_radius]
        elif p_props.shape_type == 'lathe':
            extra_p = [p_props.p1, p_props.p2, p_props.lathe_offset, p_props.profile_corner_radius]
        elif p_props.shape_type == 'bezier_curve':
            extra_p = [p_props.bezier_pt_b[0], p_props.bezier_pt_b[1], p_props.bezier_pt_b[2], p_props.bezier_start_radius]
            gyroid_p = [p_props.bezier_pt_c[0], p_props.bezier_pt_c[1], p_props.bezier_pt_c[2], p_props.bezier_end_radius]
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
        elif p_props.shape_type in ('extrude', 'lathe'):
            profile_idx = float(PROFILE_2D_INDEX.get(p_props.profile_2d_type, 0))
            data.extend([profile_idx, p_props.shell_thickness, p_props.extrude_chamfer, p_props.edge_profile_size])
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

        elif item.item_type == 'CURVE_SYNC':
            # V16.1.1: レイマーチは総当たり評価でプリミティブ数に比例して重くなるため、
            # Curve Sync はここでは何もせず対象外にする。軽量なガイド線として
            # 別途 _collect_curve_sync_guides() / _draw_curve_sync_guides() で描画する
            if o_props.use_solo and i > o_props.sdf_stack_index:
                break
            continue

        else:
            # プリミティブ
            # Solo判定は他の早期 continue より先に行う（engine.py 側と挙動を揃える）
            if o_props.use_solo and i > o_props.sdf_stack_index:
                break
            obj_orig = item.object_ptr
            if not obj_orig:
                continue
            if obj_orig.name == output_obj.name:
                continue

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


def _collect_curve_sync_guides(output_obj):
    """CURVE_SYNC アイテムのカーブ中心線を、軽量プレビュー用のワールド座標ポリライン
    一覧として集める。レイマーチ（プリミティブ総当たり評価）には乗せず、単純な線として
    描画することでプレビューの負荷を増やさないようにする（確定メッシュは通常通り正確）。
    戻り値: [(world_points: list[Vector], color: (r,g,b,a)), ...]"""
    o_props = output_obj.sdf_props
    guides = []
    for i, item in enumerate(o_props.sdf_stack):
        if not item.enabled or item.item_type != 'CURVE_SYNC':
            continue
        if o_props.use_solo and i > o_props.sdf_stack_index:
            break
        stack_obj = item.object_ptr
        c_obj_orig = _resolve_curve_sync_target(stack_obj)
        if not c_obj_orig:
            continue
        cp = getattr(stack_obj, "sdf_props", None)
        # ガイド線なので分割数は粗くてよい（重さの原因を再現しないよう上限を掛ける）
        subdiv = max(2, min(6, cp.curve_sample_resolution if cp else 16))
        color = tuple(cp.color) + (1.0,) if cp else (0.3, 0.8, 1.0, 1.0)
        try:
            c_mat = c_obj_orig.matrix_world
            # allow_to_mesh=False: この関数は描画コールバックから呼ばれるため、
            # to_mesh()（IDデータへの書き込み）を踏まないようにする。NURBS は
            # 制御点直結の近似になるが、ガイド線用途なら十分
            for pts in _curve_polylines(c_obj_orig, subdiv, allow_to_mesh=False):
                if len(pts) < 2:
                    continue
                guides.append(([c_mat @ p for p in pts], color))
        except Exception:
            pass
    return guides


def _draw_curve_sync_guides(guides, line_width=3.0):
    """_collect_curve_sync_guides() の結果を、単純なラインとして描画する。
    line_width は見た目だけの調整値で、確定メッシュには一切影響しない
    （GPUのライン幅指定のみなのでコストはほぼ無視できる）。"""
    global _guide_shader
    if not guides:
        return
    if _guide_shader is None:
        try:
            _guide_shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        except Exception:
            return

    gpu.state.blend_set('ALPHA')
    gpu.state.depth_test_set('LESS_EQUAL')
    gpu.state.line_width_set(max(1.0, line_width))
    _guide_shader.bind()
    try:
        for world_pts, color in guides:
            try:
                batch = batch_for_shader(_guide_shader, 'LINE_STRIP', {"pos": [tuple(p) for p in world_pts]})
                _guide_shader.uniform_float("color", color)
                batch.draw(_guide_shader)
            except Exception:
                pass
    finally:
        gpu.state.line_width_set(1.0)
        gpu.state.blend_set('NONE')


def _get_offscreen(width, height):
    """低解像度レンダリング用のオフスクリーンを取得する。

    サイズごとにキャッシュするので、3Dビューを分割していて各ビューポートの
    解像度が違っても作り直しは起きない。数が増えすぎたら古いものから解放する。
    """
    key = (width, height)
    off = _offscreens.get(key)
    if off is not None:
        return off

    if len(_offscreens) >= _MAX_OFFSCREENS:
        old_key = next(iter(_offscreens))
        old = _offscreens.pop(old_key)
        try:
            old.free()
        except Exception:
            pass

    try:
        off = gpu.types.GPUOffScreen(width, height)
    except Exception as exc:
        print(f"SDF Preview: offscreen creation failed ({width}x{height}): {exc}")
        return None
    _offscreens[key] = off
    return off


def _get_blit():
    """オフスクリーンを画面全体へ貼り付けるためのシェーダとバッチ。

    組み込みの 'IMAGE' シェーダは ModelViewProjectionMatrix を掛けてしまい、
    POST_VIEW ハンドラ内では画面全体ではなく3D空間内の小さな板として描かれる。
    そのため NDC をそのまま出力する専用シェーダ（shader.get_blit_shader）を使う。
    頂点はレイマーチ本体と同じフルスクリーンクアッドを流用する。
    """
    global _blit_shader, _blit_batch
    if _blit_shader is None:
        _blit_shader = get_blit_shader()
        if _blit_shader is None:
            return None, None
    if _blit_batch is None:
        _blit_batch = batch_for_shader(
            _blit_shader, 'TRIS', {"pos": _fsq_coords}, indices=_fsq_indices
        )
    return _blit_shader, _blit_batch


def _draw_raymarch(shader, uniforms):
    """レイマーチのフルスクリーンクアッドを、現在のフレームバッファへ描く。"""
    global _batch
    if _batch is None:
        _batch = batch_for_shader(shader, 'TRIS', {"pos": _fsq_coords}, indices=_fsq_indices)
    shader.bind()
    shader.uniform_float("invProjViewLocal", uniforms["invProjViewLocal"])
    shader.uniform_float("domainSize", uniforms["domainSize"])
    shader.uniform_int("primCount", uniforms["primCount"])
    shader.uniform_int("symmetryFlags", uniforms["symmetryFlags"])
    shader.uniform_int("maxSteps", uniforms["maxSteps"])
    shader.uniform_int("fastNormal", uniforms["fastNormal"])
    shader.uniform_sampler("primTex", uniforms["primTex"])
    _batch.draw(shader)


def _draw_raymarch_scaled(context, shader, uniforms, scale):
    """レイマーチを低解像度のオフスクリーンへ描き、拡大して画面へ貼る。
    成功したら True、オフスクリーンが使えなければ False（呼び出し側で通常描画へフォールバック）。"""
    region = getattr(context, "region", None)
    if region is None:
        return False
    rw, rh = int(region.width), int(region.height)
    if rw <= 0 or rh <= 0:
        return False
    w = max(16, int(rw * scale))
    h = max(16, int(rh * scale))
    # 縮小しても意味がないほど小さいビューポートでは通常描画に任せる
    if w >= rw or h >= rh:
        return False

    off = _get_offscreen(w, h)
    if off is None:
        return False
    blit_shader, blit_batch = _get_blit()
    if blit_shader is None:
        return False

    try:
        with off.bind():
            fb = gpu.state.active_framebuffer_get()
            fb.clear(color=(0.0, 0.0, 0.0, 0.0))
            gpu.state.blend_set('ALPHA')
            gpu.state.depth_test_set('ALWAYS')
            gpu.state.face_culling_set('NONE')
            _draw_raymarch(shader, uniforms)
    except Exception as exc:
        print(f"SDF Preview: offscreen render failed, falling back: {exc}")
        return False

    # 画面へ拡大転送
    gpu.state.blend_set('ALPHA')
    gpu.state.depth_test_set('ALWAYS')
    gpu.state.face_culling_set('NONE')
    blit_shader.bind()
    blit_shader.uniform_sampler("image", off.texture_color)
    blit_batch.draw(blit_shader)
    return True


def _draw_callback_3d_impl(self, context):
    global _batch, _preview_dirty
    global _cached_prim_tex, _cached_prim_count, _cached_domain_size
    global _cached_sym_mask, _cached_base_steps, _cached_curve_guides
    global _restore_timer_armed

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
    need_rebuild = _preview_dirty or _cached_prim_tex is None or _cached_curve_guides is None
    if need_rebuild:
        rebuilt = True
        # V7: スタック順序に従う
        sync_sdf_stack(output_obj)

        # V15.9.8.1: コレクション展開対応 — engine.pyと同等のフラット展開
        flat_elements = _flatten_stack_for_preview(output_obj, inv_world_output)
        # V16.1.1: Curve Sync はレイマーチに乗せず、軽量なガイド線として別途集める
        _cached_curve_guides = _collect_curve_sync_guides(output_obj)

        prim_data = []
        for el in flat_elements:
            prim_data.extend(_build_prim_data_for_element(el, o_props))

        if not prim_data:
            _cached_prim_tex = None
        else:
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

    # Curve Sync ガイド線は、レイマーチ用プリミティブが1つも無くても独立して描画する
    _draw_curve_sync_guides(_cached_curve_guides, line_width=getattr(o_props, "curve_sync_guide_width", 3.0))

    if _cached_prim_tex is None:
        return rebuilt

    # --- V15.9.9.4: インタラクション中はレイマーチのステップ数を抑える ---
    # 視点操作(orbit/pan/zoom は depsgraph を発火しない)はビュー行列の変化で、
    # トランスフォーム/編集は直近の変更時刻で検出する。
    now = time.time()
    try:
        pm = rv3d.perspective_matrix
        view_hash = hash(tuple(round(v, 3) for row in pm for v in row))
    except Exception:
        view_hash = None
    # V16.1.1: 前回ハッシュはリージョン単位で比較する。3Dビューを分割していると
    # ビューポートごとにビュー行列が違うので、1個の変数で共有すると描画が別の
    # ビューポートへ移るたびに「視点移動中」と誤判定され、静止していても
    # 低解像度のまま／ゴーストが安定して出ない状態になる。
    region_key = None
    try:
        region = getattr(context, "region", None)
        if region is not None:
            region_key = region.as_pointer()
    except Exception:
        region_key = None
    prev_view_hash = _last_view_hashes.get(region_key)
    view_moving = (view_hash is not None and view_hash != prev_view_hash)
    _last_view_hashes[region_key] = view_hash
    interacting = view_moving or ((now - _last_change_time) < _INTERACTION_IDLE_SEC)

    max_steps = _cached_base_steps
    # V16.1.1: 操作中は「ステップ数」に加えて「描画解像度」も落とす。
    # レイマーチのコストはピクセル数に正比例するため、プリミティブ数が多いシーンほど効く。
    res_scale = 1.0
    if interacting:
        if view_moving:
            max_steps = min(max_steps, _CAMERA_MOVING_STEP_CAP)
            res_scale = _CAMERA_MOVING_RES_SCALE
        else:
            max_steps = min(max_steps, _TRANSFORM_STEP_CAP)
            res_scale = _TRANSFORM_RES_SCALE

        # 操作が止まった後にフル品質で1フレーム描き直すためのタイマーを予約
        if not _restore_timer_armed:
            _restore_timer_armed = True
            try:
                bpy.app.timers.register(_restore_preview_quality,
                                        first_interval=_INTERACTION_IDLE_SEC + 0.02)
            except Exception:
                _restore_timer_armed = False

    inv_proj_view_local = inv_world_output @ rv3d.perspective_matrix.inverted()
    uniforms = {
        "invProjViewLocal": inv_proj_view_local,
        "domainSize": _cached_domain_size,
        "primCount": _cached_prim_count,
        "symmetryFlags": _cached_sym_mask,
        "maxSteps": max_steps,
        # 操作中は法線を3タップの前方差分にして map() の呼び出しを半減させる
        "fastNormal": 1 if interacting else 0,
        "primTex": _cached_prim_tex,
    }

    try:
        drawn_scaled = False
        if res_scale < 1.0:
            drawn_scaled = _draw_raymarch_scaled(context, shader, uniforms, res_scale)
        if not drawn_scaled:
            gpu.state.blend_set('ALPHA')
            gpu.state.depth_test_set('ALWAYS')
            gpu.state.face_culling_set('NONE')
            _draw_raymarch(shader, uniforms)
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
                        # Curve Sync のカーブ本体はターゲットコレクションの正式メンバーなので
                        # このチェックだけでオブジェクトの移動/変形を拾える
                        if id_orig.name in out_p.target_collection.objects:
                            is_relevant = True; break
                        # Curve Sync (Proxy): カーブ本体はコレクション外にあるので、
                        # プロキシEmpty経由で参照先カーブの移動/変形も拾う
                        for col_obj in out_p.target_collection.objects:
                            target = _resolve_curve_sync_target(col_obj)
                            if target and target.name == id_orig.name:
                                is_relevant = True; break
                        if is_relevant: break
        elif isinstance(id_orig, bpy.types.Curve):
            # Curve Sync: 編集モードでのカーブ制御点編集はデータブロック側の更新として来る
            # （直接コレクションに入れたカーブ・プロキシ経由で参照しているカーブの両方に対応）
            for o in scene.objects:
                out_p = getattr(o.original, "sdf_props", None)
                if out_p and out_p.is_output and out_p.target_collection:
                    for col_obj in out_p.target_collection.objects:
                        target = _resolve_curve_sync_target(col_obj)
                        if target and target.data == id_orig:
                            is_relevant = True; break
                if is_relevant: break
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
    # V15.9.9.4: プレビューキャッシュも無効化
    mark_preview_dirty()
    # 必要に応じて即座に更新をトリガー
    for obj in scene.objects:
        if getattr(obj, "sdf_props", None) and obj.sdf_props.is_output:
            engine.update_sdf_mesh(obj)

def clear_batch():
    global _batch, _cached_prim_tex, _cached_curve_guides, _guide_shader
    global _blit_shader, _blit_batch
    _batch = None
    # V15.9.9.4: プレビューキャッシュも破棄して次回描画で再構築させる
    _cached_prim_tex = None
    # Curve Sync ガイド線のキャッシュとシェーダも破棄する。特に _guide_shader は
    # GPUShader を保持しているため、アドオン再読み込み時に前セッションの参照が
    # 残らないようここで手放す
    _cached_curve_guides = None
    _guide_shader = None
    # V16.1.1: 低解像度描画用のオフスクリーンはGPUリソースなので明示的に解放する
    for off in _offscreens.values():
        try:
            off.free()
        except Exception:
            pass
    _offscreens.clear()
    # リージョンのポインタは領域が作り直されると使い回されるため、ここで捨てる
    _last_view_hashes.clear()
    _blit_shader = None
    _blit_batch = None
    mark_preview_dirty()
