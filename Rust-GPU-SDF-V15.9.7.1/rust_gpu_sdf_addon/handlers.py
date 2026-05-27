import bpy
import gpu
import mathutils
import math
from gpu_extras.batch import batch_for_shader
from .shader import get_shader
from .engine import update_sdf_mesh, sync_sdf_stack
from .constants import _SHAPE_MAP, _fsq_coords, _fsq_indices

_batch = None

def _compute_preview_domain_size(output_obj, o_props, inv_world_output):
    """Return effective preview domain size in local space (same unit as shader domainSize)."""
    base_domain = o_props.domain_size * 2.0
    if not getattr(o_props, "auto_domain", False):
        return base_domain

    max_extent = 0.001
    for i, item in enumerate(o_props.sdf_stack):
        if not item.enabled or not item.object_ptr:
            continue
        if o_props.use_solo and i > o_props.sdf_stack_index:
            break

        o = item.object_ptr
        if o.name == output_obj.name:
            continue

        local_matrix = inv_world_output @ o.matrix_world
        loc, _, sc = local_matrix.decompose()
        p_props = getattr(o, "sdf_props", None)

        max_s = max(sc.x, sc.y, sc.z)
        smoothness = getattr(p_props, "smoothness", 0.2) if p_props else 0.2
        noise_strength = getattr(p_props, "noise_strength", 0.0) if p_props else 0.0
        shape_extent = getattr(p_props, "radius", 1.0) if p_props else 1.0

        if p_props and p_props.is_primitive:
            shape = p_props.shape_type
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
            elif shape == 'rounded_box':
                shape_extent = max(p_props.radius, 1.0 + p_props.p1)
            elif shape == 'ellipsoid':
                shape_extent = max(p_props.p1, p_props.p2, p_props.p3)
            elif shape == 'rounded_cylinder':
                shape_extent = max(p_props.p1, p_props.p3 + p_props.p2)
            elif shape == 'capped_torus':
                shape_extent = p_props.p1 + p_props.p2
            elif shape == 'octahedron':
                shape_extent = p_props.p1
            elif shape == 'cut_sphere':
                shape_extent = p_props.radius

        prim_r = (max_s * shape_extent) + (smoothness + noise_strength) * max_s

        layout_r = 0.0
        if p_props and p_props.is_primitive:
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

        dist_from_origin = math.sqrt(loc.x * loc.x + loc.y * loc.y + loc.z * loc.z)
        max_extent = max(max_extent, dist_from_origin + layout_r + prim_r)

    auto_domain = max_extent * 2.4
    return max(base_domain, auto_domain)

