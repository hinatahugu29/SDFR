import bpy
import numpy as np
import os
from mathutils import Matrix, Vector, Euler
from ._native import rust_gpu_sdf
from .constants import FIELD_TYPE_INDEX, PROFILE_2D_INDEX


# -------------------------------------------------------------------------
# Rust メッシュ生成・同期ロジック
# -------------------------------------------------------------------------

# 非同期更新管理用 (V10.3)
_pending_update = False
_is_timer_registered = False
_force_next_normals = False
_last_mesh_request = None
_safe_retry_active = False
_gpu_chunked_mc_active = False
_gpu_chunked_dc_active = False
_cpu_chunked_fallback_active = False
_in_update = False
_duplicate_cooldown = False
_appearance_update_cooldown = False
_appearance_update_token = 0
_DEBUG_FLAG_FILE = os.path.join(os.path.dirname(__file__), "SDF_DEBUG_LAYOUT.ON")
_PERF_FLAG_FILE = os.path.join(os.path.dirname(__file__), "SDF_PERF_LOG.ON")
_MESH_DEBUG_FLAG_FILE = os.path.join(os.path.dirname(__file__), "SDF_MESH_DEBUG.ON")
_DEBUG_LAYOUT = (
    os.environ.get("SDF_DEBUG_LAYOUT", "").strip().lower() in {"1", "true", "yes", "on"}
    or os.path.exists(_DEBUG_FLAG_FILE)
)
_PERF_LOGGING = (
    os.environ.get("SDF_PERF_LOG", "").strip().lower() in {"1", "true", "yes", "on"}
    or os.path.exists(_PERF_FLAG_FILE)
)
_MESH_DEBUG = (
    os.environ.get("SDF_MESH_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}
    or os.path.exists(_MESH_DEBUG_FLAG_FILE)
)

# 状態キャッシュ (V11.2): { "object_name": state_hash }
_last_state_hashes = {}
_cached_divider_names = set()

def _dbg_layout(msg):
    if _DEBUG_LAYOUT:
        print(f"[SDF-Debug/Layout] {msg}")

def _perf_log(msg):
    if _PERF_LOGGING:
        print(msg)

def _dbg_mesh(msg):
    if _MESH_DEBUG:
        print(f"[SDF-Debug/Mesh] {msg}")

def set_diagnostics_flags(perf_log=None, mesh_debug=None, layout_debug=None):
    """Apply diagnostic logging switches without requiring an add-on reload."""
    global _PERF_LOGGING, _MESH_DEBUG, _DEBUG_LAYOUT
    if perf_log is not None:
        _PERF_LOGGING = bool(perf_log)
    if mesh_debug is not None:
        _MESH_DEBUG = bool(mesh_debug)
    if layout_debug is not None:
        _DEBUG_LAYOUT = bool(layout_debug)

def _choose_chunk_cells(resolution, requested_cells, min_cells=32):
    return max(int(min_cells), min(int(requested_cells), int(resolution)))

def _chunk_weld_threshold(props, base_threshold):
    if not getattr(props, "use_weld", False):
        return 0.0
    return max(float(base_threshold), float(getattr(props, "chunk_seam_weld_scale", 0.0)))

if _DEBUG_LAYOUT:
    debug_source = "env:SDF_DEBUG_LAYOUT" if os.environ.get("SDF_DEBUG_LAYOUT") else f"flag:{_DEBUG_FLAG_FILE}"
    print(f"[SDF-Debug/Layout] debug logging is ENABLED ({debug_source})")

def get_sdf_state_fingerprint(output_obj, depsgraph):
    """現在の全オブジェクトの状態をハッシュ化して返す"""
    props = output_obj.sdf_props
    state = [
        props.resolution,
        props.domain_size,
        props.algo_type,
        props.meshing_backend,
        props.chunked_fallback_cells,
        props.protect_partial_mesh,
        props.auto_safe_retry,
        props.safe_retry_min_res,
        props.auto_gpu_chunked_fallback,
        props.auto_chunked_fallback,
        props.auto_chunk_high_res,
        props.auto_chunk_start_res,
        props.chunk_seam_weld_scale,
        props.use_weld,
        props.weld_threshold,
        props.sym_x, props.sym_y, props.sym_z,
        props.use_solo, props.sdf_stack_index,
    ]

    # 全スタックの状態を収集
    for i, item in enumerate(props.sdf_stack):
        if not item.enabled or not item.object_ptr:
            state.append((i, False))
            continue

        state.append((i, item.item_type, item.enabled, item.start_new_group, item.is_layer_boundary, item.obj_name, item.name_override))
        
        obj_orig = item.object_ptr
        try:
            # 評価済みオブジェクトから行列を取得
            obj_eval = obj_orig.evaluated_get(depsgraph)
            state.append(tuple(tuple(row) for row in obj_eval.matrix_world))
        except:
            continue
            
        p_props = getattr(obj_orig, "sdf_props", None)
        if item.item_type == 'CURVE_SYNC':
            # Curve Sync: このスタックアイテム（カーブ本体、またはそれを指すプロキシEmpty）
            # 自身のパイプ設定・参照先カーブ名・カーブ形状をハッシュに含める
            target_curve = _resolve_curve_sync_target(obj_orig)
            state.append((
                p_props.curve_pipe_radius if p_props else 0.0,
                p_props.curve_sample_resolution if p_props else 0,
                p_props.operation if p_props else '0',
                p_props.smoothness if p_props else 0.0,
                tuple(p_props.color) if p_props else None,
                p_props.metallic if p_props else 0.0,
                p_props.roughness if p_props else 0.0,
                target_curve.name if target_curve else None,
            ))
            if target_curve:
                try:
                    target_eval = target_curve.evaluated_get(depsgraph)
                    state.append(tuple(tuple(row) for row in target_eval.matrix_world))
                    for spl in target_eval.data.splines:
                        state.append((spl.type, spl.use_cyclic_u, spl.order_u, spl.resolution_u))
                        state.append(tuple((pt.co.x, pt.co.y, pt.co.z, pt.co.w) for pt in spl.points))
                        state.append(tuple((
                            bp.co.x, bp.co.y, bp.co.z,
                            bp.handle_left.x, bp.handle_left.y, bp.handle_left.z,
                            bp.handle_right.x, bp.handle_right.y, bp.handle_right.z,
                        ) for bp in spl.bezier_points))
                except Exception:
                    pass
        elif p_props:
            # プリミティブまたはEmpty（コレクション仕切り）共通のレイアウト設定をハッシュに含める
            state.append((
                p_props.layout_use_mirror, p_props.layout_use_radial, p_props.layout_use_spiral, p_props.layout_use_jitter, p_props.layout_use_grid,
                p_props.mirror_x, p_props.mirror_y, p_props.mirror_z,
                p_props.mirror_offset,
                p_props.radial_count, p_props.radial_radius, p_props.radial_axis,
                p_props.spiral_pitch, p_props.jitter_seed, p_props.jitter_strength,
                p_props.grid_count_x, p_props.grid_count_y, p_props.grid_count_z,
                p_props.grid_spacing_x, p_props.grid_spacing_y, p_props.grid_spacing_z,
                p_props.instance_rot_x, p_props.instance_rot_y, p_props.instance_rot_z,
                p_props.step_rot_x, p_props.step_rot_y, p_props.step_rot_z,
            ))
            if p_props.is_primitive:
                state.append((
                    p_props.shape_type,
                    p_props.operation,
                    p_props.blend_profile,
                    p_props.chamfer_smooth,
                    p_props.smoothness,
                    tuple(p_props.color),
                    p_props.metallic,
                    p_props.roughness,
                    p_props.noise_strength,
                    p_props.noise_scale,
                    tuple((d.deform_type, d.axis, d.factor, tuple(d.origin), d.elongate_x, d.elongate_y, d.elongate_z, d.enabled) for d in p_props.deform_stack),
                    p_props.radius,
                    p_props.p1, p_props.p2, p_props.p3, p_props.p4,
                    p_props.field_type,
                    p_props.gyroid_preset,
                    p_props.gyroid_mask_shape,
                    p_props.gyroid_boundary_mode,
                    p_props.gyroid_phase,
                    p_props.gyroid_axis_x,
                    p_props.gyroid_axis_y,
                    p_props.gyroid_axis_z,
                    p_props.ngon_sides,
                    p_props.edge_profile,
                    p_props.edge_profile_size,
                    p_props.edge_chamfer_smooth,
                    p_props.shell_thickness,
                    p_props.profile_2d_type,
                    p_props.extrude_depth,
                    p_props.extrude_chamfer,
                    p_props.profile_corner_radius,
                    p_props.lathe_offset,
                    tuple(p_props.bezier_pt_b),
                    tuple(p_props.bezier_pt_c),
                    p_props.bezier_start_radius,
                    p_props.bezier_end_radius
                ))
            else:
                state.append(obj_orig.name)
        else:
            state.append(obj_orig.name)
            
    return hash(tuple(state))

def _resolve_curve_sync_target(stack_obj):
    """CURVE_SYNC スタックアイテムの object_ptr から実際のジオメトリを持つカーブを解決する。
    object_ptr 自身が Curve ならそれをそのまま返し、Curve Sync プロキシ Empty なら
    その sdf_props.curve_target_obj を辿る。"""
    if not stack_obj:
        return None
    if stack_obj.type == 'CURVE':
        return stack_obj
    cp = getattr(stack_obj, "sdf_props", None)
    if cp and cp.curve_target_obj and cp.curve_target_obj.type == 'CURVE':
        return cp.curve_target_obj
    return None

def sync_sdf_stack(output_obj):
    """SDF_Collection と sdf_stack を同期する"""
    import time
    t0 = time.perf_counter()
    props = output_obj.sdf_props
    col = props.target_collection
    if not col: return
    
    # --- V15.9.9.5: 構造的な変更がない場合は同期処理を即リターン ---
    col_names = {obj.name for obj in col.objects if obj.name != output_obj.name}
    stack_names = {item.object_ptr.name for item in props.sdf_stack if item.object_ptr}
    has_stale_stack_item = any(
        (item.obj_name and item.obj_name not in col.objects) or
        (not item.object_ptr and bool(item.obj_name))
        for item in props.sdf_stack
    )
    collection_item_names = [
        (item.empty_ptr or item.object_ptr).name
        for item in props.sdf_stack
        if item.item_type == 'COLLECTION' and (item.empty_ptr or item.object_ptr)
    ]
    has_duplicate_collection_item = len(collection_item_names) != len(set(collection_item_names))
    if col_names == stack_names and not has_stale_stack_item and not has_duplicate_collection_item:
        # print(f"[SDF-PERF] sync_sdf_stack: skipped in {(time.perf_counter() - t0)*1000.0:.4f} ms")
        return
    
    # 現在のリストにあるオブジェクトの名前セット（ポインタ比較による重複バグ防止）
    existing_names = set()
    for item in props.sdf_stack:
        if item.object_ptr:
            item.obj_name = item.object_ptr.name
        if item.obj_name:
            existing_names.add(item.obj_name)
    
    # コレクションにあってリストにないものを追加
    new_objs = [obj for obj in col.objects if obj.name != output_obj.name and obj.name not in existing_names]
    
    # プリミティブを先に追加し、コレクション区切りEMPTYを最後に追加する
    # （Curve Sync プロキシEmptyは仕切りではなくプリミティブ扱いなので対象外）
    # その際、複製順序タグ（_sdf_dup_order）があれば元の順序を完全に維持する
    new_objs.sort(key=lambda o: (
        1 if (o.type == 'EMPTY' and not getattr(o.sdf_props, "is_curve_sync_proxy", False)) else 0,
        o.get("_sdf_dup_order", 9999),
    ))
    
    for obj in new_objs:
        item = props.sdf_stack.add()
        item.object_ptr = obj
        item.obj_name = obj.name
        if obj.type == 'EMPTY':
            if getattr(obj.sdf_props, "is_curve_sync_proxy", False):
                item.item_type = 'CURVE_SYNC'
            else:
                item.item_type = 'COLLECTION'
                item.empty_ptr = obj
                item.name_override = obj.name
        elif obj.type == 'CURVE':
            item.item_type = 'CURVE_SYNC'
        else:
            item.item_type = 'PRIMITIVE'

    seen_collection_objects = set()
    duplicate_collection_indices = []
    for i, item in enumerate(props.sdf_stack):
        if item.item_type != 'COLLECTION':
            continue
        obj = item.empty_ptr or item.object_ptr
        obj_name = obj.name if obj else item.obj_name
        if not obj_name:
            continue
        if obj_name in seen_collection_objects:
            duplicate_collection_indices.append(i)
        else:
            seen_collection_objects.add(obj_name)
    for i in reversed(duplicate_collection_indices):
        props.sdf_stack.remove(i)
            
    # リストにあってコレクションにない（または削除された）ものを削除
    for i in range(len(props.sdf_stack) - 1, -1, -1):
        item = props.sdf_stack[i]
        # object_ptrがNoneでも、名前がcol.objectsにあれば一時的な切断とみなして削除しない
        if item.obj_name and item.obj_name not in col.objects:
            props.sdf_stack.remove(i)
        elif not item.obj_name and not item.object_ptr:
            props.sdf_stack.remove(i)
            
    global _cached_divider_names
    _cached_divider_names = {item.empty_ptr.name for item in props.sdf_stack if item.item_type == 'COLLECTION' and item.empty_ptr}
    _perf_log(f"[SDF-PERF] sync_sdf_stack: executed in {(time.perf_counter() - t0)*1000.0:.2f} ms")

def get_layout_matrices(p_props):
    """オブジェクトのレイアウト設定に基づいて、複製展開用の相対変換行列のリストを生成する"""
    matrices = [Matrix.Identity(4)]
    
    # 1. Grid
    if p_props.layout_use_grid:
        grid_mats = []
        cx = (p_props.grid_count_x - 1) * p_props.grid_spacing_x * 0.5
        cy = (p_props.grid_count_y - 1) * p_props.grid_spacing_y * 0.5
        cz = (p_props.grid_count_z - 1) * p_props.grid_spacing_z * 0.5
        for x in range(p_props.grid_count_x):
            tx = x * p_props.grid_spacing_x - cx
            for y in range(p_props.grid_count_y):
                ty = y * p_props.grid_spacing_y - cy
                for z in range(p_props.grid_count_z):
                    tz = z * p_props.grid_spacing_z - cz
                    grid_mats.append(Matrix.Translation((tx, ty, tz)))
        new_mats = []
        for m in matrices:
            for gm in grid_mats:
                new_mats.append(m @ gm)
        matrices = new_mats
        
    # 2. Radial or Spiral
    if p_props.layout_use_radial or p_props.layout_use_spiral:
        radial_mats = []
        count = max(1, p_props.radial_count)
        axis = int(p_props.radial_axis)
        _dbg_layout(
            f"get_layout_matrices radial/spiral enabled: count={count}, axis={axis}, "
            f"radius={p_props.radial_radius:.4f}, pitch={p_props.spiral_pitch:.4f}"
        )
        
        axis_vec = Vector((1, 0, 0)) if axis == 0 else Vector((0, 1, 0)) if axis == 1 else Vector((0, 0, 1))
        
        inst_rot_vec = Vector((p_props.instance_rot_x, p_props.instance_rot_y, p_props.instance_rot_z))
        step_rot_vec = Vector((p_props.step_rot_x, p_props.step_rot_y, p_props.step_rot_z))
        
        for i in range(count):
            angle = i * (2.0 * np.pi / count)
            rot_mat = Matrix.Rotation(angle, 4, axis_vec)
            
            if axis == 2:
                offset_vec = Vector((p_props.radial_radius, 0.0, 0.0))
            elif axis == 1:
                offset_vec = Vector((0.0, 0.0, p_props.radial_radius))
            else:
                offset_vec = Vector((0.0, p_props.radial_radius, 0.0))
                
            height = i * p_props.spiral_pitch if p_props.layout_use_spiral else 0.0
            h_vec = axis_vec * height
            
            trans_offset_orig = Matrix.Translation(offset_vec)
            trans_offset_back = Matrix.Translation(-offset_vec)
            h_trans = Matrix.Translation(h_vec)
            
            current_rot_vec = inst_rot_vec + step_rot_vec * i
            accum_rot = Euler((current_rot_vec.x, current_rot_vec.y, current_rot_vec.z)).to_matrix().to_4x4()
            
            instance_mat = rot_mat @ h_trans @ trans_offset_orig @ accum_rot
            radial_mats.append(instance_mat)
            
        new_mats = []
        for m in matrices:
            for rm in radial_mats:
                new_mats.append(m @ rm)
        matrices = new_mats

    # 3. Mirror
    if p_props.layout_use_mirror:
        mirror_mats = [Matrix.Identity(4)]
        offset = p_props.mirror_offset
        _dbg_layout(
            f"get_layout_matrices mirror enabled: x={p_props.mirror_x}, y={p_props.mirror_y}, "
            f"z={p_props.mirror_z}, offset={offset:.4f}"
        )
        
        if p_props.mirror_x:
            new_mirrors = []
            m_scale = Matrix.Scale(-1.0, 4, (1.0, 0.0, 0.0))
            m_trans_pos = Matrix.Translation((offset, 0.0, 0.0))
            m_trans_neg = Matrix.Translation((-offset, 0.0, 0.0))
            for mm in mirror_mats:
                new_mirrors.append(mm @ m_trans_pos)
                new_mirrors.append(mm @ m_trans_neg @ m_scale)
            mirror_mats = new_mirrors
            
        if p_props.mirror_y:
            new_mirrors = []
            m_scale = Matrix.Scale(-1.0, 4, (0.0, 1.0, 0.0))
            m_trans_pos = Matrix.Translation((0.0, offset, 0.0))
            m_trans_neg = Matrix.Translation((0.0, -offset, 0.0))
            for mm in mirror_mats:
                new_mirrors.append(mm @ m_trans_pos)
                new_mirrors.append(mm @ m_trans_neg @ m_scale)
            mirror_mats = new_mirrors

        if p_props.mirror_z:
            new_mirrors = []
            m_scale = Matrix.Scale(-1.0, 4, (0.0, 0.0, 1.0))
            m_trans_pos = Matrix.Translation((0.0, 0.0, offset))
            m_trans_neg = Matrix.Translation((0.0, 0.0, -offset))
            for mm in mirror_mats:
                new_mirrors.append(mm @ m_trans_pos)
                new_mirrors.append(mm @ m_trans_neg @ m_scale)
            mirror_mats = new_mirrors
            
        new_mats = []
        for m in matrices:
            for mm in mirror_mats:
                new_mats.append(m @ mm)
        matrices = new_mats
        
    return matrices


def _finalize_group_elements(elements, primitives, auto_domain, inv_world_output, props, max_extent_list):
    """working_group / expanded_group の要素を primitives へ確定する。
    Curve Sync は構築済みカプセル群を 'prebuilt_prims' マーカーとして working_group に
    積んでいるので、ここでそのまま展開する（スタック順を保つため）。"""
    for el in elements:
        prebuilt = el.get('prebuilt_prims')
        if prebuilt:
            primitives.extend(prebuilt)
            continue
        p = build_element_primitive(el, auto_domain, inv_world_output, props, max_extent_list,
                                    layer_id=el.get('layer_id', 0))
        if p:
            primitives.append(p)


def build_element_primitive(el, auto_domain, inv_world_output, props, max_extent, layer_id=0):
    obj_orig = el['obj_orig']
    obj = el['obj_eval']
    p_props = el['p_props']
    is_prim = el['is_prim']
    loc = el['loc']
    rot = el['rot']
    scale = el['scale']
    
    if is_prim:
        shape = p_props.shape_type
        op_int = int(p_props.operation)
        smoothness = p_props.smoothness
        color = list(p_props.color)
        metallic = p_props.metallic
        roughness = p_props.roughness
        noise_strength = p_props.noise_strength
        noise_scale = p_props.noise_scale
        radius = p_props.radius
        
        # --- Auto Domain Logic ---
        if auto_domain:
            max_s = max(abs(scale.x), abs(scale.y), abs(scale.z))
            if shape == 'torus':
                shape_extent = p_props.p1 + p_props.p2
            elif shape in ('cylinder', 'capsule', 'hex_prism'):
                shape_extent = max(p_props.p1, p_props.p2)
            elif shape == 'capped_cone':
                shape_extent = max(p_props.p1, p_props.p2, p_props.p3)
            elif shape == 'pyramid':
                shape_extent = max(p_props.p1, p_props.p2)
            elif shape == 'ngon_prism':
                shape_extent = max(p_props.p1, p_props.p3)
            elif shape == 'ellipsoid':
                shape_extent = max(p_props.p1, p_props.p2, p_props.p3)
            elif shape == 'rounded_cylinder':
                shape_extent = max(p_props.p1 + p_props.p2, p_props.p3)
            elif shape == 'capped_torus':
                shape_extent = p_props.p1 + p_props.p2
            elif shape == 'octahedron':
                shape_extent = p_props.p1
            elif shape == 'cut_sphere':
                shape_extent = radius
            elif shape == 'math_field':
                shape_extent = max(p_props.p4, 0.1)
            elif shape == 'extrude':
                shape_extent = max(p_props.p1, p_props.p2, p_props.extrude_depth)
            elif shape == 'lathe':
                shape_extent = p_props.lathe_offset + max(p_props.p1, p_props.p2)
            elif shape == 'bezier_curve':
                b_dist = np.sqrt(p_props.bezier_pt_b[0]**2 + p_props.bezier_pt_b[1]**2 + p_props.bezier_pt_b[2]**2)
                c_dist = np.sqrt(p_props.bezier_pt_c[0]**2 + p_props.bezier_pt_c[1]**2 + p_props.bezier_pt_c[2]**2)
                shape_extent = max(b_dist, c_dist) + max(p_props.bezier_start_radius, p_props.bezier_end_radius)
            else:
                shape_extent = radius
            
            prim_r = (max_s * shape_extent) + (smoothness + noise_strength) * max_s
            p_center = loc
            
            layout_r = 0.0
            if p_props.layout_use_mirror:
                layout_r = max(layout_r, abs(p_props.mirror_offset))
            if p_props.layout_use_radial or p_props.layout_use_spiral:
                layout_r = max(layout_r, abs(p_props.radial_radius))
            if p_props.layout_use_grid:
                grid_ext_x = (p_props.grid_count_x - 1) * p_props.grid_spacing_x
                grid_ext_y = (p_props.grid_count_y - 1) * p_props.grid_spacing_y
                grid_ext_z = (p_props.grid_count_z - 1) * p_props.grid_spacing_z
                layout_r = max(layout_r, np.sqrt(grid_ext_x**2 + grid_ext_y**2 + grid_ext_z**2) * 0.5)
            if p_props.layout_use_jitter:
                layout_r = max(layout_r, abs(p_props.jitter_strength))

            deform_r = 0.0
            has_deform = False
            for si, d_item in enumerate(p_props.deform_stack):
                if si >= 4:
                    break
                if not d_item.enabled:
                    continue
                has_deform = True
                d_type = d_item.deform_type
                if d_type == 'ELONGATE':
                    ex = max(d_item.elongate_x, 0.0)
                    ey = max(d_item.elongate_y, 0.0)
                    ez = max(d_item.elongate_z, 0.0)
                    deform_r += np.sqrt(ex * ex + ey * ey + ez * ez)
                elif d_type == 'BEND':
                    bend_angle = abs(d_item.factor)
                    deform_r += max_s * max_s * bend_angle * 0.5 + max_s * 0.3
                elif d_type == 'TWIST':
                    twist_angle = abs(d_item.factor)
                    deform_r += max_s * twist_angle * max_s * 0.5
                elif d_type == 'TAPER':
                    taper_factor = abs(d_item.factor)
                    deform_r += max_s * taper_factor * max_s

            if has_deform:
                deform_r += max_s * 0.75 + 0.25
            
            dist_from_origin = np.sqrt(p_center.x**2 + p_center.y**2 + p_center.z**2)
            max_extent[0] = max(max_extent[0], dist_from_origin + layout_r + prim_r + deform_r)

        # V12 Packing
        mode_flags = 0
        if p_props.layout_use_mirror: mode_flags |= 1
        if p_props.layout_use_radial: mode_flags |= 2
        if p_props.layout_use_spiral: mode_flags |= 4
        if p_props.layout_use_grid:   mode_flags |= 8
        if p_props.layout_use_jitter: mode_flags |= 32
        
        mirror_mask = (1 if p_props.mirror_x else 0) | (2 if p_props.mirror_y else 0) | (4 if p_props.mirror_z else 0)
        radial_axis = int(p_props.radial_axis)
        radial_count = max(1, p_props.radial_count)
        
        p1_int = int(mode_flags | (mirror_mask << 8) | (radial_count << 12) | (radial_axis << 20))
        packed1 = float(p1_int)
        
        g_int = int(p_props.grid_count_x + 100 * p_props.grid_count_y + 10000 * p_props.grid_count_z)
        grid_packed = float(g_int)
        
        layout_data1 = [packed1, p_props.mirror_offset, p_props.radial_radius, p_props.spiral_pitch]
        layout_data2 = [p_props.jitter_seed, p_props.jitter_strength, grid_packed, p_props.grid_spacing_x]
        layout_data3 = [p_props.grid_spacing_y, p_props.grid_spacing_z, p_props.instance_rot_x, p_props.instance_rot_y]
        layout_data4 = [p_props.instance_rot_z, p_props.step_rot_x, p_props.step_rot_y, p_props.step_rot_z]
        extra_params = [p_props.p1, p_props.p2, p_props.p3, p_props.p4]
        gyroid_params = [0.0, 1.0, 1.0, 1.0]
        if shape == 'math_field':
            gyroid_params = [
                p_props.gyroid_phase,
                max(p_props.gyroid_axis_x, 0.05),
                max(p_props.gyroid_axis_y, 0.05),
                max(p_props.gyroid_axis_z, 0.05),
            ]
        if shape == 'ngon_prism':
            extra_params[1] = float(p_props.ngon_sides)
        
        # Deform Packing
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
        
        deform_data1 = [float(packed_meta), slot_params[0][0], slot_params[0][1], slot_params[0][2]]
        deform_data2 = [slot_params[0][3], slot_params[1][0], slot_params[1][1], slot_params[1][2]]
        deform_data3 = [slot_params[1][3], slot_params[2][0], slot_params[2][1], slot_params[2][2]]
        deform_data4 = [slot_params[2][3], slot_params[3][0], slot_params[3][1], slot_params[3][2]]
        
        blend_prof = int(p_props.blend_profile)
        cham_smooth = p_props.chamfer_smooth
        edge_profile = int(p_props.edge_profile)
        edge_chamfer_smooth = p_props.edge_chamfer_smooth
        shell_thickness = p_props.shell_thickness
        edge_profile_size = p_props.edge_profile_size
        if shape == 'math_field':
            # edge_profile は通常のプリミティブでは面取り種別だが、Math Fieldでは未使用のため
            # 数式選択(field_type)を運ぶスロットとして流用する
            edge_profile = FIELD_TYPE_INDEX.get(p_props.field_type, 0)
            edge_chamfer_smooth = float(int(p_props.gyroid_mask_shape))
            edge_profile_size = float(int(p_props.gyroid_boundary_mode))
        elif shape in ('extrude', 'lathe'):
            edge_profile = PROFILE_2D_INDEX.get(p_props.profile_2d_type, 0)
            edge_chamfer_smooth = p_props.extrude_chamfer
            if shape == 'extrude':
                extra_params = [p_props.p1, p_props.p2, p_props.extrude_depth, p_props.profile_corner_radius]
            else:
                extra_params = [p_props.p1, p_props.p2, p_props.lathe_offset, p_props.profile_corner_radius]
        elif shape == 'bezier_curve':
            extra_params = [p_props.bezier_pt_b[0], p_props.bezier_pt_b[1], p_props.bezier_pt_b[2], p_props.bezier_start_radius]
            gyroid_params = [p_props.bezier_pt_c[0], p_props.bezier_pt_c[1], p_props.bezier_pt_c[2], p_props.bezier_end_radius]
        
    else:
        name_lower = obj_orig.name.lower()
        if 'sphere' in name_lower: shape = 'sphere'
        elif 'box' in name_lower or 'cube' in name_lower: shape = 'box'
        elif 'torus' in name_lower: shape = 'torus'
        elif 'cylinder' in name_lower: shape = 'cylinder'
        else: return None
        
        op_int = 0
        smoothness = 0.5
        color = [1.0, 1.0, 1.0]
        metallic = 0.0
        roughness = 0.5
        noise_strength = 0.0
        noise_scale = 5.0
        layout_data1 = [0.0] * 4
        layout_data2 = [0.0] * 4
        layout_data3 = [0.0] * 4
        layout_data4 = [0.0] * 4
        deform_data1 = [0.0] * 4
        deform_data2 = [0.0] * 4
        deform_data3 = [0.0] * 4
        deform_data4 = [0.0] * 4
        extra_params = [0.0] * 4
        gyroid_params = [0.0, 1.0, 1.0, 1.0]
        radius = 1.0
        blend_prof = 0
        cham_smooth = 0.0
        edge_profile = 0
        edge_chamfer_smooth = 0.0
        shell_thickness = 0.0
        edge_profile_size = 0.0
        
        if auto_domain:
            max_s = max(scale.x, scale.y, scale.z)
            prim_r = max_s * 1.5
            dist_from_origin = np.sqrt(loc.x**2 + loc.y**2 + loc.z**2)
            max_extent[0] = max(max_extent[0], dist_from_origin + prim_r)

    sym_loc = [loc.x, loc.y, loc.z]
    size = (scale.x, scale.y, scale.z)
    
    return rust_gpu_sdf.SdfPrimitive(
        shape, sym_loc, [rot.x, rot.y, rot.z, rot.w], radius, size, op_int, smoothness, 
        color=color, metallic=metallic, roughness=roughness, noise_strength=noise_strength, noise_scale=noise_scale,
        layout_data1=layout_data1, layout_data2=layout_data2, 
        layout_data3=layout_data3, layout_data4=layout_data4,
        extra_params=extra_params,
        gyroid_params=gyroid_params,
        deform_data1=deform_data1, deform_data2=deform_data2,
        deform_data3=deform_data3, deform_data4=deform_data4,
        blend_profile=blend_prof,
        chamfer_smooth=cham_smooth,
        edge_profile=edge_profile,
        edge_chamfer_smooth=edge_chamfer_smooth,
        shell_thickness=shell_thickness,
        edge_profile_size=edge_profile_size,
        layer_id=layer_id
    )

def _curve_polylines_from_to_mesh(c_obj):
    """評価済みカーブを Blender 自身の変換でポリライン化する。
    NURBS のように制御点の直結では形状が合わないスプライン用のフォールバック。
    ベベル/押し出しで面が生成されている場合はポリラインとして扱えないため空を返す。
    """
    try:
        me = c_obj.to_mesh()
    except Exception:
        return []
    if me is None:
        return []
    try:
        if len(me.polygons) > 0 or len(me.edges) == 0:
            return []
        coords = [v.co.copy() for v in me.vertices]
        adj = {}
        for e in me.edges:
            a, b = e.vertices[0], e.vertices[1]
            adj.setdefault(a, []).append(b)
            adj.setdefault(b, []).append(a)
    finally:
        try:
            c_obj.to_mesh_clear()
        except Exception:
            pass

    # 端点(次数1)から辿り、残り(閉ループ)を後から処理する
    starts = [v for v in adj if len(adj[v]) == 1] + [v for v in adj if len(adj[v]) != 1]
    used_edges = set()
    lines = []
    for s in starts:
        for first in adj[s]:
            key = (min(s, first), max(s, first))
            if key in used_edges:
                continue
            used_edges.add(key)
            line = [coords[s], coords[first]]
            cur = first
            while True:
                nxt = None
                for n in adj[cur]:
                    k = (min(cur, n), max(cur, n))
                    if k not in used_edges:
                        used_edges.add(k)
                        nxt = n
                        break
                if nxt is None:
                    break
                line.append(coords[nxt])
                cur = nxt
            if len(line) >= 2:
                lines.append(line)
    return lines


def _curve_polylines(c_obj, subdiv, allow_to_mesh=True):
    """評価済みカーブオブジェクトからポリライン(点列)のリストを作る。
    BEZIER / POLY は subdiv を反映して自前サンプリング、NURBS は to_mesh() へフォールバック。

    allow_to_mesh=False のときは to_mesh() を使わず、NURBS も制御点直結で近似する。
    to_mesh()/to_mesh_clear() はオブジェクトの一時メッシュを生成・解放する（=IDデータへの
    書き込み）ため、ビューポートの描画コールバック内から呼ぶのは安全ではない。
    プレビューのガイド線収集など描画中に走る経路からは False を渡すこと。
    """
    lines = []
    needs_to_mesh = False
    for spl in c_obj.data.splines:
        cyclic = spl.use_cyclic_u
        if spl.type == 'BEZIER' and len(spl.bezier_points) >= 2:
            bps = list(spl.bezier_points)
            seg_count = len(bps) if cyclic else len(bps) - 1
            pts = []
            for i in range(seg_count):
                bp1 = bps[i]
                bp2 = bps[(i + 1) % len(bps)]
                p0 = bp1.co
                p1 = bp1.handle_right
                p2 = bp2.handle_left
                p3 = bp2.co
                for step in range(subdiv):
                    t = step / float(subdiv)
                    u = 1.0 - t
                    pts.append(u*u*u * p0 + 3.0*u*u*t * p1 + 3.0*u*t*t * p2 + t*t*t * p3)
            # 開いたカーブは終端を明示的に追加、閉じたカーブは始点へ戻して閉じる
            pts.append(bps[0].co.copy() if cyclic else bps[-1].co.copy())
            lines.append(pts)
        elif spl.type == 'NURBS' and len(spl.points) >= 2:
            needs_to_mesh = True
        elif len(spl.points) >= 2:
            pts = [pt.co.xyz for pt in spl.points]
            if cyclic:
                pts.append(pts[0].copy())
            lines.append(pts)

    if needs_to_mesh:
        if allow_to_mesh:
            fallback = _curve_polylines_from_to_mesh(c_obj)
            if fallback:
                # to_mesh() は全スプラインを含むため、自前サンプリング分は破棄して一本化する
                return fallback
        # to_mesh() が使えない/使わない場合は制御点直結で代用する
        for spl in c_obj.data.splines:
            if spl.type == 'NURBS' and len(spl.points) >= 2:
                pts = [pt.co.xyz for pt in spl.points]
                if spl.use_cyclic_u:
                    pts.append(pts[0].copy())
                lines.append(pts)
    return lines


def update_sdf_mesh(output_obj, depsgraph=None):


    global _pending_update, _is_timer_registered, _last_state_hashes, _in_update, _last_mesh_request, _safe_retry_active, _gpu_chunked_mc_active, _gpu_chunked_dc_active, _cpu_chunked_fallback_active
    if not output_obj or not output_obj.sdf_props.is_output or not output_obj.sdf_props.target_collection:
        return

    # --- V15.9.9.5: トランスフォーム操作中は重いメッシュ処理をスキップ ---
    try:
        op = bpy.context.active_operator
        if op and op.bl_idname in {"TRANSFORM_OT_translate", "TRANSFORM_OT_rotate", "TRANSFORM_OT_resize", "TRANSFORM_OT_tweak"}:
            return
    except Exception:
        pass

    if _in_update:
        return

    if not depsgraph:
        depsgraph = bpy.context.evaluated_depsgraph_get()

    _in_update = True
    try:
        # 常に最新のリストを保つ (V11.2)
        sync_sdf_stack(output_obj)
        sync_sdf_parents(output_obj)
    finally:
        _in_update = False

    # --- V15.9.9.4: メッシュ生成OFF時はここで即リターン ---
    # 「Show Result Mesh」がOFFのとき、結果メッシュは hide_viewport で隠されており
    # Rust計算もスキップされる。スタック/親子同期(sync_*)は済ませたうえで、
    # この後に続く状態フィンガープリント計算・全プリミティブ再構築・Rustメッシュ
    # 生成リクエスト（いずれも O(プリミティブ数) の重い処理）を丸ごと回避する。
    # プレビュー描画は draw_callback_3d 側で独立して行われるため影響しない。
    try:
        if not bpy.context.scene.sdf_show_result:
            return
    except Exception:
        pass

    
    # 状態の変更をチェック
    current_hash = get_sdf_state_fingerprint(output_obj, depsgraph)
    if _last_state_hashes.get(output_obj.name) == current_hash:
        return # 変更がないので何もしない
    
    # すでに更新中なら更新を予約して終了
    if rust_gpu_sdf.is_updating():
        # if not _pending_update:
        #    print(f"SDF Info: Update already in progress. Queuing next update for '{output_obj.name}'.")
        _pending_update = True
        if not _is_timer_registered:
            print("SDF Info: Re-registering mesh timer.")
            bpy.app.timers.register(sdf_mesh_timer, first_interval=0.05)
            _is_timer_registered = True
        return
    
    # ハッシュを更新（リクエストが通る直前で更新）
    _last_state_hashes[output_obj.name] = current_hash
    
    output_eval = output_obj.evaluated_get(depsgraph)
    inv_world_output = output_eval.matrix_world.inverted()

    
    props = output_obj.sdf_props
    res = props.resolution
    use_dc = (props.algo_type == 'DC')
    sym_mask = (1 if props.sym_x else 0) | (2 if props.sym_y else 0) | (4 if props.sym_z else 0)

    # --- V15.3: Auto Domain Expansion ---
    auto_domain = props.auto_domain
    max_extent = 0.001

    primitives = []
    working_group = []
    next_layer_id = 1
    active_layer_id = 0
    max_extent_list = [max_extent] # 参照渡し用のリスト
    _dbg_mesh(f"start scanning stack (len={len(props.sdf_stack)})")

    for i, item in enumerate(props.sdf_stack):
        if not item.enabled:
            continue
            
        if item.item_type == 'COLLECTION':
            empty_obj = item.empty_ptr
            if not empty_obj:
                continue
            _dbg_layout(
                f"stack[{i}] collection divider='{empty_obj.name}', "
                f"incoming_group_size={len(working_group)}"
            )
                
            try:
                empty_eval = empty_obj.evaluated_get(depsgraph)
            except:
                empty_eval = empty_obj
                
            empty_props = getattr(empty_obj, "sdf_props", None)
            if not empty_props:
                continue
                
            # レイアウト行列リスト
            layout_mats = get_layout_matrices(empty_props)
            _dbg_layout(f"divider '{empty_obj.name}' layout matrix count={len(layout_mats)}")
            
            expanded_group = []
            P = empty_eval.matrix_world
            try:
                P_inv = P.inverted()
            except:
                P_inv = Matrix.Identity(4)
                
            for element in working_group:
                # Curve Sync の構築済みカプセル群はレイアウト展開の対象外（v1スコープ）。
                # 展開せずにそのまま引き継ぐ（順序は保たれる）
                if element.get('prebuilt_prims'):
                    expanded_group.append(element)
                    continue

                # 親から見た相対トランスフォームの計算
                C = element['matrix_world']
                L = P_inv @ C
                
                # レイアウト展開
                for M in layout_mats:
                    C_new = P @ M @ L
                    local_mat = inv_world_output @ C_new
                    loc, rot, scale = local_mat.decompose()
                    det = local_mat.to_3x3().determinant()
                    _dbg_layout(
                        f"expanded '{element['obj_orig'].name}' via '{empty_obj.name}': "
                        f"loc=({loc.x:.3f},{loc.y:.3f},{loc.z:.3f}), "
                        f"scale=({scale.x:.3f},{scale.y:.3f},{scale.z:.3f}), det={det:.4f}"
                    )
                    
                    copied_el = element.copy()
                    copied_el['matrix_world'] = C_new.copy()
                    copied_el['loc'] = loc
                    copied_el['rot'] = rot
                    copied_el['scale'] = scale
                    expanded_group.append(copied_el)
            _dbg_layout(
                f"divider '{empty_obj.name}' expanded_group_size={len(expanded_group)} "
                f"(start_new_group={item.start_new_group}, layer_boundary={item.is_layer_boundary})"
            )
                    
            if item.is_layer_boundary:
                _finalize_group_elements(working_group, primitives, auto_domain, inv_world_output, props, max_extent_list)
                working_group = []
                active_layer_id = next_layer_id
                next_layer_id += 1
            elif item.start_new_group:
                active_layer_id = 0
                # 独立グループなので、ここで primitives に確定追加してリセット
                _finalize_group_elements(expanded_group, primitives, auto_domain, inv_world_output, props, max_extent_list)
                working_group = []
            else:
                # 入れ子として作業グループを引き継ぐ
                active_layer_id = 0
                working_group = expanded_group
                
        elif item.item_type == 'CURVE_SYNC':
            # Curve Sync: Blender カーブを capsule の連なりとして Union（複数本対応）
            # stack_obj はカーブ本体、またはカーブを指すプロキシEmpty（curve_target_obj）のどちらか。
            # パイプ半径等の設定は常に stack_obj 自身の sdf_props から読む（プロキシなら
            # 同じカーブを異なる設定で複数回参照できる）
            # Solo判定は他の早期 continue より先に行う。後ろに置くと、参照先カーブが
            # 未設定のプロキシが Solo 位置より後ろにあった場合に break できず、
            # それ以降のアイテムまで描画されてしまう
            if props.use_solo and i > props.sdf_stack_index:
                break
            stack_obj = item.object_ptr
            c_obj_orig = _resolve_curve_sync_target(stack_obj)
            if not c_obj_orig:
                continue

            try:
                c_obj = c_obj_orig.evaluated_get(depsgraph)
                c_mat = inv_world_output @ c_obj.matrix_world
                cp = getattr(stack_obj, "sdf_props", None)
                subdiv = max(4, cp.curve_sample_resolution if cp else 16)
                r_pipe = max(0.001, cp.curve_pipe_radius if cp else 0.15)
                op_int = int(cp.operation) if cp else 0
                smoothness = cp.smoothness if cp else 0.2
                color = list(cp.color) if cp else [0.3, 0.8, 1.0]
                metallic = cp.metallic if cp else 0.0
                roughness = cp.roughness if cp else 0.5
                curve_prims = []
                for pts in _curve_polylines(c_obj, subdiv):
                    for seg_i in range(len(pts) - 1):
                        p_a = c_mat @ pts[seg_i]
                        p_b = c_mat @ pts[seg_i + 1]
                        center = (p_a + p_b) * 0.5
                        vec_ab = p_b - p_a
                        h_len = vec_ab.length * 0.5
                        if h_len < 0.0001: continue
                        quat = vec_ab.to_track_quat('Z', 'Y')
                        prim = rust_gpu_sdf.SdfPrimitive(
                            'capsule', [center.x, center.y, center.z], [quat.x, quat.y, quat.z, quat.w],
                            r_pipe, (1.0, 1.0, 1.0), op_int, smoothness,
                            color=color, metallic=metallic, roughness=roughness,
                            noise_strength=0.0, noise_scale=5.0,
                            extra_params=[r_pipe, h_len, 0.0, 0.0],
                            layer_id=active_layer_id
                        )
                        curve_prims.append(prim)
                        if auto_domain:
                            dist_o = center.length
                            max_extent_list[0] = max(max_extent_list[0], dist_o + h_len + r_pipe + 0.5)
                # 構築済みプリミティブとして working_group に順序を保ったまま差し込む。
                # 直接 primitives に入れると通常プリミティブ（仕切り待ちで working_group に
                # 溜まる）を追い越してしまい、Subtract/Intersect が「土台の無い状態での減算」
                # になって無効化される。逆に working_group を強制確定すると、仕切りによる
                # レイアウト展開（Radial等）待ちのプリミティブが未展開のまま確定されてしまう
                if curve_prims:
                    working_group.append({'prebuilt_prims': curve_prims, 'layer_id': active_layer_id})
                _dbg_mesh(f"curve sync '{c_obj_orig.name}': capsules={len(curve_prims)}, subdiv={subdiv}, r={r_pipe:.4f}")
            except Exception as exc:
                import traceback
                print(f"SDF Curve Sync Error ('{c_obj_orig.name}'): {exc}")
                traceback.print_exc()

        else:
            # プリミティブ
            # Solo判定は他の早期 continue より先に行う（CURVE_SYNC 側と同じ理由）
            if props.use_solo and i > props.sdf_stack_index:
                break
            obj_orig = item.object_ptr
            if not obj_orig:
                continue
            if obj_orig.name == output_obj.name:
                continue

            try:
                obj = obj_orig.evaluated_get(depsgraph)
            except:
                continue

            p_props = getattr(obj_orig, "sdf_props", None)
            if not p_props:
                p_props = getattr(obj, "sdf_props", None)
                
            is_prim = p_props and p_props.is_primitive
            
            local_mat = inv_world_output @ obj.matrix_world
            loc, rot, scale = local_mat.decompose()
            _dbg_layout(
                f"stack[{i}] primitive '{obj_orig.name}': "
                f"loc=({loc.x:.3f},{loc.y:.3f},{loc.z:.3f}), "
                f"scale=({scale.x:.3f},{scale.y:.3f},{scale.z:.3f})"
            )
            
            element = {
                'obj_orig': obj_orig,
                'obj_eval': obj,
                'matrix_world': obj.matrix_world.copy(),
                'p_props': p_props,
                'is_prim': is_prim,
                'loc': loc,
                'rot': rot,
                'scale': scale,
                'layer_id': active_layer_id
            }
            working_group.append(element)
            
    # ループ完了後に残っているものを全てビルドして primitives に追加
    _dbg_mesh(f"loop done, working_group remaining={len(working_group)}")
    _finalize_group_elements(working_group, primitives, auto_domain, inv_world_output, props, max_extent_list)
            
    max_extent = max_extent_list[0]
    _dbg_mesh(f"total primitives={len(primitives)}, max_extent={max_extent:.4f}")
    _dbg_layout(
        f"prepared primitives={len(primitives)}, remaining_working_group={len(working_group)}, "
        f"auto_domain={auto_domain}, max_extent={max_extent:.4f}"
    )
        
    if not primitives:
        _dbg_mesh("NO primitives, returning early")
        return

    # ドメイン設定の最終確定
    if auto_domain:
        # 少しマージンを持たせる (1.1x)
        domain = max(props.domain_size * 2.0, max_extent * 2.4)
    else:
        domain = props.domain_size * 2.0
                
    if not primitives: return

    # --- メッシュ生成ON/OFFスイッチ（V15.9.9 実装） ---
    if not bpy.context.scene.sdf_show_result:
        # メッシュ生成がOFFの場合はRust計算をスキップし、必要ならメッシュを空にする
        if len(output_obj.data.vertices) > 0:
            output_obj.data.clear_geometry()
            output_obj.update_tag()
        _pending_update = False
        return

    # 非同期リクエスト
    try:
        w_thresh = props.weld_threshold if props.use_weld else 0.0
        # リクエストログ (V13.3) - 高速化のためコメントアウト
        algo = "DC" if use_dc else "MC"
        _dbg_layout(
            f"request_mesh_update: algo={algo}, res={res}, domain={domain:.4f}, "
            f"sym_mask={sym_mask}, weld={w_thresh:.6f}"
        )
        # print(f"SDF Debug: Requesting {algo} update (Res: {res}, Domain: {domain:.2f})")
        
        _last_mesh_request = (primitives, res, domain, use_dc, sym_mask, w_thresh)
        _safe_retry_active = False
        _gpu_chunked_mc_active = False
        _gpu_chunked_dc_active = False
        _cpu_chunked_fallback_active = False

        backend = getattr(props, "meshing_backend", 'AUTO')
        chunk_cells = _choose_chunk_cells(res, props.chunked_fallback_cells)
        dc_chunk_cells = _choose_chunk_cells(res, props.chunked_fallback_cells, 64)
        chunk_w_thresh = _chunk_weld_threshold(props, w_thresh)
        requested = False
        auto_high_res_chunk = (
            backend == 'AUTO'
            and props.auto_chunk_high_res
            and res >= props.auto_chunk_start_res
            and (
                hasattr(rust_gpu_sdf, "request_gpu_chunked_mesh_update")
                or hasattr(rust_gpu_sdf, "request_gpu_chunked_dc_update")
            )
        )
        if backend == 'GPU_CHUNKED_DC' and hasattr(rust_gpu_sdf, "request_gpu_chunked_dc_update"):
            _dbg_mesh(f"requesting GPU chunked DC backend (Res: {res}, Chunk: {dc_chunk_cells})")
            requested = rust_gpu_sdf.request_gpu_chunked_dc_update(primitives, res, domain, sym_mask, chunk_w_thresh, dc_chunk_cells)
            _gpu_chunked_dc_active = requested
        elif (backend == 'GPU_CHUNKED_MC' or auto_high_res_chunk) and hasattr(rust_gpu_sdf, "request_gpu_chunked_mesh_update"):
            _dbg_mesh(f"requesting GPU chunked MC backend (Res: {res}, Chunk: {chunk_cells})")
            requested = rust_gpu_sdf.request_gpu_chunked_mesh_update(primitives, res, domain, sym_mask, chunk_w_thresh, chunk_cells)
            _gpu_chunked_mc_active = requested
        elif backend == 'CPU_CHUNKED_MC' and hasattr(rust_gpu_sdf, "request_chunked_mesh_update"):
            _dbg_mesh(f"requesting CPU chunked MC backend (Res: {res}, Chunk: {chunk_cells})")
            requested = rust_gpu_sdf.request_chunked_mesh_update(primitives, res, domain, sym_mask, chunk_w_thresh, chunk_cells)
            _cpu_chunked_fallback_active = requested
        else:
            requested = rust_gpu_sdf.request_mesh_update(primitives, res, domain, use_dc, sym_mask, w_thresh)

        if requested:
            _pending_update = False
            # タイマーがなければ登録
            if not _is_timer_registered:
                bpy.app.timers.register(sdf_mesh_timer, first_interval=0.05)
                _is_timer_registered = True
    except Exception as e:
        print(f"SDF Request Error: {e}")
        if use_dc:
            dc_err = rust_gpu_sdf.get_dc_last_error()
            scene = bpy.context.scene
            if hasattr(scene, "sdf_scene_props"):
                scene.sdf_scene_props.dc_last_error = dc_err or str(e)

def apply_mesh_data(output_obj, data, force_normals=False):
    """計算済みデータをメッシュに適用する"""
    global _pending_update, _safe_retry_active, _gpu_chunked_mc_active, _gpu_chunked_dc_active, _cpu_chunked_fallback_active
    try:
        diagnostics = ""
        scene = bpy.context.scene
        if hasattr(scene, "sdf_scene_props") and hasattr(rust_gpu_sdf, "get_mesh_diagnostics"):
            diagnostics = rust_gpu_sdf.get_mesh_diagnostics()
            scene.sdf_scene_props.mesh_diagnostics = diagnostics

        health = ""
        for part in diagnostics.split(";"):
            part = part.strip()
            if part.startswith("health="):
                health = part.split("=", 1)[1]
                break

        if output_obj.sdf_props.protect_partial_mesh and health in {"CAPACITY_LIMITED", "EMPTY_RESULT"}:
            props = output_obj.sdf_props
            if props.auto_gpu_chunked_fallback and not _gpu_chunked_mc_active and _last_mesh_request and hasattr(rust_gpu_sdf, "request_gpu_chunked_mesh_update"):
                primitives, prev_res, domain, _use_dc, sym_mask, w_thresh = _last_mesh_request
                chunk_cells = _choose_chunk_cells(prev_res, props.chunked_fallback_cells)
                chunk_w_thresh = _chunk_weld_threshold(props, w_thresh)
                print(f"SDF Mesh Protect: falling back to chunked GPU MC at resolution {prev_res}, chunk {chunk_cells}.")
                if rust_gpu_sdf.request_gpu_chunked_mesh_update(primitives, prev_res, domain, sym_mask, chunk_w_thresh, chunk_cells):
                    _gpu_chunked_mc_active = True
                    _pending_update = False
                    return "retry"
            if props.auto_safe_retry and not _safe_retry_active and _last_mesh_request:
                primitives, prev_res, domain, use_dc, sym_mask, w_thresh = _last_mesh_request
                retry_res = max(props.safe_retry_min_res, prev_res // 2)
                if retry_res < prev_res:
                    print(f"SDF Mesh Protect: retrying at lower resolution {retry_res} after {health}.")
                    if rust_gpu_sdf.request_mesh_update(primitives, retry_res, domain, use_dc, sym_mask, w_thresh):
                        _safe_retry_active = True
                        _pending_update = False
                        return "retry"
            if props.auto_chunked_fallback and not _cpu_chunked_fallback_active and _last_mesh_request and hasattr(rust_gpu_sdf, "request_chunked_mesh_update"):
                primitives, prev_res, domain, _use_dc, sym_mask, w_thresh = _last_mesh_request
                chunk_cells = _choose_chunk_cells(prev_res, props.chunked_fallback_cells)
                chunk_w_thresh = _chunk_weld_threshold(props, w_thresh)
                print(f"SDF Mesh Protect: falling back to chunked CPU MC at resolution {prev_res}, chunk {chunk_cells}.")
                if rust_gpu_sdf.request_chunked_mesh_update(primitives, prev_res, domain, sym_mask, chunk_w_thresh, chunk_cells):
                    _cpu_chunked_fallback_active = True
                    _pending_update = False
                    return "retry"
            print(f"SDF Mesh Protect: skipped applying partial mesh ({diagnostics})")
            return "protected"

        verts_raw, indices = data
        if not verts_raw: return "empty"

        # 頂点データの検証と変換 (V13.3 安定化)
        verts_np = np.array(verts_raw, dtype=np.float32)
        if len(verts_np) % 11 != 0:
            print(f"SDF Warning: verts_raw size {len(verts_np)} is not multiple of 11. Truncating.")
            verts_np = verts_np[:(len(verts_np) // 11) * 11]
            
        verts_np = verts_np.reshape(-1, 11)
        # NaN / Inf を安全な数値に置換してクラッシュを物理的に防ぐ
        verts_np = np.nan_to_num(verts_np, nan=0.0, posinf=0.0, neginf=0.0)
        
        # インデックスデータの検証と変換 (V13.3 安定化)
        indices_np = np.array(indices, dtype=np.int32)
        if len(indices_np) % 3 != 0:
            extra = len(indices_np) % 3
            print(f"SDF Warning: indices size {len(indices_np)} is not multiple of 3. Extra elements: {indices_np[-extra:].tolist()}. Truncating.")
            indices_np = indices_np[:(len(indices_np) // 3) * 3]

        import time
        t_start = time.perf_counter()
        
        mesh = output_obj.data
        mesh.clear_geometry()
        
        # 面データの生成 (foreach_set による高速化)
        try:
            v_count = len(verts_np)
            f_count = len(indices_np) // 3
            
            mesh.vertices.add(v_count)
            mesh.vertices.foreach_set("co", verts_np[:, 0:3].ravel())
            
            mesh.loops.add(len(indices_np))
            mesh.loops.foreach_set("vertex_index", indices_np)
            
            mesh.polygons.add(f_count)
            mesh.polygons.foreach_set("loop_start", np.arange(0, len(indices_np), 3, dtype=np.int32))
            mesh.polygons.foreach_set("loop_total", np.full(f_count, 3, dtype=np.int32))
            
        except Exception as pydata_err:
            print(f"SDF Mesh creation error (fast path): {pydata_err}")
            return "error"

        # 重要: 属性や法線を設定する前に、一度 update() を呼んで Blender 内部のメモリを確定させる
        # これを怠ると、高解像度時にアクセス違反（クラッシュ）の原因になる
        mesh.update()

        # 属性の設定
        colors_rgb = verts_np[:, 3:6]
        colors_rgba = np.hstack([colors_rgb, np.ones((colors_rgb.shape[0], 1), dtype=np.float32)]).flatten()
        metallic_data = verts_np[:, 6]
        roughness_data = verts_np[:, 7]

        if "Color" not in mesh.attributes:
            mesh.attributes.new(name="Color", type='FLOAT_COLOR', domain='POINT')
        mesh.attributes["Color"].data.foreach_set("color", colors_rgba)

        if "Metallic" not in mesh.attributes:
            mesh.attributes.new(name="Metallic", type='FLOAT', domain='POINT')
        mesh.attributes["Metallic"].data.foreach_set("value", metallic_data)

        if "Roughness" not in mesh.attributes:
            mesh.attributes.new(name="Roughness", type='FLOAT', domain='POINT')
        mesh.attributes["Roughness"].data.foreach_set("value", roughness_data)
        
        # 重要: 法線を設定する前に再度 update() して整合性を確保 (V13.5 安定化)
        mesh.update()

        # スムーズシェーディングの設定
        if mesh.polygons:
            mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))

        # カスタム法線の適用 (Attribute API により全解像度で安全に適用可能)
        if mesh.loops and len(mesh.loops) > 0 and (output_obj.sdf_props.use_live_normals or force_normals):
                try:
                    # 法線データの準備
                    normals_flat = verts_np[:, 8:11].astype(np.float32)
                    normals_flat = np.nan_to_num(normals_flat)
                    
                    v_indices = np.empty(len(mesh.loops), dtype=np.int32)
                    mesh.loops.foreach_get("vertex_index", v_indices)
                    v_indices = np.clip(v_indices, 0, len(normals_flat) - 1)
                    final_loop_normals = normals_flat[v_indices]
                    
                    if len(final_loop_normals) > 0:
                        # --- Blender 4.1 / 5.0 対応: Attribute API を使用した高速・安全な適用 ---
                        if bpy.app.version >= (4, 1, 0):
                            # カスタム法線属性を直接操作（旧APIによるクラッシュを回避）
                            if "normals" not in mesh.attributes:
                                mesh.attributes.new(name="normals", type='FLOAT_VECTOR', domain='CORNER')
                            
                            # データを1次元化して一括転送
                            mesh.attributes["normals"].data.foreach_set("vector", final_loop_normals.ravel())
                            
                            # 更新通知
                            mesh.update()
                        else:
                            # 旧API (Blender 4.0以前)
                            normals_to_apply = final_loop_normals.tolist()
                            if hasattr(mesh, "normals_split_custom_clear"):
                                mesh.normals_split_custom_clear()
                            mesh.normals_split_custom_set(normals_to_apply)
                except Exception as normal_err:
                    print(f"SDF Normal Apply Warning (Attribute Path): {normal_err}")
        elif mesh.loops and not output_obj.sdf_props.use_live_normals:
            if hasattr(mesh, "normals_split_custom_clear"):
                mesh.normals_split_custom_clear()
        elif mesh.loops and not output_obj.sdf_props.use_live_normals:
            if hasattr(mesh, "normals_split_custom_clear"):
                mesh.normals_split_custom_clear()
            
        # 最後にタグを更新
        output_obj.update_tag()
        
        # 適用時間のログ (デバッグ用)
        # print(f"SDF Debug: Mesh Applied in {(time.perf_counter() - t_start)*1000:.2f} ms")
        
    except Exception as e:
        print(f"SDF Apply Error: {e}")
        return "error"

    _safe_retry_active = False
    _gpu_chunked_mc_active = False
    _gpu_chunked_dc_active = False
    _cpu_chunked_fallback_active = False
    return "applied"

def sdf_mesh_timer():
    """バックグラウンド計算が終わったか監視するタイマー"""
    global _pending_update, _is_timer_registered, _force_next_normals
    
    try:
        # 結果をチェック
        data = rust_gpu_sdf.fetch_mesh_if_ready()
        if data:
            # ターゲットオブジェクトを見つける
            retry_requested = False
            for obj in bpy.context.scene.objects:
                if obj.sdf_props.is_output:
                    result = apply_mesh_data(obj, data, force_normals=_force_next_normals)
                    retry_requested = retry_requested or result == "retry"
                    obj.update_tag() 
            if retry_requested:
                return 0.05
            
            _force_next_normals = False # フラグをリセット
            
            # ビューポートを強制再描画
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
            
            # もしペンディングがあれば、即座に次のリクエストを投げる
            if _pending_update:
                for obj in bpy.context.scene.objects:
                    if obj.sdf_props.is_output:
                        update_sdf_mesh(obj)
                        # 次の計算結果を待つためにタイマーを継続させる
                        return 0.05
            
            _is_timer_registered = False
            return None # 予定がなければ終了
            
        # 計算中なら継続
        if rust_gpu_sdf.is_updating():
            return 0.05
            
        # 計算が止まっているが結果もない場合（エラーまたはキャンセル等）
        # V15.9.9.1: DCシェーダーのコンパイル失敗がこの無言スキップの原因であることが多いため、
        # 診断文字列が残っていればシーンプロパティへ反映し、UI側で確認できるようにする
        dc_err = rust_gpu_sdf.get_dc_last_error()
        if dc_err:
            _dbg_mesh(f"DC last error present: {dc_err}")
            scene = bpy.context.scene
            if hasattr(scene, "sdf_scene_props"):
                scene.sdf_scene_props.dc_last_error = dc_err

        # もし更新予約があれば再試行
        if _pending_update:
            for obj in bpy.context.scene.objects:
                if obj.sdf_props.is_output:
                    update_sdf_mesh(obj)
                    return 0.05

        _is_timer_registered = False
        return None
        
    except Exception as e:
        print(f"SDF Timer Error: {e}")
        _is_timer_registered = False
        return None

def update_sdf_callback(self, context):
    # V15.9.9.4: プロパティ変更はプレビュー見た目にも影響するのでキャッシュを無効化
    try:
        from . import handlers
        handlers.mark_preview_dirty()
    except Exception:
        pass
    if context.scene.sdf_live_update:
        for obj in context.scene.objects:
            if obj.sdf_props.is_output:
                update_sdf_mesh(obj)

def trigger_normal_update(obj):
    """手動で法線を更新するためのトリガー"""
    global _force_next_normals
    _force_next_normals = True
    update_sdf_mesh(obj)

def _update_preview(self, context):
    """プレビュー切替時にビューポートを即座に再描画"""
    # V15.9.9.4: preview_quality 等の変更を反映するためキャッシュを無効化
    try:
        from . import handlers
        handlers.mark_preview_dirty()
    except Exception:
        pass
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()

def sync_sdf_parents(output_obj):
    """SDFスタックの順序に基づいて、プリミティブオブジェクトの親子関係(Parenting)を動的に繋ぎ替える"""
    if not output_obj or not output_obj.sdf_props.is_output:
        return
        
    props = output_obj.sdf_props
    stack = props.sdf_stack
    
    current_parent = None
    
    for i in range(len(stack) - 1, -1, -1):
        item = stack[i]
        if item.item_type == 'COLLECTION':
            # 仕切りに遭遇したら、これより上のプリミティブの親はこれになる
            current_parent = item.empty_ptr
        else:
            obj = item.object_ptr
            if obj:
                # すでに正しい親になっているかチェック
                if obj.parent != current_parent:
                    # ワールド座標を維持してペアレント関係を更新
                    try:
                        old_matrix = obj.matrix_world.copy()
                        
                        if current_parent:
                            if current_parent != obj:
                                # 循環関係チェック
                                parent_chain = []
                                temp = current_parent
                                while temp is not None:
                                    parent_chain.append(temp)
                                    temp = temp.parent
                                    if temp == obj:
                                        # 循環が検知されたらペアレントしない
                                        break
                                else:
                                    obj.parent = current_parent
                                    obj.matrix_parent_inverse = current_parent.matrix_world.inverted()
                        else:
                            obj.parent = None
                            
                        obj.matrix_world = old_matrix
                    except Exception as parent_err:
                        print(f"SDF parenting error for {obj.name}: {parent_err}")

