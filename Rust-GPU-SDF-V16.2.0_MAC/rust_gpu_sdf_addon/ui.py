import bpy
from ._native import rust_gpu_sdf
from .constants import PRIMITIVE_UI_DEFS
from .engine import _resolve_curve_sync_target


def _gn_input_binding(mod, identifier):
    """Geometry Nodes モディファイアの入力1件を layout.prop() へ渡す形にして返す。

    戻り値は (データ, プロパティ名)。見つからなければ None。

    Blender 5.2 で、モディファイアの入力値がカスタムプロパティから通常のRNAプロパティへ
    変わった（5.2 リリースノート / Geometry Nodes の項）。

        # 5.1 まで
        modifier["Socket_3"] = 5.0
        # 5.2 から
        modifier.properties.inputs.Socket_3.value = 5.0

    5.2 の NodesModifier 自身はカスタムプロパティを持たないため、旧来の
    `"Socket_3" in mod` は TypeError を投げる。

    バージョン番号では分岐せず、新しい形から順に実際に引けるかで判定する。
    こうしておけば 5.1/5.2 のどちらでも同じコードが動き、将来また変わっても
    候補を1つ足すだけで済む。
    """
    # 5.2 以降: mod.properties.inputs.<identifier>.value
    inputs = getattr(getattr(mod, "properties", None), "inputs", None)
    if inputs is not None:
        socket = getattr(inputs, identifier, None)
        if socket is None:
            # コレクション風に引ける実装だった場合の保険
            try:
                socket = inputs[identifier]
            except Exception:
                socket = None
        if socket is not None:
            try:
                if socket.bl_rna.properties.get("value") is not None:
                    return socket, "value"
            except Exception:
                pass

    # 5.1 まで: mod["Socket_3"]（カスタムプロパティ）
    try:
        if identifier in mod:
            return mod, f'["{identifier}"]'
    except TypeError:
        pass

    return None


