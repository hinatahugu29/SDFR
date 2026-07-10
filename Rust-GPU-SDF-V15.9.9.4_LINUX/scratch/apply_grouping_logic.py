import re
import os

engine_path = r"e:\blender_addon\外部テスト\Rust-GPU-SDF-V15.9.8.1\rust_gpu_sdf_addon\engine.py"

with open(engine_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 置き換える新しいループコードとヘルパー関数の定義
# update_sdf_mesh 関数の primitives = [] の手前にヘルパー関数を挿入する。
# また、primitives = [] から primitives.append(p) までのループを新しい展開ループに置き換える。

helper_and_loop_code = """
def build_element_primitive(el, auto_domain, inv_world_output, props, max_extent):
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
            max_s = max(scale.x, scale.y, scale.z)
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

    sym_loc = [abs(loc.x) if props.sym_x else loc.x, abs(loc.y) if props.sym_y else loc.y, abs(loc.z) if props.sym_z else loc.z]
    size = (scale.x, scale.y, scale.z)
    
    return rust_gpu_sdf.SdfPrimitive(
        shape, sym_loc, [rot.x, rot.y, rot.z, rot.w], radius, size, op_int, smoothness, 
        color=color, metallic=metallic, roughness=roughness, noise_strength=noise_strength, noise_scale=noise_scale,
        layout_data1=layout_data1, layout_data2=layout_data2, 
        layout_data3=layout_data3, layout_data4=layout_data4,
        extra_params=extra_params,
        deform_data1=deform_data1, deform_data2=deform_data2,
        deform_data3=deform_data3, deform_data4=deform_data4,
        blend_profile=blend_prof,
        chamfer_smooth=cham_smooth,
        edge_profile=edge_profile,
        edge_chamfer_smooth=edge_chamfer_smooth,
        shell_thickness=shell_thickness,
        edge_profile_size=edge_profile_size
    )

def update_sdf_mesh(output_obj, depsgraph=None):
"""

content = content.replace("def update_sdf_mesh(output_obj, depsgraph=None):", helper_and_loop_code)

# 2. ループ部分の置換
# primitives = [] から primitives.append(p) の終わり（forループ終了）までを抽出して置換する。

loop_pattern = r"    primitives = \[\]\s+for i, item in enumerate\(props\.sdf_stack\):.*?primitives\.append\(p\)"
# re.DOTALL を使用して複数行にまたがるマッチングを行う

new_loop_code = """    primitives = []
    working_group = []
    max_extent_list = [max_extent] # 参照渡し用のリスト

    for i, item in enumerate(props.sdf_stack):
        if not item.enabled:
            continue
            
        if item.item_type == 'COLLECTION':
            empty_obj = item.empty_ptr
            if not empty_obj:
                continue
                
            try:
                empty_eval = empty_obj.evaluated_get(depsgraph)
            except:
                empty_eval = empty_obj
                
            empty_props = getattr(empty_obj, "sdf_props", None)
            if not empty_props:
                continue
                
            # レイアウト行列リスト
            layout_mats = get_layout_matrices(empty_props)
            
            expanded_group = []
            P = empty_eval.matrix_world
            try:
                P_inv = P.inverted()
            except:
                P_inv = Matrix.Identity(4)
                
            for element in working_group:
                # 親から見た相対トランスフォームの計算
                C = element['matrix_world']
                L = P_inv @ C
                
                # レイアウト展開
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
                    
            if item.start_new_group:
                # 独立グループなので、ここで primitives に確定追加してリセット
                for el in expanded_group:
                    p = build_element_primitive(el, auto_domain, inv_world_output, props, max_extent_list)
                    if p:
                        primitives.append(p)
                working_group = []
            else:
                # 入れ子として作業グループを引き継ぐ
                working_group = expanded_group
                
        else:
            # プリミティブ
            obj_orig = item.object_ptr
            if not obj_orig:
                continue
            if obj_orig.name == output_obj.name:
                continue
            if props.use_solo and i > props.sdf_stack_index:
                break
                
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
            
            element = {
                'obj_orig': obj_orig,
                'obj_eval': obj,
                'matrix_world': obj.matrix_world.copy(),
                'p_props': p_props,
                'is_prim': is_prim,
                'loc': loc,
                'rot': rot,
                'scale': scale
            }
            working_group.append(element)
            
    # ループ完了後に残っているものを全てビルドして primitives に追加
    for el in working_group:
        p = build_element_primitive(el, auto_domain, inv_world_output, props, max_extent_list)
        if p:
            primitives.append(p)
            
    max_extent = max_extent_list[0]"""

# 慎重に正規表現で置換する
# re.sub で、primitives = [] の定義から primitives.append(p) までのループ部分全体を置換
content, count = re.subn(loop_pattern, new_loop_code, content, flags=re.DOTALL)
print(f"Substituted loops count: {count}")

with open(engine_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Done rewrite.")
