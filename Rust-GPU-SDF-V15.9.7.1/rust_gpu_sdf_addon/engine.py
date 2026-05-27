import bpy
import numpy as np
from . import rust_gpu_sdf

# -------------------------------------------------------------------------
# Rust メッシュ生成・同期ロジック
# -------------------------------------------------------------------------

# 非同期更新管理用 (V10.3)
_pending_update = False
_is_timer_registered = False
_force_next_normals = False

# 状態キャッシュ (V11.2): { "object_name": state_hash }
_last_state_hashes = {}

def get_sdf_state_fingerprint(output_obj, depsgraph):
    """現在の全オブジェクトの状態をハッシュ化して返す"""
    props = output_obj.sdf_props
    state = [
        props.resolution,
        props.domain_size,
        props.algo_type,
        props.sym_x, props.sym_y, props.sym_z,
        props.use_solo, props.sdf_stack_index
    ]
    
    # 全スタックの状態を収集
    for i, item in enumerate(props.sdf_stack):
        if not item.enabled or not item.object_ptr:
            state.append((i, False))
            continue
        
        obj_orig = item.object_ptr
        try:
            # 評価済みオブジェクトから行列を取得
            obj_eval = obj_orig.evaluated_get(depsgraph)
            state.append(tuple(tuple(row) for row in obj_eval.matrix_world))
        except:
            continue
            
        p_props = getattr(obj_orig, "sdf_props", None)
        if p_props and p_props.is_primitive:
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
                p_props.layout_use_mirror, p_props.layout_use_radial, p_props.layout_use_spiral, p_props.layout_use_jitter, p_props.layout_use_grid,
                p_props.mirror_x, p_props.mirror_y, p_props.mirror_z,
                p_props.mirror_offset,
                p_props.radial_count, p_props.radial_radius, p_props.radial_axis,
                p_props.spiral_pitch, p_props.jitter_seed, p_props.jitter_strength,
                p_props.grid_count_x, p_props.grid_count_y, p_props.grid_count_z,
                p_props.grid_spacing_x, p_props.grid_spacing_y, p_props.grid_spacing_z,
                p_props.instance_rot_x, p_props.instance_rot_y, p_props.instance_rot_z,
                p_props.step_rot_x, p_props.step_rot_y, p_props.step_rot_z,
                tuple((d.deform_type, d.axis, d.factor, tuple(d.origin), d.elongate_x, d.elongate_y, d.elongate_z, d.enabled) for d in p_props.deform_stack),
                p_props.radius,
                p_props.p1, p_props.p2, p_props.p3, p_props.p4,
                p_props.ngon_sides,
                p_props.edge_profile,
                p_props.edge_profile_size,
                p_props.edge_chamfer_smooth,
                p_props.shell_thickness
            ))
        else:
            state.append(obj_orig.name)
            
    return hash(tuple(state))

def sync_sdf_stack(output_obj):
    """SDF_Collection と sdf_stack を同期する"""
    props = output_obj.sdf_props
    col = props.target_collection
    if not col: return
    
    # 現在のリストにあるオブジェクトのセット
    existing_objs = {item.object_ptr for item in props.sdf_stack if item.object_ptr}
    
    # コレクションにあってリストにないものを追加
    for obj in col.objects:
        if obj.name == output_obj.name: continue
        if obj not in existing_objs:
            item = props.sdf_stack.add()
            item.object_ptr = obj
            
    # リストにあってコレクションにない（または削除された）ものを削除
    for i in range(len(props.sdf_stack) - 1, -1, -1):
        item = props.sdf_stack[i]
        if not item.object_ptr or item.object_ptr.name not in col.objects:
            props.sdf_stack.remove(i)