class SDF_UL_stack_list(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            if item.item_type == 'COLLECTION':
                op = row.operator("sdf.select_stack_obj", text=f"== {item.name_override} ==", icon='FILE_FOLDER', emboss=False)
                op.obj_name = item.empty_ptr.name if item.empty_ptr else ""
                op.index = index
                op_dup = row.operator("sdf.duplicate_collection", text="", icon='DUPLICATE', emboss=False)
                op_dup.index = index
                row.prop(item, "is_layer_boundary", text="", toggle=True, emboss=False, icon='MOD_MASK' if item.is_layer_boundary else 'FILE_FOLDER')
                row.prop(item, "start_new_group", text="", toggle=True, emboss=False, icon='LINKED' if not item.start_new_group else 'UNLINKED')
                row.prop(item, "enabled", text="", icon='CHECKBOX_HLT' if item.enabled else 'CHECKBOX_DEHLT', emboss=False)
            elif item.object_ptr:
                o = item.object_ptr
                p = o.sdf_props
                if item.item_type == 'CURVE_SYNC':
                    shape_icon = 'CURVE_DATA'
                else:
                    shape_icon = 'MESH_UVSPHERE'
                    if p.shape_type == 'box': shape_icon = 'MESH_CUBE'
                    elif p.shape_type == 'torus': shape_icon = 'MESH_TORUS'
                    elif p.shape_type == 'cylinder': shape_icon = 'MESH_CYLINDER'

                chip = row.row(align=True)
                chip.scale_x = 0.6
                chip.prop(p, "color", text="")
                row.label(text=f"{index+1:02d}", icon=shape_icon)
                display_name = o.name
                if item.item_type == 'CURVE_SYNC' and o.type == 'EMPTY':
                    target = _resolve_curve_sync_target(o)
                    display_name = f"{o.name} -> {target.name}" if target else f"{o.name} (no curve set)"
                op = row.operator("sdf.select_stack_obj", text=display_name, emboss=False)
                op.obj_name = o.name
                op.index = index
                row.prop(p, "operation", text="", icon_only=True, emboss=False)
                row.prop(item, "enabled", text="", icon='CHECKBOX_HLT' if item.enabled else 'CHECKBOX_DEHLT', emboss=False)
            else:
                row.label(text="(Missing Object)", icon='ERROR')

# --- V15: Deform Stack UIList ---
_DEFORM_TYPE_ICONS = {
    'ELONGATE': 'FIXED_SIZE',
    'BEND': 'MOD_SIMPLEDEFORM',
    'TWIST': 'MOD_SCREW',
    'TAPER': 'MOD_TRIANGULATE',
}
_DEFORM_TYPE_LABELS = {
    'ELONGATE': "Elongate",
    'BEND': "Bend",
    'TWIST': "Twist",
    'TAPER': "Taper",
}

class SDF_UL_deform_list(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            d_icon = _DEFORM_TYPE_ICONS.get(item.deform_type, 'MODIFIER')
            label = _DEFORM_TYPE_LABELS.get(item.deform_type, "?")
            axis_labels = {0: "X", 1: "Y", 2: "Z"}
            axis_str = axis_labels.get(int(item.axis), "?")
            row.label(text=f"{index+1}. {label} ({axis_str})", icon=d_icon)
            row.prop(item, "enabled", text="", icon='CHECKBOX_HLT' if item.enabled else 'CHECKBOX_DEHLT', emboss=False)

class SDF_PT_main(bpy.types.Panel):
    bl_label = "SDF.R Modeling"
    bl_idname = "SDF_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "SDF-R"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        props = scene.sdf_scene_props
        
        # --- UI Guard (Initialization status) ---
        if not props.is_gpu_ready:
            box = layout.box()
            col = box.column(align=True)
            if props.dc_last_error:
                col.label(text="SDF.R Engine: Initialization Error", icon='ERROR')
                col.separator()
                log_path = rust_gpu_sdf.get_log_path()
                if log_path:
                    col.label(text=f"See log: {log_path}")
                col.label(text="Try disabling DC and using Marching Cubes (MC).")
            else:
                col.label(text="SDF.R Engine Warming-up...", icon='NODE_COMPOSITING')
                col.separator()
                col.label(text="Initializing (First time takes approx. 2 mins)")
                col.label(text="Please wait and do not operate Blender...")
            return

        # 1. Header & Status
        row = layout.row(align=True)
        row.prop(scene, "sdf_live_update", text="Live Update", icon='RENDER_STILL')
        row.prop(scene, "sdf_show_result", text="", icon='MESH_DATA')
        row.prop(scene, "sdf_show_primitives", text="", icon='SHADING_WIRE' if scene.sdf_show_primitives else 'SHADING_BBOX')
        row.prop(scene, "sdf_show_preview", text="", icon='GHOST_ENABLED' if scene.sdf_show_preview else 'GHOST_DISABLED')

        output_obj = None
        for o in scene.objects:
            if getattr(o, "sdf_props", None) and o.sdf_props.is_output:
                output_obj = o
                break

        updating = False
        try:
            updating = rust_gpu_sdf.is_updating()
        except Exception:
            pass
        layout.label(text="GPU: Updating" if updating else "GPU: Ready", icon='TIME' if updating else 'NODE_COMPOSITING')
        self._draw_engine_diagnostics(layout, scene, output_obj, updating)

        # V15.9.9.1: DCシェーダーのコンパイル失敗が検出された場合の案内表示
        if props.dc_last_error:
            dc_box = layout.box()
            dc_col = dc_box.column(align=True)
            dc_col.label(text="Dual Contouring (DC) unavailable", icon='ERROR')
            log_path = rust_gpu_sdf.get_log_path()
            if log_path:
                dc_col.label(text=f"See log: {log_path}")
            dc_col.label(text="Falling back is recommended: switch Algorithm to MC.")

        if not output_obj:
            layout.separator()
            row = layout.row()
            row.scale_y = 1.5
            row.operator("sdf.make_output", text="New SDF Workspace", icon='FILE_NEW')
            self._draw_all_clear(layout, scene)
            return

        m_props = output_obj.sdf_props

        # SECTION 1: Output & Quality
        box = layout.box()
        box.label(text="Output & Quality", icon='MOD_MESHDEFORM')

        diag = getattr(scene.sdf_scene_props, "mesh_diagnostics", "")
        if diag:
            health = "UNKNOWN"
            algo = "?"
            details = {}
            for part in diag.split(";"):
                part = part.strip()
                if part.startswith("health="):
                    health = part.split("=", 1)[1]
                elif part.startswith("algo="):
                    algo = part.split("=", 1)[1]
                elif "=" in part:
                    key, value = part.split("=", 1)
                    details[key.strip()] = value.strip()
            icon = 'CHECKMARK' if health == "OK" else 'ERROR' if health in {"CAPACITY_LIMITED", "EMPTY_RESULT"} else 'INFO'
            row = box.row(align=True)
            row.label(text=f"Mesh: {health} ({algo})", icon=icon)
            stat_parts = []
            if "faces" in details:
                stat_parts.append(f"F {details['faces'].split('/')[0]}")
            elif "welded_faces" in details:
                stat_parts.append(f"F {details['welded_faces']}")
            if "verts" in details:
                stat_parts.append(f"V {details['verts'].split('/')[0]}")
            elif "welded_verts" in details:
                stat_parts.append(f"V {details['welded_verts']}")
            if "chunk_cells" in details:
                stat_parts.append(f"Chunk {details['chunk_cells']}")
            if "ghost_cells" in details:
                stat_parts.append(f"Ghost {details['ghost_cells']}")
            if "weld_scale" in details:
                stat_parts.append(f"Weld {details['weld_scale']}")
            if details.get("filtered_tris") and details["filtered_tris"] != "0":
                stat_parts.append(f"Filtered {details['filtered_tris']}")
            if "chunks" in details:
                chunk_vals = details["chunks"].split("/")
                if len(chunk_vals) >= 4 and chunk_vals[0] != "0":
                    stat_parts.append(f"Chunks {chunk_vals[1]}/{chunk_vals[0]}")
                    if chunk_vals[3] != "0":
                        stat_parts.append(f"Issues {chunk_vals[3]}")
            if "reason" in details:
                stat_parts.append(details["reason"])
            if details.get("experimental") == "true":
                stat_parts.append("Experimental")
            if stat_parts:
                sub = box.row(align=True)
                sub.label(text="  ".join(stat_parts), icon='MESH_DATA')
            if health in {"CAPACITY_LIMITED", "EMPTY_RESULT"}:
                box.prop(m_props, "protect_partial_mesh", text="Protect Partial Mesh", icon='LOCKED')
                box.prop(m_props, "auto_safe_retry", text="Auto Safe Retry", icon='FILE_REFRESH')
                if m_props.auto_safe_retry:
                    box.prop(m_props, "safe_retry_min_res", text="Retry Min Res")
                box.prop(m_props, "auto_chunked_fallback", text="Chunked CPU Fallback", icon='MOD_BUILD')
                box.prop(m_props, "auto_gpu_chunked_fallback", text="Chunked GPU Fallback", icon='NODE_COMPOSITING')
                if m_props.auto_chunked_fallback or m_props.auto_gpu_chunked_fallback:
                    box.prop(m_props, "chunked_fallback_cells", text="Chunk Cells")
        
        col = box.column(align=True)
        row = col.row(align=True)
        row.scale_y = 1.2
        is_low = (m_props.resolution == m_props.res_preset_low)
        op = row.operator("sdf.set_resolution_preset", text="Low", icon='PREVIEW_RANGE', depress=is_low)
        op.mode = 'LOW'
        is_high = (m_props.resolution == m_props.res_preset_high)
        op = row.operator("sdf.set_resolution_preset", text="High", icon='RENDER_STILL', depress=is_high)
        op.mode = 'HIGH'
        
        row = col.row(align=True)
        row.prop(m_props, "res_preset_low", text="L-Val")
        row.prop(m_props, "res_preset_high", text="H-Val")
        
        row = box.row(align=True)
        row.prop(m_props, "resolution", text="Res")
        row.prop(m_props, "domain_size", text="Domain")
        row.prop(m_props, "auto_domain", text="", icon='FULLSCREEN_ENTER' if m_props.auto_domain else 'FULLSCREEN_EXIT', toggle=True)

        
        box.prop(m_props, "preview_quality", text="Preview Quality")
        box.prop(m_props, "curve_sync_guide_width", text="Curve Sync Guide Width", slider=True)

        row = box.row(align=True)
        row.label(text="Symmetry:", icon='MOD_MIRROR')
        row.prop(m_props, "sym_x", text="X", toggle=True)
        row.prop(m_props, "sym_y", text="Y", toggle=True)
        row.prop(m_props, "sym_z", text="Z", toggle=True)
        
        row = box.row(align=True)
        op = row.operator("sdf.switch_algo", text="Marching Cubes", depress=(m_props.algo_type == 'MC'))
        op.target_type = 'MC'
        op = row.operator("sdf.switch_algo", text="Dual Contouring", depress=(m_props.algo_type == 'DC'))
        op.target_type = 'DC'

        row = box.row(align=True)
        row.prop(m_props, "meshing_backend", text="Backend")
        if m_props.meshing_backend != 'AUTO':
            row.prop(m_props, "chunked_fallback_cells", text="Chunk")
            row.prop(m_props, "chunk_seam_weld_scale", text="Seam")
        else:
            row.prop(m_props, "auto_chunk_high_res", text="", icon='MOD_BUILD', toggle=True)
            if m_props.auto_chunk_high_res:
                row.prop(m_props, "auto_chunk_start_res", text="From")
                row.prop(m_props, "chunked_fallback_cells", text="Chunk")
                row.prop(m_props, "chunk_seam_weld_scale", text="Seam")
        
        col_weld = box.column(align=True)
        row = col_weld.row(align=True)
        row.prop(m_props, "use_weld", text="Weld (Merge)", icon='AUTOMERGE_ON')
        if m_props.use_weld:
            row.prop(m_props, "weld_threshold", text="Scale")
        
        col_quality = box.column(align=True)
        col_quality.prop(m_props, "use_live_normals", text="Live Normals (Heavy)", icon='IPO_CONSTANT')
        col_quality.prop(m_props, "res_mode_auto_normals", text="Auto-enable Live Normals on High")
        
        # SECTION 2: Post-Process (GN)
        box = layout.box()
        box.label(text="Post-Process (Smoothing)", icon='MOD_SMOOTH')
        georem_mod = output_obj.modifiers.get("GeoRemesh_R")
        if georem_mod:
            node_group = georem_mod.node_group
            if node_group and node_group.interface:
                col = box.column(align=True)
                shown = 0
                missing = []
                for item in node_group.interface.items_tree:
                    if item.in_out == 'INPUT' and item.socket_type != 'NodeSocketGeometry':
                        # V16.1.1: 入力の持ち方はバージョンで変わる（_gn_input_binding 参照）。
                        # 実体が無い指定を prop() に渡すと property not found が出るうえ、
                        # そこで描画が止まって以降の項目が一切出なくなる。
                        binding = _gn_input_binding(georem_mod, item.identifier)
                        if binding is None:
                            missing.append(item.name)
                            continue
                        data, prop_path = binding
                        if item.socket_type == 'NodeSocketMenu':
                            col.prop(data, prop_path, expand=True)
                        else:
                            col.prop(data, prop_path, text=item.name)
                        shown += 1
                if missing and shown == 0:
                    # 1つも解決できない = この版での持ち方が未知。機能自体は生きているので、
                    # Blender 標準のモディファイアパネルから調整してもらう
                    col.label(text="Not editable here on this Blender version", icon='INFO')
                    col.label(text="Adjust in Properties > Modifiers > GeoRemesh_R")
                elif missing:
                    warn = box.column(align=True)
                    warn.label(text="Inputs not available:", icon='ERROR')
                    warn.label(text=", ".join(missing))
                    warn.operator("sdf.setup_post_process",
                                  text="Re-apply Node Group", icon='FILE_REFRESH')
        else:
            box.operator("sdf.setup_post_process", text="Setup Post Process", icon='ADD')

        # SECTION 3: The Stack
        box = layout.box()
        box.label(text="The Stack", icon='OUTLINER')
        row = box.row()
        row.template_list("SDF_UL_stack_list", "", m_props, "sdf_stack", m_props, "sdf_stack_index")
        col = row.column(align=True)
        op = col.operator("sdf.stack_move", icon='TRIA_UP', text="")
        op.direction = 'UP'
        op = col.operator("sdf.stack_move", icon='TRIA_DOWN', text="")
        op.direction = 'DOWN'
        col.separator()
        col.prop(m_props, "use_solo", text="", icon='SOLO_ON' if m_props.use_solo else 'SOLO_OFF')
        col.operator("sdf.stack_remove", icon='X', text="")
        col.operator("sdf.add_collection_divider", icon='COLLECTION_NEW', text="")

        # SECTION 4: Material
        box = layout.box()
        box.label(text="Material", icon='MATERIAL')
        row = box.row(align=True)
        row.operator("sdf.setup_material", text="Setup Nodes", icon='NODE_SEL')
        row.operator("sdf.reset_material", text="Reset", icon='FILE_REFRESH')
        row = box.row(align=True)
        row.prop(props, "material_all_color", text="")
        row.operator("sdf.apply_color_all", text="Apply Color All", icon='COLOR')
        row = box.row(align=True)
        row.prop(props, "material_all_metallic", slider=True)
        row.prop(props, "material_all_roughness", slider=True)
        row = box.row(align=True)
        row.prop(props, "material_all_transmission", slider=True)
        sub_ior = row.row(align=True)
        # IOR は Transmission が効いている時だけ意味を持つ
        sub_ior.enabled = props.material_all_transmission > 0.0
        sub_ior.prop(props, "material_all_ior")
        if props.material_all_transmission > 0.0:
            box.label(text="Transmission is a whole-material value (not per-primitive).", icon='INFO')
        box.operator("sdf.apply_material_all", text="Apply Material All", icon='CHECKMARK')
        
        # SECTION 5: Finalize (Bake)
        box = layout.box()
        row = box.row(align=True)
        row.scale_y = 1.2
        row.operator("sdf.update_normals", text="Fix Normals", icon='MOD_SMOOTH')
        row.operator("sdf.generate_mesh", text="Force Update", icon='FILE_REFRESH')
        row = box.row(align=True)
        row.scale_y = 1.2
        row.operator("sdf.bake_mesh", text="Snapshot Mesh", icon='DUPLICATE')
        row.operator("sdf.finalize", text="Finalize (Bake)", icon='CHECKBOX_HLT')

        # --- Primitive Settings ---
        layout.separator()
        obj = context.active_object
        if obj and getattr(obj, "sdf_props", None) and not obj.sdf_props.is_output:
            props = obj.sdf_props
            active_stack_item = None
            if output_obj:
                stack = output_obj.sdf_props.sdf_stack
                idx = output_obj.sdf_props.sdf_stack_index
                if 0 <= idx < len(stack):
                    active_stack_item = stack[idx]
            
            if active_stack_item and active_stack_item.item_type == 'COLLECTION':
                box = layout.box()
                box.label(text=f"Group Settings: {active_stack_item.name_override}", icon='FILE_FOLDER')
                box.prop(active_stack_item, "name_override", text="Name")
                box.prop(active_stack_item, "is_layer_boundary", text="Layer Boundary")
                if active_stack_item.is_layer_boundary:
                    sub_layer = box.box().column(align=True)
                    sub_layer.label(text="Layer Merge", icon='MOD_MASK')
                    sub_layer.prop(active_stack_item, "layer_smoothness", text="Layer Blend")
                    sub_layer.prop(active_stack_item, "layer_blend_profile", text="Profile")
                    if active_stack_item.layer_blend_profile == '4':
                        sub_layer.prop(active_stack_item, "layer_chamfer_smooth", text="Chamfer Smooth")
                    if active_stack_item.layer_smoothness <= 0.0:
                        sub_layer.label(text="Hard boundary (no blending outside)", icon='CHECKMARK')
                box.prop(active_stack_item, "start_new_group", text="Break Parent (Start New Group)")
                
                empty_props = obj.sdf_props
                col_place = box.column(align=True)
                col_place.label(text="Group Layout:", icon='MOD_ARRAY')
                row = col_place.row(align=True)
                row.prop(empty_props, "layout_use_mirror", text="Mirror", toggle=True)
                row.prop(empty_props, "layout_use_radial", text="Radial", toggle=True)
                row.prop(empty_props, "layout_use_spiral", text="Spiral", toggle=True)
                row.prop(empty_props, "layout_use_grid", text="Grid", toggle=True)
                row.prop(empty_props, "layout_use_jitter", text="Jitter", toggle=True)
                
                if empty_props.layout_use_mirror:
                    sub = col_place.box().column(align=True)
                    sub.label(text="Mirror Settings", icon='MOD_MIRROR')
                    row = sub.row(align=True)
                    row.prop(empty_props, "mirror_x", text="X", toggle=True)
                    row.prop(empty_props, "mirror_y", text="Y", toggle=True)
                    row.prop(empty_props, "mirror_z", text="Z", toggle=True)
                    sub.prop(empty_props, "mirror_offset", text="Offset")

                if empty_props.layout_use_radial:
                    sub = col_place.box().column(align=True)
                    sub.label(text="Radial Pattern", icon='MOD_ARRAY')
                    row = sub.row(align=True)
                    row.prop(empty_props, "radial_count", text="Count")
                    row.prop(empty_props, "radial_radius", text="Radius")
                    sub.row().prop(empty_props, "radial_axis", expand=True)

                if empty_props.layout_use_grid:
                    sub = col_place.box().column(align=True)
                    sub.label(text="Grid Layout", icon='GRID')
                    row = sub.row(align=True)
                    row.prop(empty_props, "grid_count_x", text="X")
                    row.prop(empty_props, "grid_count_y", text="Y")
                    row.prop(empty_props, "grid_count_z", text="Z")
                    row = sub.row(align=True)
                    row.prop(empty_props, "grid_spacing_x", text="SpX")
                    row.prop(empty_props, "grid_spacing_y", text="SpY")
                    row.prop(empty_props, "grid_spacing_z", text="SpZ")

                if empty_props.layout_use_spiral:
                    sub = col_place.box().column(align=True)
                    sub.label(text="Spiral Pattern", icon='MOD_CURVE')
                    row = sub.row(align=True)
                    row.prop(empty_props, "radial_count", text="Count")
                    row.prop(empty_props, "radial_radius", text="Radius")
                    sub.prop(empty_props, "spiral_pitch", text="Pitch")
                    sub.row().prop(empty_props, "radial_axis", expand=True)

                if empty_props.layout_use_radial or empty_props.layout_use_spiral:
                    col_rot = col_place.box().column(align=True)
                    col_rot.label(text="Rotation (Indiv & Accum):", icon='FILE_REFRESH')
                    row = col_rot.row(align=True)
                    row.prop(empty_props, "instance_rot_x", text="X")
                    row.prop(empty_props, "instance_rot_y", text="Y")
                    row.prop(empty_props, "instance_rot_z", text="Z")
                    row = col_rot.row(align=True)
                    row.prop(empty_props, "step_rot_x", text="X")
                    row.prop(empty_props, "step_rot_y", text="Y")
                    row.prop(empty_props, "step_rot_z", text="Z")

                if empty_props.layout_use_jitter:
                    sub = col_place.box().column(align=True)
                    sub.label(text="Jitter Settings", icon='RNDCURVE')
                    sub.prop(empty_props, "jitter_seed", text="Seed")
                    sub.prop(empty_props, "jitter_strength", text="Strength")
            
            elif (props.is_primitive or (output_obj and output_obj.sdf_props.target_collection and obj.name in output_obj.sdf_props.target_collection.objects)) and obj.type != 'EMPTY':
                box = layout.box()
                box.label(text=f"Settings: {obj.name}", icon='MESH_UVSPHERE')
                box.prop(props, "shape_type")
                box.row().prop(props, "operation", expand=True)
                row_blend = box.row(align=True)
                row_blend.prop(props, "blend_profile", text="")
                if props.blend_profile == '4':
                    row_blend.prop(props, "chamfer_smooth", text="Factor")
                box.prop(props, "smoothness")
                row = box.row(align=True)
                row.prop(props, "noise_strength", text="Noise")
                row.prop(props, "noise_scale", text="Scale")
                box.prop(props, "color")

                scene_props = context.scene.sdf_scene_props
                col_color_mode = box.column(align=True)
                col_color_mode.prop(scene_props, "color_mode", text="Color Mode")
                if scene_props.color_mode == 'AUTO_HUE':
                    row = col_color_mode.row(align=True)
                    row.prop(scene_props, "auto_hue_saturation", text="Saturation")
                    row.prop(scene_props, "auto_hue_value", text="Value")
                    row = col_color_mode.row(align=True)
                    row.prop(scene_props, "auto_hue_step_deg", text="Hue Step (deg)")
                    row.prop(scene_props, "auto_hue_offset", text="Hue Offset (deg)")
                elif scene_props.color_mode == 'SINGLE':
                    col_color_mode.prop(scene_props, "single_color", text="Base Color")
                
                col_mat = box.column(align=True)
                col_mat.prop(props, "metallic", slider=True)
                col_mat.prop(props, "roughness", slider=True)
                
                # Dynamic Params
                shape_key = str(props.shape_type)
                if shape_key in PRIMITIVE_UI_DEFS:
                    ui_def = PRIMITIVE_UI_DEFS[shape_key]
                    if shape_key == 'math_field':
                        formula_row = box.row(align=True)
                        formula_row.prop(props, "field_type", text="Formula")
                        gyroid_row = box.row(align=True)
                        gyroid_row.prop(props, "gyroid_preset", text="Preset")
                        gyroid_row.prop(props, "gyroid_mask_shape", text="Mask")
                        gyroid_row.prop(props, "gyroid_boundary_mode", text="Boundary")
                        blend_row = box.row(align=True)
                        blend_row.operator("sdf.use_previous_as_mask", text="Use Previous as Mask", icon='MOD_BOOLEAN')
                        phase_row = box.row(align=True)
                        phase_row.prop(props, "gyroid_phase", text="Phase")
                        axis_row = box.row(align=True)
                        axis_row.prop(props, "gyroid_axis_x", text="Axis X")
                        axis_row.prop(props, "gyroid_axis_y", text="Y")
                        axis_row.prop(props, "gyroid_axis_z", text="Z")
                        box.operator("sdf.match_math_field_axis_to_scale", text="Auto Match Scale", icon='CON_SIZELIKE')
                    if shape_key == 'bezier_curve':
                        sub_b = box.column(align=True)
                        sub_b.label(text="Control Points & Taper:", icon='CURVE_BEZCURVE')
                        sub_b.prop(props, "bezier_pt_b", text="Point B (Mid)")
                        sub_b.prop(props, "bezier_pt_c", text="Point C (End)")
                        row_r = sub_b.row(align=True)
                        row_r.prop(props, "bezier_start_radius", text="Start R")
                        row_r.prop(props, "bezier_end_radius", text="End R")
                    if shape_key in ('extrude', 'lathe'):
                        prof_row = box.row(align=True)
                        prof_row.prop(props, 'profile_2d_type', text='2D Profile')
                        if shape_key == 'extrude':
                            box.prop(props, 'extrude_depth', text='Depth')
                            box.prop(props, 'extrude_chamfer', text='Chamfer')
                        elif shape_key == 'lathe':
                            box.prop(props, 'lathe_offset', text='Lathe Radius / Offset')
                        box.prop(props, 'profile_corner_radius', text='Corner Radius')
                    if ui_def['params']:
                        sub = box.column(align=True)
                        for p_name, label, _ in ui_def['params']:
                            sub.prop(props, p_name, text=label)
                
                # --- V16: Primitive Edge Profile & Modifiers ---
                sub = box.column(align=True)
                sub.separator()
                
                if shape_key != 'math_field':
                    row_edge = sub.row(align=True)
                    row_edge.prop(props, "edge_profile", text="Edge")
                    if props.edge_profile != '0':
                        row_edge.prop(props, "edge_profile_size", text="Size")
                    
                    if props.edge_profile == '4':
                        row_cs = sub.row(align=True)
                        row_cs.prop(props, "edge_chamfer_smooth", text="Smoothness")
                
                sub.prop(props, "shell_thickness", text="Shell (Hollow)")
                
                # Layout (Mirror, Radial, Grid)
                layout.separator()
                col_place = box.column(align=True)
                col_place.label(text="Layout (Instancing):", icon='MOD_ARRAY')
                row = col_place.row(align=True)
                row.prop(props, "layout_use_mirror", text="Mirror", toggle=True)
                row.prop(props, "layout_use_radial", text="Radial", toggle=True)
                row.prop(props, "layout_use_spiral", text="Spiral", toggle=True)
                row.prop(props, "layout_use_grid", text="Grid", toggle=True)
                row.prop(props, "layout_use_jitter", text="Jitter", toggle=True)

                # Advanced Rotation (Individual & Step)
                col_rot = box.column(align=True)
                col_rot.label(text="Rotation (Indiv & Accum):", icon='FILE_REFRESH')
                row = col_rot.row(align=True)
                row.prop(props, "instance_rot_x", text="X")
                row.prop(props, "instance_rot_y", text="Y")
                row.prop(props, "instance_rot_z", text="Z")
                row = col_rot.row(align=True)
                row.prop(props, "step_rot_x", text="X")
                row.prop(props, "step_rot_y", text="Y")
                row.prop(props, "step_rot_z", text="Z")

                if props.layout_use_mirror:
                    sub = col_place.box().column(align=True)
                    sub.label(text="Mirror Settings", icon='MOD_MIRROR')
                    row = sub.row(align=True)
                    row.prop(props, "mirror_x", text="X", toggle=True)
                    row.prop(props, "mirror_y", text="Y", toggle=True)
                    row.prop(props, "mirror_z", text="Z", toggle=True)
                    sub.prop(props, "mirror_offset", text="Offset")

                if props.layout_use_radial:
                    sub = col_place.box().column(align=True)
                    sub.label(text="Radial Pattern", icon='MOD_ARRAY')
                    row = sub.row(align=True)
                    row.prop(props, "radial_count", text="Count")
                    row.prop(props, "radial_radius", text="Radius")
                    sub.row().prop(props, "radial_axis", expand=True)

                if props.layout_use_grid:
                    sub = col_place.box().column(align=True)
                    sub.label(text="Grid Layout", icon='GRID')
                    row = sub.row(align=True)
                    row.prop(props, "grid_count_x", text="X")
                    row.prop(props, "grid_count_y", text="Y")
                    row.prop(props, "grid_count_z", text="Z")
                    row = sub.row(align=True)
                    row.prop(props, "grid_spacing_x", text="SpX")
                    row.prop(props, "grid_spacing_y", text="SpY")
                    row.prop(props, "grid_spacing_z", text="SpZ")

                if props.layout_use_spiral:
                    sub = col_place.box().column(align=True)
                    sub.label(text="Spiral Pattern", icon='MOD_CURVE')
                    row = sub.row(align=True)
                    row.prop(props, "radial_count", text="Count")
                    row.prop(props, "radial_radius", text="Radius")
                    sub.prop(props, "spiral_pitch", text="Pitch")
                    sub.row().prop(props, "radial_axis", expand=True)

                if props.layout_use_jitter:
                    sub = col_place.box().column(align=True)
                    sub.label(text="Jitter Settings", icon='RNDCURVE')
                    sub.prop(props, "jitter_seed", text="Seed")
                    sub.prop(props, "jitter_strength", text="Strength")

                # --- V15: Deform Stack ---
                layout.separator()
                col_deform = box.column(align=True)
                col_deform.label(text="Deform (Stack):", icon='MOD_SIMPLEDEFORM')
                
                row = col_deform.row()
                row.template_list("SDF_UL_deform_list", "", props, "deform_stack", props, "deform_stack_index", rows=3)
                col_btn = row.column(align=True)
                col_btn.operator("sdf.deform_add", icon='ADD', text="")
                col_btn.operator("sdf.deform_remove", icon='REMOVE', text="")
                col_btn.separator()
                op = col_btn.operator("sdf.deform_move", icon='TRIA_UP', text="")
                op.direction = 'UP'
                op = col_btn.operator("sdf.deform_move", icon='TRIA_DOWN', text="")
                op.direction = 'DOWN'
                
                if len(props.deform_stack) > 0 and props.deform_stack_index < len(props.deform_stack):
                    d_item = props.deform_stack[props.deform_stack_index]
                    sub = col_deform.box().column(align=True)
                    sub.prop(d_item, "deform_type", text="Type")
                    sub.prop(d_item, "enabled", text="Enabled")
                    
                    if d_item.deform_type == 'ELONGATE':
                        row = sub.row(align=True)
                        row.prop(d_item, "elongate_x", text="X")
                        row.prop(d_item, "elongate_y", text="Y")
                        row.prop(d_item, "elongate_z", text="Z")
                    else:
                        sub.prop(d_item, "factor", text="Angle" if d_item.deform_type in ('BEND', 'TWIST') else "Factor")
                        sub.row().prop(d_item, "axis", expand=True)
                        row = sub.row(align=True)
                        axis_val = d_item.axis
                        if axis_val == '2':  # Z
                            row.prop(d_item, "origin", index=0, text="X")
                            row.prop(d_item, "origin", index=1, text="Y")
                        elif axis_val == '1':  # Y
                            row.prop(d_item, "origin", index=2, text="Z")
                            row.prop(d_item, "origin", index=0, text="X")
                        else:  # X
                            row.prop(d_item, "origin", index=1, text="Y")
                            row.prop(d_item, "origin", index=2, text="Z")


        # --- Add New Primitives ---
        layout.separator()
        layout.label(text="Add New Primitives:")
        grid = layout.column(align=True)
        row = grid.row(align=True)
        row.operator("sdf.add_primitive", text="Sphere", icon='MESH_UVSPHERE').shape = 'sphere'
        row.operator("sdf.add_primitive", text="Box", icon='MESH_CUBE').shape = 'box'
        row.operator("sdf.add_primitive", text="R-Box", icon='MOD_BEVEL').shape = 'rounded_box'
        row = grid.row(align=True)
        row.operator("sdf.add_primitive", text="Torus", icon='MESH_TORUS').shape = 'torus'
        row.operator("sdf.add_primitive", text="Cylinder", icon='MESH_CYLINDER').shape = 'cylinder'
        row.operator("sdf.add_primitive", text="Capsule", icon='MESH_CAPSULE').shape = 'capsule'
        row = grid.row(align=True)
        row.operator("sdf.add_primitive", text="Hex", icon='MESH_CIRCLE').shape = 'hex_prism'
        row.operator("sdf.add_primitive", text="Pyramid", icon='MESH_CONE').shape = 'pyramid'
        row.operator("sdf.add_primitive", text="Taper", icon='MESH_CONE').shape = 'capped_cone'

        row = grid.row(align=True)
        row.operator("sdf.add_primitive", text="N-gon", icon='MESH_ICOSPHERE').shape = 'ngon_prism'
        row.operator("sdf.add_primitive", text="Ellipsoid", icon='META_ELLIPSOID').shape = 'ellipsoid'
        row.operator("sdf.add_primitive", text="R-Cylinder", icon='MESH_CAPSULE').shape = 'rounded_cylinder'
        row = grid.row(align=True)
        row.operator("sdf.add_primitive", text="C-Torus", icon='CURVE_BEZCIRCLE').shape = 'capped_torus'
        row.operator("sdf.add_primitive", text="Octahedron", icon='MESH_ICOSPHERE').shape = 'octahedron'
        row.operator("sdf.add_primitive", text="Cut Sphere", icon='SPHERE').shape = 'cut_sphere'
        row = grid.row(align=True)
        row.operator("sdf.add_primitive", text="Math Field", icon='MOD_WAVE').shape = 'math_field'
        row = grid.row(align=True)
        # Extrude/Lathe は Box/Circle 断面しか実装されておらず（N-gon/Star は未対応で
        # Box にフォールバックする）、その2断面は rounded_box/cylinder/torus と機能が
        # 被るため、新規追加メニューからは外している。既存オブジェクトの shape_type や
        # メッシュ生成ロジックはそのまま残しており、既にシーンにある Extrude/Lathe
        # プリミティブは引き続き正しく動作する。
        row.operator("sdf.add_primitive", text="Bezier", icon='CURVE_BEZCURVE').shape = 'bezier_curve'
        row.operator("sdf.add_curve_sync", text="Curve Ref", icon='CURVE_DATA')

        # --- Object Utilities ---
        layout.separator()
        layout.label(text="Object Utilities:", icon='MODIFIER')
        row = layout.row(align=True)
        row.operator("sdf.toggle_display", text="Wire/Solid", icon='SHADING_WIRE')
        row.operator("sdf.move_to_sdf_collection", text="Move to SDF", icon='COLLECTION_NEW')

        # --- Curve Sync: Blender カーブをコレクションに入れる（直接方式）、または
        # Curve Ref プロキシから任意のカーブを参照する（プロキシ方式）の2通り ---
        active_obj = context.active_object
        is_curve_sync_proxy = bool(
            active_obj and active_obj.type == 'EMPTY' and active_obj.sdf_props.is_curve_sync_proxy
        )
        if active_obj and (active_obj.type == 'CURVE' or is_curve_sync_proxy):
            is_curve_sync_member = False
            for o in scene.objects:
                out_props = getattr(o, "sdf_props", None)
                if out_props and out_props.is_output and out_props.target_collection:
                    if active_obj.name in out_props.target_collection.objects:
                        is_curve_sync_member = True
                        break
            box_cs = layout.box()
            if is_curve_sync_proxy:
                # プロキシは常にターゲットコレクションのメンバー（sdf.add_curve_sync が作る）
                cp = active_obj.sdf_props
                box_cs.label(text=f"Curve Sync Ref: {active_obj.name}", icon='CURVE_DATA')
                box_cs.prop(cp, "curve_target_obj", text="Target Curve")
                if not cp.curve_target_obj:
                    box_cs.label(text="Pick a Curve object above.", icon='INFO')
                else:
                    op_edit = box_cs.operator("sdf.edit_curve_sync_target", text=f"Edit '{cp.curve_target_obj.name}'", icon='EDITMODE_HLT')
                    op_edit.proxy_name = active_obj.name
                box_cs.prop(cp, "curve_pipe_radius", text="Pipe Radius")
                box_cs.prop(cp, "curve_sample_resolution", text="Subdiv Samples")
                box_cs.prop(cp, "operation", text="Operation")
                box_cs.prop(cp, "smoothness", text="Smoothness")
                row_mat = box_cs.row(align=True)
                row_mat.prop(cp, "color", text="")
                row_mat.prop(cp, "metallic", text="Metallic", slider=True)
                row_mat.prop(cp, "roughness", text="Roughness", slider=True)
            elif is_curve_sync_member:
                cp = active_obj.sdf_props
                box_cs.label(text=f"Curve Sync: {active_obj.name}", icon='CURVE_DATA')
                if context.mode != 'EDIT_CURVE':
                    box_cs.operator("object.mode_set", text="Edit Curve", icon='EDITMODE_HLT').mode = 'EDIT'
                box_cs.prop(cp, "curve_pipe_radius", text="Pipe Radius")
                box_cs.prop(cp, "curve_sample_resolution", text="Subdiv Samples")
                box_cs.prop(cp, "operation", text="Operation")
                box_cs.prop(cp, "smoothness", text="Smoothness")
                row_mat = box_cs.row(align=True)
                row_mat.prop(cp, "color", text="")
                row_mat.prop(cp, "metallic", text="Metallic", slider=True)
                row_mat.prop(cp, "roughness", text="Roughness", slider=True)
            else:
                box_cs.label(text="Move this Curve to the SDF Collection to sync it as a pipe mesh.", icon='INFO')
                box_cs.operator("sdf.move_to_sdf_collection", text="Move to SDF", icon='COLLECTION_NEW')
                box_cs.label(text="...or add a Curve Ref proxy instead (keeps this curve outside the collection).", icon='INFO')
                box_cs.operator("sdf.add_curve_sync", text="Add Curve Ref", icon='CURVE_DATA')

        # ALL CLEAR
        self._draw_all_clear(layout, scene)

    def _draw_engine_diagnostics(self, layout, scene, output_obj, updating):
        scene_props = scene.sdf_scene_props
        header = layout.row(align=True)
        header.prop(
            scene_props,
            "show_engine_diagnostics",
            text="Engine Diagnostics",
            icon='TRIA_DOWN' if scene_props.show_engine_diagnostics else 'TRIA_RIGHT',
            emboss=False
        )
        if not scene_props.show_engine_diagnostics:
            return

        box = layout.box()
        col = box.column(align=True)
        status_icon = 'TIME' if updating else 'CHECKMARK' if scene_props.is_gpu_ready else 'ERROR'
        status_text = "Updating" if updating else "Ready" if scene_props.is_gpu_ready else "Not Ready"
        col.label(text=f"Engine: {status_text}", icon=status_icon)

        log_path = ""
        try:
            log_path = rust_gpu_sdf.get_log_path()
        except Exception:
            pass
        if log_path:
            col.label(text=f"Log: {log_path}", icon='TEXT')

        diag = getattr(scene_props, "mesh_diagnostics", "")
        if diag:
            details = {}
            for part in diag.split(";"):
                part = part.strip()
                if "=" in part:
                    key, value = part.split("=", 1)
                    details[key.strip()] = value.strip()
            health = details.get("health", "UNKNOWN")
            algo = details.get("algo", "?")
            col.label(text=f"Last Mesh: {health} ({algo})", icon='MESH_DATA')
            stat_parts = []
            for key, label in (
                ("faces", "F"),
                ("welded_faces", "F"),
                ("verts", "V"),
                ("welded_verts", "V"),
                ("chunk_cells", "Chunk"),
                ("ghost_cells", "Ghost"),
                ("active_blocks", "Blocks"),
            ):
                if key in details:
                    stat_parts.append(f"{label} {details[key].split('/')[0]}")
            if details.get("reason"):
                stat_parts.append(details["reason"])
            if stat_parts:
                col.label(text="  ".join(stat_parts), icon='INFO')

        if output_obj:
            m_props = output_obj.sdf_props
            col.label(text=f"Backend: {m_props.meshing_backend} / {m_props.algo_type}", icon='SETTINGS')
            col.label(text=f"Resolution: {m_props.resolution}, Preview: {m_props.preview_quality}", icon='VIEWZOOM')

        if scene_props.dc_last_error:
            col.separator()
            col.label(text="DC Diagnostic", icon='ERROR')
            col.label(text=scene_props.dc_last_error[:120])

        col.separator()
        row = col.row(align=True)
        row.prop(scene_props, "diagnostics_perf_log", text="Perf", toggle=True)
        row.prop(scene_props, "diagnostics_mesh_debug", text="Mesh", toggle=True)
        row.prop(scene_props, "diagnostics_layout_debug", text="Layout", toggle=True)

    def _draw_all_clear(self, layout, scene):
        layout.separator()
        col_clear = layout.column(align=True)
        row = col_clear.row(align=True)
        row.prop(scene.sdf_scene_props, "all_clear_include_history", text="Include Baked Results")
        row.operator("sdf.all_clear", text="All Clear", icon='TRASH')