def draw_callback_3d(self, context):
    """ビューポートにレイマーチングオーバーレイを描画"""
    global _batch
    if context is None: context = bpy.context
    try:
        scene = context.scene
        if not scene.sdf_live_update or not getattr(scene, "sdf_show_preview", True):
            return
    except Exception:
        return
    shader = get_shader()
    if not shader: return

    prim_data = []
    output_obj = None
    target_col = None
    for o in scene.objects:
        props = getattr(o, "sdf_props", None)
        if props and props.is_output:
            output_obj = o
            target_col = props.target_collection
            break
        
    if not output_obj or not target_col: return

    inv_world_output = output_obj.matrix_world.inverted()

    # V7: スタック順序に従う
    sync_sdf_stack(output_obj)
    
    o_props = output_obj.sdf_props
    for i, item in enumerate(o_props.sdf_stack):
        if not item.enabled or not item.object_ptr:
            continue
        o = item.object_ptr
        if o.name == output_obj.name: 
            continue
            
        # V7: ソロモード対応
        if o_props.use_solo and i > o_props.sdf_stack_index:
            break
            
        p_props = getattr(o, "sdf_props", None)
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

        local_matrix = inv_world_output @ o.matrix_world
        loc, rot, sc = local_matrix.decompose()
        
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
            
            # Pack1: mode(8) | mask(4) | count(8) | axis(4)
            # 8bit: mode(flags)
            # 4bit: mirror_mask (8-11)
            # 8bit: radial_count (12-19)
            # 2bit: radial_axis (20-21)
            packed1 = float(mode_flags | (mirror_mask << 8) | (radial_count << 12) | (radial_axis << 20))
            
            # Grid Count Packing: X + 100*Y + 10000*Z
            grid_packed = float(p_props.grid_count_x + 100 * p_props.grid_count_y + 10000 * p_props.grid_count_z)
            
            ld1 = [packed1, p_props.mirror_offset, p_props.radial_radius, p_props.spiral_pitch]
            ld2 = [p_props.jitter_seed, p_props.jitter_strength, grid_packed, p_props.grid_spacing_x]
            ld3 = [p_props.grid_spacing_y, p_props.grid_spacing_z, p_props.instance_rot_x, p_props.instance_rot_y]
            ld4 = [p_props.instance_rot_z, p_props.step_rot_x, p_props.step_rot_y, p_props.step_rot_z]
            
            # --- V15: Deform Stack Packing ---
            # パッキング方針:
            #   deform_data1.x = packed_meta (全スロットのtype+axisを6bitずつ格納)
            #   残り15 floats: 各スロット4パラメータ × 最大4スロット (slot3のparam[3]は省略)
            #   配置: dd1.yzw = slot0[0..2], dd2.x = slot0[3]
            #         dd2.yzw = slot1[0..2], dd3.x = slot1[3]
            #         dd3.yzw = slot2[0..2], dd4.x = slot2[3]
            #         dd4.yzw = slot3[0..2]  (slot3[3]は0として扱う)
            #   Elongate: params = [stretch_x, stretch_y, stretch_z, 0]
            #   Bend/Twist/Taper: params = [factor, ox, oy, oz]
            _DEFORM_TYPE_MAP = {'ELONGATE': 1, 'BEND': 2, 'TWIST': 3, 'TAPER': 4}
            packed_meta = 0
            slot_params = [[0.0]*4, [0.0]*4, [0.0]*4, [0.0]*4]
            for si, d_item in enumerate(p_props.deform_stack):
                if si >= 4:
                    break
                if not d_item.enabled:
                    continue
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
        else:
            ld1 = [0.0] * 4
            ld2 = [0.0] * 4
            ld3 = [0.0] * 4
            ld4 = [0.0] * 4
            dd1 = [0.0] * 4
            dd2 = [0.0] * 4
            dd3 = [0.0] * 4
            dd4 = [0.0] * 4

        # 0: center_and_shape
        prim_data.extend([sym_loc[0], sym_loc[1], sym_loc[2], shape_type])
        # 1: rotation
        prim_data.extend([rot.x, rot.y, rot.z, rot.w])
        # 2: size_and_op
        radius = 0.0
        size = (sc.x, sc.y, sc.z)
        extra_p = [0.0, 0.0, 0.0, 0.0]
        
        if p_props and p_props.is_primitive:
            radius = p_props.radius
            extra_p = [p_props.p1, p_props.p2, p_props.p3, p_props.p4]
            if p_props.shape_type == 'ngon_prism':
                extra_p[1] = float(p_props.ngon_sides)
        else:
            # 非プリミティブの場合のフォールバック
            if shape_type == 0.0: radius = sc.x
            elif shape_type == 2.0: radius = sc.z
            elif shape_type == 3.0: radius = sc.x

        prim_data.extend([size[0], size[1], size[2], op_type])
        # 3: params [radius, smoothness, metallic, roughness]
        prim_data.extend([radius, smoothness, metallic, roughness])
        # 4: noise_params [str, scale, r, g]
        prim_data.extend([noise_strength, noise_scale, color[0], color[1]])
        # 5: color_b_and_extra [b, ...]
        prim_data.extend([color[2], 0.0, 0.0, 0.0])
        # 6-9: layouts
        prim_data.extend(ld1)
        prim_data.extend(ld2)
        prim_data.extend(ld3)
        prim_data.extend(ld4)
        # 10: extra_params (V13)
        prim_data.extend(extra_p)
        # 11-14: deform_data (V14)
        prim_data.extend(dd1)
        prim_data.extend(dd2)
        prim_data.extend(dd3)
        prim_data.extend(dd4)
        # 15: modifier_params (V16)
        if p_props and p_props.is_primitive:
            prim_data.extend([float(p_props.edge_profile), p_props.shell_thickness, p_props.edge_chamfer_smooth, p_props.edge_profile_size])
        else:
            prim_data.extend([0.0, 0.0, 0.0, 0.0])

    if not prim_data: return
    # V16: 16 pixels per primitive (64 floats)
    prim_count = len(prim_data) // 64

    if _batch is None:
        _batch = batch_for_shader(shader, 'TRIS', {"pos": _fsq_coords}, indices=_fsq_indices)
    
    rv3d = context.region_data
    if not rv3d: return
    
    inv_proj_view_local = inv_world_output @ rv3d.perspective_matrix.inverted()

    gpu.state.blend_set('ALPHA')
    gpu.state.depth_test_set('ALWAYS')
    gpu.state.face_culling_set('NONE')
    shader.bind()
    try:
        shader.uniform_float("invProjViewLocal", inv_proj_view_local)
        domain_size = _compute_preview_domain_size(output_obj, o_props, inv_world_output)
        shader.uniform_float("domainSize", domain_size)
        shader.uniform_int("primCount", prim_count)
        
        sym_mask = (1 if output_obj.sdf_props.sym_x else 0) | \
                   (2 if output_obj.sdf_props.sym_y else 0) | \
                   (4 if output_obj.sdf_props.sym_z else 0)
        shader.uniform_int("symmetryFlags", sym_mask)
        
        # 描画品質（ステップ数）の決定
        q_map = {'LOW': 128, 'MID': 256, 'HIGH': 512}
        max_steps = q_map.get(output_obj.sdf_props.preview_quality, 256)
        auto_steps = int(domain_size * 24.0)
        max_steps = max(max_steps, min(auto_steps, 2048))
        shader.uniform_int("maxSteps", max_steps)
        
        data_buf = gpu.types.Buffer('FLOAT', len(prim_data), prim_data)
        prim_tex = gpu.types.GPUTexture((16, prim_count), format='RGBA32F', data=data_buf)
        shader.uniform_sampler("primTex", prim_tex)
        _batch.draw(shader)
    except Exception as e:
        print(f"SDF Draw Error: {e}")
        import traceback; traceback.print_exc()
    gpu.state.blend_set('NONE')
    gpu.state.depth_test_set('LESS_EQUAL')
    gpu.state.face_culling_set('BACK')