def update_sdf_mesh(output_obj, depsgraph=None):
    global _pending_update, _is_timer_registered, _last_state_hashes
    if not output_obj or not output_obj.sdf_props.is_output or not output_obj.sdf_props.target_collection:
        return
    
    if not depsgraph:
        depsgraph = bpy.context.evaluated_depsgraph_get()
    
    # 常に最新のリストを保つ (V11.2)
    sync_sdf_stack(output_obj)
    
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
    for i, item in enumerate(props.sdf_stack):
        if not item.enabled or not item.object_ptr: continue
        obj_orig = item.object_ptr
        if obj_orig.name == output_obj.name: continue
        if props.use_solo and i > props.sdf_stack_index: break
        try:
            obj = obj_orig.evaluated_get(depsgraph)
        except: continue
        # プロパティ取得（UIの最新状態を反映するため original から優先取得）
        # 行列（matrix_world）は引き続き evaluated から取得することで、制約等は維持される
        p_props = getattr(obj_orig, "sdf_props", None)
        if not p_props:
            p_props = getattr(obj, "sdf_props", None)
            
        is_prim = p_props and p_props.is_primitive
        
        # 行列計算
        local_mat = inv_world_output @ obj.matrix_world
        loc, rot, scale = local_mat.decompose()
        
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
            
            # 決定的なデバッグ出力
            if shape == "sphere":
                print(f"SDF Python Debug: Sphere Radius detected as {radius:.4f}")
            
            # --- Auto Domain Logic (V15.9.1: Shape-Aware Expansion) ---
            if auto_domain:
                max_s = max(scale.x, scale.y, scale.z)
                
                # 形状ごとの最大半径（ローカル空間）を計算
                if shape == 'torus':
                    # Main Radius + Pipe Radius
                    shape_extent = p_props.p1 + p_props.p2
                elif shape in ('cylinder', 'capsule', 'hex_prism'):
                    # Radius (p1) or Height (Half-height is p2)
                    shape_extent = max(p_props.p1, p_props.p2)
                elif shape == 'capped_cone':
                    # max(Bottom Radius, Top Radius, Height)
                    shape_extent = max(p_props.p1, p_props.p2, p_props.p3)
                elif shape == 'pyramid':
                    # max(Base, Height)
                    shape_extent = max(p_props.p1, p_props.p2)
                elif shape == 'ngon_prism':
                    # max(Radius, Height)
                    shape_extent = max(p_props.p1, p_props.p3)
                elif shape == 'ellipsoid':
                    # max(Radius X, Radius Y, Radius Z)
                    shape_extent = max(p_props.p1, p_props.p2, p_props.p3)
                elif shape == 'rounded_cylinder':
                    # max(Radius + Edge, Height)
                    shape_extent = max(p_props.p1 + p_props.p2, p_props.p3)
                elif shape == 'capped_torus':
                    # Main Radius + Pipe Radius
                    shape_extent = p_props.p1 + p_props.p2
                elif shape == 'octahedron':
                    # Size
                    shape_extent = p_props.p1
                elif shape == 'cut_sphere':
                    # Radius
                    shape_extent = radius
                else:
                    # sphere, box, rounded_boxなどは共通の radius プロパティを使用
                    shape_extent = radius
                
                # スケールと膨張（滑らかさ、ノイズ）を考慮
                prim_r = (max_s * shape_extent) + (smoothness + noise_strength) * max_s
                p_center = loc
                
                # レイアウトによる広がり
                layout_r = 0.0
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
                
                # 中心からの最大距離
                dist_from_origin = np.sqrt(p_center.x**2 + p_center.y**2 + p_center.z**2)
                max_extent = max(max_extent, dist_from_origin + layout_r + prim_r + deform_r)

            # V12 Phase 2: Layout Stacking (16-slot Packing)
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
            p1_int = int(mode_flags | (mirror_mask << 8) | (radial_count << 12) | (radial_axis << 20))
            packed1 = float(p1_int)
            
            # Grid Count Packing: X + 100*Y + 10000*Z
            g_int = int(p_props.grid_count_x + 100 * p_props.grid_count_y + 10000 * p_props.grid_count_z)
            grid_packed = float(g_int)
            
            layout_data1 = [
                packed1,
                p_props.mirror_offset,
                p_props.radial_radius,
                p_props.spiral_pitch
            ]
            layout_data2 = [
                p_props.jitter_seed,
                p_props.jitter_strength,
                grid_packed,
                p_props.grid_spacing_x
            ]
            layout_data3 = [
                p_props.grid_spacing_y,
                p_props.grid_spacing_z,
                p_props.instance_rot_x,
                p_props.instance_rot_y
            ]
            layout_data4 = [
                p_props.instance_rot_z,
                p_props.step_rot_x,
                p_props.step_rot_y,
                p_props.step_rot_z
            ]
            extra_params = [p_props.p1, p_props.p2, p_props.p3, p_props.p4]
            if shape == 'ngon_prism':
                extra_params[1] = float(p_props.ngon_sides)
            
            # --- V15: Deform Stack Packing ---
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
            
            deform_data1 = [float(packed_meta), slot_params[0][0], slot_params[0][1], slot_params[0][2]]
            deform_data2 = [slot_params[0][3], slot_params[1][0], slot_params[1][1], slot_params[1][2]]
            deform_data3 = [slot_params[1][3], slot_params[2][0], slot_params[2][1], slot_params[2][2]]
            deform_data4 = [slot_params[2][3], slot_params[3][0], slot_params[3][1], slot_params[3][2]]
            
        else:
            name_lower = obj_orig.name.lower()
            if 'sphere' in name_lower: shape = 'sphere'
            elif 'box' in name_lower or 'cube' in name_lower: shape = 'box'
            elif 'torus' in name_lower: shape = 'torus'
            elif 'cylinder' in name_lower: shape = 'cylinder'
            else: continue
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
            
            if auto_domain:
                max_s = max(scale.x, scale.y, scale.z)
                prim_r = max_s * 1.5 # 安全マージン
                max_extent = max(max_extent, np.sqrt(loc.x**2 + loc.y**2 + loc.z**2) + prim_r)

        sym_loc = [abs(loc.x) if props.sym_x else loc.x, abs(loc.y) if props.sym_y else loc.y, abs(loc.z) if props.sym_z else loc.z]
        size = (scale.x, scale.y, scale.z)
        print(f"SDF Debug (Python): Shape={shape}, Radius={radius:.4f}, Scale={size}")

        p = rust_gpu_sdf.SdfPrimitive(
            shape, sym_loc, [rot.x, rot.y, rot.z, rot.w], radius, size, op_int, smoothness, 
            color=color, metallic=metallic, roughness=roughness, noise_strength=noise_strength, noise_scale=noise_scale,
            layout_data1=layout_data1, layout_data2=layout_data2, 
            layout_data3=layout_data3, layout_data4=layout_data4,
            extra_params=extra_params,
            deform_data1=deform_data1, deform_data2=deform_data2,
            deform_data3=deform_data3, deform_data4=deform_data4,
            blend_profile=int(p_props.blend_profile) if is_prim else blend_prof,
            chamfer_smooth=p_props.chamfer_smooth if is_prim else cham_smooth,
            edge_profile=int(p_props.edge_profile) if is_prim else 0,
            edge_chamfer_smooth=p_props.edge_chamfer_smooth if is_prim else 0.0,
            shell_thickness=p_props.shell_thickness if is_prim else 0.0,
            edge_profile_size=p_props.edge_profile_size if is_prim else 0.0
        )
        primitives.append(p)
        
    if not primitives: return

    # ドメイン設定の最終確定
    if auto_domain:
        # 少しマージンを持たせる (1.1x)
        domain = max(props.domain_size * 2.0, max_extent * 2.4)
    else:
        domain = props.domain_size * 2.0
                
    if not primitives: return

    # 非同期リクエスト
    try:
        w_thresh = props.weld_threshold if props.use_weld else 0.0
        # リクエストログ (V13.3) - 高速化のためコメントアウト
        algo = "DC" if use_dc else "MC"
        # print(f"SDF Debug: Requesting {algo} update (Res: {res}, Domain: {domain:.2f})")
        
        if rust_gpu_sdf.request_mesh_update(primitives, res, domain, use_dc, sym_mask, w_thresh):
            _pending_update = False
            # タイマーがなければ登録
            if not _is_timer_registered:
                bpy.app.timers.register(sdf_mesh_timer, first_interval=0.05)
                _is_timer_registered = True
    except Exception as e:
        print(f"SDF Request Error: {e}")

def apply_mesh_data(output_obj, data, force_normals=False):
    """計算済みデータをメッシュに適用する"""
    try:
        verts_raw, indices = data
        if not verts_raw: return

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
            return

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

def sdf_mesh_timer():
    """バックグラウンド計算が終わったか監視するタイマー"""
    global _pending_update, _is_timer_registered, _force_next_normals
    
    try:
        # 結果をチェック
        data = rust_gpu_sdf.fetch_mesh_if_ready()
        if data:
            # ターゲットオブジェクトを見つける
            for obj in bpy.context.scene.objects:
                if obj.sdf_props.is_output:
                    apply_mesh_data(obj, data, force_normals=_force_next_normals)
                    obj.update_tag() 
            
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
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()