def sdf_depsgraph_handler(scene, depsgraph):
    if getattr(sdf_depsgraph_handler, "_is_running", False): return

    # 1. 選択状態の同期 (Viewport -> UI List)
    # これは Live Update の ON/OFF に関わらず実行する
    active_obj = bpy.context.active_object
    if active_obj:
        active_orig = active_obj.original if hasattr(active_obj, "original") else active_obj
        for obj in bpy.data.objects:
            props = getattr(obj, "sdf_props", None)
            if props and props.is_output:
                for i, item in enumerate(props.sdf_stack):
                    if item.object_ptr and item.object_ptr.name == active_orig.name:
                        if props.sdf_stack_index != i:
                            props.sdf_stack_index = i
                        break

    # 2. メッシュの更新判定 (Live Update が ON の場合のみ)
    if not scene.sdf_live_update: return

    is_relevant = False
    for update in depsgraph.updates:
        id_orig = update.id.original if hasattr(update.id, "original") else update.id
        if isinstance(id_orig, bpy.types.Object):
            p = getattr(id_orig, "sdf_props", None)
            if p and (p.is_primitive or (p.is_output and update.is_updated_transform)):
                is_relevant = True
            if not is_relevant:
                for o in scene.objects:
                    out_p = getattr(o.original, "sdf_props", None)
                    if out_p and out_p.is_output and out_p.target_collection:
                        if id_orig.name in out_p.target_collection.objects:
                            is_relevant = True; break
        if is_relevant: break

    if is_relevant:
        sdf_depsgraph_handler._is_running = True
        try:
            # メッシュの更新
            for obj_orig in scene.objects:
                props = getattr(obj_orig.original, "sdf_props", None)
                if props and props.is_output and obj_orig.mode == 'OBJECT':
                    update_sdf_mesh(obj_orig, depsgraph=depsgraph)
        except Exception as e:
            print(f"SDF Handler Error: {e}")
        finally:
            sdf_depsgraph_handler._is_running = False

def sdf_undo_handler(scene):
    """Undo/Redo 時に状態ハッシュキャッシュをクリアし、再計算を強制する"""
    from . import engine
    engine._last_state_hashes.clear()
    # 必要に応じて即座に更新をトリガー
    for obj in scene.objects:
        if getattr(obj, "sdf_props", None) and obj.sdf_props.is_output:
            engine.update_sdf_mesh(obj)

def clear_batch():
    global _batch
    _batch = None
