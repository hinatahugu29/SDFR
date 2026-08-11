import bpy
import os
from .engine import update_sdf_callback, _update_preview

# --- V15: Deform Stack Item ---
class SDF_DeformItem(bpy.types.PropertyGroup):
    """デフォームスタックの各項目"""
    deform_type: bpy.props.EnumProperty(
        items=[
            ('ELONGATE', "Elongate", "Stretch space along axes"),
            ('BEND', "Bend", "Bend space around axis"),
            ('TWIST', "Twist", "Twist space along axis"),
            ('TAPER', "Taper", "Taper space along axis"),
        ],
        name="Type", default='BEND', update=update_sdf_callback
    )
    axis: bpy.props.EnumProperty(
        items=[('0', "X", ""), ('1', "Y", ""), ('2', "Z", "")],
        name="Axis", default='2', update=update_sdf_callback
    )
    factor: bpy.props.FloatProperty(name="Factor", default=0.0, update=update_sdf_callback)
    origin: bpy.props.FloatVectorProperty(name="Origin Offset", default=(0.0, 0.0, 0.0), update=update_sdf_callback)
    # Elongate用（XYZ個別）
    elongate_x: bpy.props.FloatProperty(name="X", default=0.0, min=0.0, update=update_sdf_callback)
    elongate_y: bpy.props.FloatProperty(name="Y", default=0.0, min=0.0, update=update_sdf_callback)
    elongate_z: bpy.props.FloatProperty(name="Z", default=0.0, min=0.0, update=update_sdf_callback)
    enabled: bpy.props.BoolProperty(name="Enabled", default=True, update=update_sdf_callback)

def update_res_preset(self, context):
    """Updates the resolution immediately if the preset value is currently applied"""
    if self.resolution == self.res_preset_low or self.resolution == self.res_preset_high:
        # If the current resolution matches one of the presets, synchronize the values
        # Note: Since full automatic synchronization is a matter of preference, 
        # only the convenience during "slider operation" is considered here
        pass
    update_sdf_callback(self, context)

_DIAGNOSTIC_FLAGS = {
    "diagnostics_perf_log": "SDF_PERF_LOG.ON",
    "diagnostics_mesh_debug": "SDF_MESH_DEBUG.ON",
    "diagnostics_layout_debug": "SDF_DEBUG_LAYOUT.ON",
}

def _diagnostic_flag_path(filename):
    return os.path.join(os.path.dirname(__file__), filename)

def _set_diagnostic_flag_file(filename, enabled):
    path = _diagnostic_flag_path(filename)
    if enabled:
        with open(path, "w", encoding="utf-8") as f:
            f.write("enabled by SDF.R diagnostics UI\n")
    elif os.path.exists(path):
        os.remove(path)

def _diagnostic_flag_enabled(filename):
    return os.path.exists(_diagnostic_flag_path(filename))

def update_diagnostic_flags(self, context):
    """Persist diagnostics toggles and apply them to loaded modules immediately."""
    _set_diagnostic_flag_file(_DIAGNOSTIC_FLAGS["diagnostics_perf_log"], self.diagnostics_perf_log)
    _set_diagnostic_flag_file(_DIAGNOSTIC_FLAGS["diagnostics_mesh_debug"], self.diagnostics_mesh_debug)
    _set_diagnostic_flag_file(_DIAGNOSTIC_FLAGS["diagnostics_layout_debug"], self.diagnostics_layout_debug)

    try:
        from . import engine, handlers
        engine.set_diagnostics_flags(
            perf_log=self.diagnostics_perf_log,
            mesh_debug=self.diagnostics_mesh_debug,
            layout_debug=self.diagnostics_layout_debug,
        )
        handlers.set_perf_logging(self.diagnostics_perf_log)
    except Exception as exc:
        print(f"SDF.R diagnostics switch update failed: {exc}")

def update_gyroid_preset(self, context):
    """Apply practical Gyroid defaults while keeping manual editing available."""
    preset = getattr(self, "gyroid_preset", "CUSTOM")
    values = {
        "FINE": (8.0, 0.045, 0.0, 1.6, 0.0, 1.0, 1.0, 1.0),
        "MEDIUM": (5.0, 0.08, 0.0, 1.6, 0.0, 1.0, 1.0, 1.0),
        "COARSE": (3.2, 0.12, 0.0, 1.8, 0.0, 1.0, 1.0, 1.0),
        "THICK": (4.2, 0.16, 0.0, 1.7, 0.0, 1.0, 1.0, 1.0),
        "SHELL": (6.0, 0.06, 0.22, 1.6, 0.0, 1.0, 1.0, 1.0),
    }.get(preset)
    if values:
        self.p1, self.p2, self.p3, self.p4 = values[:4]
        self.gyroid_phase, self.gyroid_axis_x, self.gyroid_axis_y, self.gyroid_axis_z = values[4:]
    update_sdf_callback(self, context)

def sync_scene_diagnostic_flags():
    """Initialize scene toggles from existing diagnostics flag files."""
    perf_on = _diagnostic_flag_enabled(_DIAGNOSTIC_FLAGS["diagnostics_perf_log"])
    mesh_on = _diagnostic_flag_enabled(_DIAGNOSTIC_FLAGS["diagnostics_mesh_debug"])
    layout_on = _diagnostic_flag_enabled(_DIAGNOSTIC_FLAGS["diagnostics_layout_debug"])
    try:
        scenes = list(bpy.data.scenes)
    except Exception as exc:
        print(f"SDF.R diagnostics scene sync deferred: {exc}")
        return 0.2
    for scene in scenes:
        props = getattr(scene, "sdf_scene_props", None)
        if props:
            props.diagnostics_perf_log = perf_on
            props.diagnostics_mesh_debug = mesh_on
            props.diagnostics_layout_debug = layout_on
    return None

class SDF_SceneProperties(bpy.types.PropertyGroup):
    """Global SDF Settings"""
    all_clear_include_history: bpy.props.BoolProperty(
        name="Include Baked Results",
        description="Check to also delete all baked meshes and history collections",
        default=False
    )
    is_gpu_ready: bpy.props.BoolProperty(name="GPU Ready", default=False)
    is_dc_compiled: bpy.props.BoolProperty(name="DC Compiled", default=False)
    # V15.9.9.1: DCシェーダー/パイプラインのコンパイル失敗時の診断文字列 (成功時/未発生時は空文字列)
    dc_last_error: bpy.props.StringProperty(name="DC Last Error", default="")
    mesh_diagnostics: bpy.props.StringProperty(name="Mesh Diagnostics", default="health=NO_MESH; algo=none")
    show_engine_diagnostics: bpy.props.BoolProperty(name="Engine Diagnostics", default=False)
    diagnostics_perf_log: bpy.props.BoolProperty(
        name="Performance Log",
        description="Print preview/depsgraph/mesh timing logs",
        default=False,
        update=update_diagnostic_flags
    )
    diagnostics_mesh_debug: bpy.props.BoolProperty(
        name="Mesh Debug Log",
        description="Print mesh request and backend selection debug logs",
        default=False,
        update=update_diagnostic_flags
    )
    diagnostics_layout_debug: bpy.props.BoolProperty(
        name="Layout Debug Log",
        description="Print layout expansion debug logs",
        default=False,
        update=update_diagnostic_flags
    )
    color_mode: bpy.props.EnumProperty(
        items=[
            ('FIXED', "Fixed Palette", "Use the built-in color palette in sequence"),
            ('AUTO_HUE', "Auto Hue", "Rotate hue while keeping saturation/value fixed"),
            ('SINGLE', "Single Color", "Use one shared color for all newly added primitives"),
        ],
        name="Color Mode",
        default='FIXED'
    )
    auto_hue_saturation: bpy.props.FloatProperty(name="Saturation", default=0.55, min=0.0, max=1.0)
    auto_hue_value: bpy.props.FloatProperty(name="Value", default=0.95, min=0.0, max=1.0)
    auto_hue_step_deg: bpy.props.FloatProperty(name="Hue Step (deg)", default=120.0, min=0.0, max=360.0)
    auto_hue_offset: bpy.props.FloatProperty(name="Hue Offset (deg)", default=0.0, min=0.0, max=360.0)
    single_color: bpy.props.FloatVectorProperty(
        name="Base Color",
        subtype='COLOR',
        default=(0.8, 0.8, 0.8),
        min=0.0,
        max=1.0
    )
    material_all_color: bpy.props.FloatVectorProperty(
        name="Base Color",
        subtype='COLOR',
        default=(0.8, 0.8, 0.8),
        min=0.0,
        max=1.0
    )
    material_all_metallic: bpy.props.FloatProperty(name="Metallic", default=0.0, min=0.0, max=1.0)
    material_all_roughness: bpy.props.FloatProperty(name="Roughness", default=0.5, min=0.0, max=1.0)
    # Transmission はプリミティブごとの頂点属性ではなく、SDFマテリアル（Principled BSDF）
    # 全体に対する1つの値として扱う。metallic/roughness と違い頂点フォーマット
    # (11 float) を拡張しないので、個別指定はできない点に注意
    material_all_transmission: bpy.props.FloatProperty(
        name="Transmission",
        description="Transmission weight applied to the whole SDF material (not per-primitive)",
        default=0.0, min=0.0, max=1.0,
    )
    material_all_ior: bpy.props.FloatProperty(
        name="IOR",
        description="Index of refraction used together with Transmission (1.45 = glass)",
        default=1.45, min=1.0, max=3.0,
    )

class SDF_StackItem(bpy.types.PropertyGroup):
    """計算順序リストの各項目"""
    object_ptr: bpy.props.PointerProperty(name="Object", type=bpy.types.Object)
    obj_name: bpy.props.StringProperty(name="Object Name Cache", default="")
    enabled: bpy.props.BoolProperty(name="Enabled", default=True, update=update_sdf_callback)
    item_type: bpy.props.EnumProperty(
        items=[
            ('PRIMITIVE', "Primitive", "Standard SDF Primitive Object"),
            ('COLLECTION', "Collection", "Collection divider for grouping"),
            ('CURVE_SYNC', "Curve Sync", "Blender Curve object synced as a pipe-mesh (chain of capsule primitives)"),
        ],
        name="Type", default='PRIMITIVE', update=update_sdf_callback
    )
    name_override: bpy.props.StringProperty(name="Name Override", default="Collection", update=update_sdf_callback)
    empty_ptr: bpy.props.PointerProperty(name="Group Empty", type=bpy.types.Object)
    start_new_group: bpy.props.BoolProperty(name="Start New Group", default=False, update=update_sdf_callback)
    is_layer_boundary: bpy.props.BoolProperty(
        name="Layer Boundary",
        description="Evaluate this divider's group as a local layer and union the layer result back into the scene",
        default=False,
        update=update_sdf_callback
    )


class SDF_ObjectProperties(bpy.types.PropertyGroup):
    is_primitive: bpy.props.BoolProperty(name="Is SDF Primitive", default=False, update=update_sdf_callback)
    shape_type: bpy.props.EnumProperty(
        items=[
            ('sphere', "Sphere", ""),
            ('box', "Box", ""),
            ('rounded_box', "Rounded Box", ""),
            ('torus', "Torus", ""),
            ('cylinder', "Cylinder", ""),
            ('capsule', "Capsule", ""),
            ('hex_prism', "Hex Prism", ""),
            ('pyramid', "Pyramid", ""),
            ('capped_cone', "Tapered Cylinder", ""),
            ('ngon_prism', "N-gon Prism", ""),
            ('ellipsoid', "Ellipsoid", "Axis-aligned ellipsoid"),
            ('rounded_cylinder', "Rounded Cylinder", "Cylinder with rounded edges"),
            ('capped_torus', "Capped Torus", "Partial torus (arc)"),
            ('octahedron', "Octahedron", "Regular octahedron"),
            ('cut_sphere', "Cut Sphere", "Sphere cut by a plane"),
            ('math_field', "Math Field", "Periodic mathematical field surface clipped by extent"),
            ('extrude', "Extrude (2D Profile)", "Extrude 2D profile along Z axis"),
            ('lathe', "Lathe (Revolve)", "Revolve 2D profile around Y axis"),
            ('bezier_curve', "Bezier Curve (3D)", "3D Quadratic Bezier Curve with taper")
        ],
        name="Shape", default='sphere', update=update_sdf_callback
    )
    bezier_pt_b: bpy.props.FloatVectorProperty(name="Control Point B (Mid)", default=(1.0, 1.0, 0.0), update=update_sdf_callback)
    bezier_pt_c: bpy.props.FloatVectorProperty(name="Control Point C (End)", default=(2.0, 0.0, 0.0), update=update_sdf_callback)
    bezier_start_radius: bpy.props.FloatProperty(name="Start Radius", default=0.3, min=0.001, max=10.0, update=update_sdf_callback)
    bezier_end_radius: bpy.props.FloatProperty(name="End Radius", default=0.1, min=0.001, max=10.0, update=update_sdf_callback)
    profile_2d_type: bpy.props.EnumProperty(
        items=[
            ('box', "Rectangle / Box", "2D Box profile"),
            ('circle', "Circle", "2D Circle profile"),
            ('ngon', "N-gon Polygon", "2D Regular polygon profile"),
            ('star', "Star", "2D Star profile"),
        ],
        name="2D Profile", default='box', update=update_sdf_callback
    )
    extrude_depth: bpy.props.FloatProperty(name="Depth", default=1.0, min=0.01, max=100.0, update=update_sdf_callback)
    extrude_chamfer: bpy.props.FloatProperty(name="Chamfer", default=0.0, min=0.0, max=2.0, update=update_sdf_callback)
    profile_corner_radius: bpy.props.FloatProperty(name="Corner Radius", default=0.1, min=0.0, max=5.0, update=update_sdf_callback)
    lathe_offset: bpy.props.FloatProperty(name="Lathe Radius / Offset", default=1.0, min=0.0, max=100.0, update=update_sdf_callback)
    
    # --- Curve Sync: このオブジェクトが CURVE_SYNC スタックアイテムとして使われた場合の
    # パイプ半径・分割数。Curve タイプのオブジェクト自身に持たせる（色/operation/smoothness は
    # 下の color/operation/smoothness フィールドを共用する）
    curve_pipe_radius: bpy.props.FloatProperty(name="Pipe Radius", default=0.15, min=0.001, max=10.0, update=update_sdf_callback)
    curve_sample_resolution: bpy.props.IntProperty(name="Sample Subdiv", default=16, min=4, max=128, update=update_sdf_callback)
    # --- Curve Sync (Proxy): カーブ本体をSDFコレクションに移動させたくない場合用の代替経路。
    # Empty プロキシ（is_curve_sync_proxy=True）に持たせ、シーン中の任意のカーブを指す。
    # 同じカーブを複数のプロキシから別々の Pipe Radius / Color で参照することもできる。
    is_curve_sync_proxy: bpy.props.BoolProperty(name="Is Curve Sync Proxy", default=False)
    curve_target_obj: bpy.props.PointerProperty(
        name="Curve Object", type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'CURVE',
        update=update_sdf_callback,
    )
    operation: bpy.props.EnumProperty(
        items=[
            ('0', "Union", "", 'ADD', 0), 
            ('1', "Subtract", "", 'REMOVE', 1), 
            ('2', "Intersect", "", 'BOOL_INTERSECT', 2)
        ],
        name="Op", default='0', update=update_sdf_callback
    )
    blend_profile: bpy.props.EnumProperty(
        items=[
            ('0', "Round", "Standard smooth min"),
            ('1', "Sharp", "Pulls in toward the corner"),
            ('2', "Soft", "Gentle, smoothly continuous"),
            ('3', "Tight", "Squared, deep but tight"),
            ('4', "Chamfer", "Flat 45 degree bevel")
        ],
        name="Profile", default='0', update=update_sdf_callback
    )
    chamfer_smooth: bpy.props.FloatProperty(name="Chamfer Smooth", default=0.0, min=0.0, max=2.0, update=update_sdf_callback)
    
    # --- V16: Primitive Edge Profile & Modifiers ---
    edge_profile: bpy.props.EnumProperty(
        items=[
            ('0', "Round", "Standard radius rounding"),
            ('1', "Sharp", "Pulls in toward the corner"),
            ('2', "Soft", "Gentle, smoothly continuous"),
            ('3', "Tight", "Squared, deep but tight"),
            ('4', "Chamfer", "Flat 45 degree bevel")
        ],
        name="Edge Profile", default='0', update=update_sdf_callback
    )
    edge_profile_size: bpy.props.FloatProperty(name="Edge Size", default=0.1, min=0.0, max=100.0, update=update_sdf_callback)
    edge_chamfer_smooth: bpy.props.FloatProperty(name="Edge Chamfer Smooth", default=0.0, min=0.0, max=2.0, update=update_sdf_callback)
    shell_thickness: bpy.props.FloatProperty(name="Shell Thickness", default=0.0, min=0.0, max=100.0, update=update_sdf_callback)
    
    radius: bpy.props.FloatProperty(name="Radius", default=1.0, min=0.01, max=100.0, update=update_sdf_callback)
    smoothness: bpy.props.FloatProperty(name="Smoothness", default=0.2, min=0.0, max=2.0, update=update_sdf_callback)
    color: bpy.props.FloatVectorProperty(name="Color", subtype='COLOR', default=(1.0, 1.0, 1.0), min=0.0, max=1.0, update=update_sdf_callback)
    metallic: bpy.props.FloatProperty(name="Metallic", default=0.0, min=0.0, max=1.0, update=update_sdf_callback)
    roughness: bpy.props.FloatProperty(name="Roughness", default=0.5, min=0.0, max=1.0, update=update_sdf_callback)
    noise_strength: bpy.props.FloatProperty(name="Noise", default=0.0, min=0.0, max=2.0, update=update_sdf_callback)
    noise_scale: bpy.props.FloatProperty(name="Noise Scale", default=5.0, min=0.1, max=50.0, update=update_sdf_callback)
    field_type: bpy.props.EnumProperty(
        items=[
            ('gyroid', "Gyroid", "Classic triply periodic minimal surface"),
            ('schwarz_p', "Schwarz P", "Cubic-symmetry periodic minimal surface"),
            ('schwarz_d', "Schwarz D (Diamond)", "Diamond-symmetry periodic minimal surface"),
        ],
        name="Formula", default='gyroid', update=update_sdf_callback
    )
    gyroid_preset: bpy.props.EnumProperty(
        items=[
            ('CUSTOM', "Custom", "Keep current Math Field parameters"),
            ('FINE', "Fine", "Small cells with thin walls"),
            ('MEDIUM', "Medium", "Balanced cells"),
            ('COARSE', "Coarse", "Large open cells"),
            ('THICK', "Thick", "Stronger thicker walls"),
            ('SHELL', "Shell", "Offset shell pattern"),
        ],
        name="Preset", default='MEDIUM', update=update_gyroid_preset
    )
    gyroid_boundary_mode: bpy.props.EnumProperty(
        items=[
            ('0', "Fade", "Fade out before the extent boundary"),
            ('1', "Open", "Open cut at the extent boundary"),
            ('2', "Box Clip", "Closed intersection with the extent box"),
        ],
        name="Boundary", default='2', update=update_sdf_callback
    )
    gyroid_mask_shape: bpy.props.EnumProperty(
        items=[
            ('0', "Box", "Use Extent as half-size for a box mask"),
            ('1', "Sphere", "Use Extent as radius for a spherical mask"),
            ('2', "Cylinder", "Use Extent as radius and half-height for a capped cylinder mask"),
        ],
        name="Mask", default='0', update=update_sdf_callback
    )
    gyroid_phase: bpy.props.FloatProperty(
        name="Phase",
        description="Shift the Gyroid periodic field without moving the mask",
        default=0.0,
        min=-6.28318530718,
        max=6.28318530718,
        subtype='ANGLE',
        update=update_sdf_callback
    )
    gyroid_axis_x: bpy.props.FloatProperty(name="Axis X", default=1.0, min=0.05, max=8.0, update=update_sdf_callback)
    gyroid_axis_y: bpy.props.FloatProperty(name="Axis Y", default=1.0, min=0.05, max=8.0, update=update_sdf_callback)
    gyroid_axis_z: bpy.props.FloatProperty(name="Axis Z", default=1.0, min=0.05, max=8.0, update=update_sdf_callback)
    is_output: bpy.props.BoolProperty(name="Is SDF Output", default=False, update=update_sdf_callback)
    target_collection: bpy.props.PointerProperty(name="Collection", type=bpy.types.Collection, update=update_sdf_callback)
    resolution: bpy.props.IntProperty(name="Res", default=48, min=16, max=1024, update=update_sdf_callback)
    domain_size: bpy.props.FloatProperty(name="Domain", default=5.0, min=1.0, max=50.0, update=update_sdf_callback)
    auto_domain: bpy.props.BoolProperty(name="Auto Expand Domain", default=True, description="Automatically expand calculation area to fit all primitives", update=update_sdf_callback)

    preview_quality: bpy.props.EnumProperty(
        items=[
            ('LOW', "Low (128)", "Low load. Suitable for simple shapes"),
            ('MID', "Mid (256)", "Balanced. Suitable for standard deformation"),
            ('HIGH', "High (512)", "High quality. Minimizes rendering artifacts for complex deformation")
        ],
        name="Preview Quality", default='LOW', update=_update_preview
    )
    curve_sync_guide_width: bpy.props.FloatProperty(
        name="Curve Sync Guide Line Width",
        description="Line thickness of the lightweight Curve Sync preview guide (viewport only, does not affect the final mesh)",
        default=3.0, min=1.0, max=10.0, update=_update_preview,
    )
    use_live_normals: bpy.props.BoolProperty(name="Real-time Normals", default=False, update=update_sdf_callback)
    protect_partial_mesh: bpy.props.BoolProperty(name="Protect Partial Mesh", default=True, update=update_sdf_callback)
    auto_safe_retry: bpy.props.BoolProperty(name="Auto Safe Retry", default=True, update=update_sdf_callback)
    safe_retry_min_res: bpy.props.IntProperty(name="Retry Min Res", default=64, min=16, max=1024, update=update_sdf_callback)
    auto_chunked_fallback: bpy.props.BoolProperty(name="Chunked CPU Fallback", default=True, update=update_sdf_callback)
    auto_gpu_chunked_fallback: bpy.props.BoolProperty(name="Chunked GPU Fallback", default=True, update=update_sdf_callback)
    auto_chunk_high_res: bpy.props.BoolProperty(name="Auto Chunk High Res", default=True, update=update_sdf_callback)
    auto_chunk_start_res: bpy.props.IntProperty(name="Chunk Start Res", default=512, min=64, max=1024, update=update_sdf_callback)
    chunked_fallback_cells: bpy.props.IntProperty(name="Chunk Cells", default=128, min=32, max=256, update=update_sdf_callback)
    chunk_seam_weld_scale: bpy.props.FloatProperty(name="Seam Weld", default=0.05, min=0.0, max=1.0, precision=3, update=update_sdf_callback)
    meshing_backend: bpy.props.EnumProperty(
        items=[
            ('AUTO', "Auto", "Use the normal selected mesher, then fall back if needed"),
            ('GPU_CHUNKED_MC', "GPU Chunked MC", "Use GPU Marching Cubes in fixed-size chunks from the first request"),
            ('GPU_CHUNKED_DC', "GPU Chunked DC (Seam Test)", "Experimental only. Chunk boundaries can remain visible"),
            ('CPU_CHUNKED_MC', "CPU Chunked MC", "Use CPU Marching Cubes in chunks from the first request")
        ],
        name="Meshing Backend", default='AUTO', update=update_sdf_callback
    )
    algo_type: bpy.props.EnumProperty(
        items=[
            ('MC', "Marching Cubes", "Standard (GPU Sparse Accelerated) - Fast feedback"), 
            ('DC', "Dual Contouring", "Sharp Edges (GPU Sparse Accelerated) - High quality")
        ],
        name="Algo", default='MC', update=update_sdf_callback
    )
    sym_x: bpy.props.BoolProperty(name="X", default=False, update=update_sdf_callback)
    sym_y: bpy.props.BoolProperty(name="Y", default=False, update=update_sdf_callback)
    sym_z: bpy.props.BoolProperty(name="Z", default=False, update=update_sdf_callback)
    
    # --- V13.1: Resolution Presets ---
    res_preset_low: bpy.props.IntProperty(name="Low Preset", default=64, min=16, max=1024, update=update_res_preset)
    res_preset_high: bpy.props.IntProperty(name="High Preset", default=256, min=16, max=1024, update=update_res_preset)
    res_mode_auto_normals: bpy.props.BoolProperty(name="Auto-enable Live Normals on High", default=True, update=update_sdf_callback)
    
    # --- V12: Placement ---
    # --- V12: Reinforced Layout (Layout Stacking) ---
    layout_use_mirror: bpy.props.BoolProperty(name="Mirror", default=False, update=update_sdf_callback)
    layout_use_radial: bpy.props.BoolProperty(name="Radial", default=False, update=update_sdf_callback)
    layout_use_spiral: bpy.props.BoolProperty(name="Spiral", default=False, update=update_sdf_callback)
    layout_use_jitter: bpy.props.BoolProperty(name="Jitter", default=False, update=update_sdf_callback)
    
    # Mirror settings
    mirror_offset: bpy.props.FloatProperty(name="Offset", default=0.0, update=update_sdf_callback)
    mirror_x: bpy.props.BoolProperty(name="X", default=False, update=update_sdf_callback)
    mirror_y: bpy.props.BoolProperty(name="Y", default=False, update=update_sdf_callback)
    mirror_z: bpy.props.BoolProperty(name="Z", default=False, update=update_sdf_callback)
    
    # Radial/Spiral settings
    radial_count: bpy.props.IntProperty(name="Count", default=4, min=1, max=64, update=update_sdf_callback)
    radial_radius: bpy.props.FloatProperty(name="Radius", default=1.0, update=update_sdf_callback)
    radial_axis: bpy.props.EnumProperty(
        items=[('0', "X", ""), ('1', "Y", ""), ('2', "Z", "")],
        name="Axis", default='2', update=update_sdf_callback
    )
    spiral_pitch: bpy.props.FloatProperty(name="Pitch (Height)", default=0.0, update=update_sdf_callback)
    
    # Jitter settings
    jitter_seed: bpy.props.FloatProperty(name="Seed", default=1.0, update=update_sdf_callback)
    jitter_strength: bpy.props.FloatProperty(name="Strength", default=0.0, update=update_sdf_callback)

    # --- V12 Phase 2: Grid & Advanced Rotation ---
    layout_use_grid: bpy.props.BoolProperty(name="Grid", default=False, update=update_sdf_callback)
    grid_count_x: bpy.props.IntProperty(name="Count X", default=1, min=1, max=20, update=update_sdf_callback)
    grid_count_y: bpy.props.IntProperty(name="Count Y", default=1, min=1, max=20, update=update_sdf_callback)
    grid_count_z: bpy.props.IntProperty(name="Count Z", default=1, min=1, max=20, update=update_sdf_callback)
    grid_spacing_x: bpy.props.FloatProperty(name="Spacing X", default=2.0, update=update_sdf_callback)
    grid_spacing_y: bpy.props.FloatProperty(name="Spacing Y", default=2.0, update=update_sdf_callback)
    grid_spacing_z: bpy.props.FloatProperty(name="Spacing Z", default=2.0, update=update_sdf_callback)

    instance_rot_x: bpy.props.FloatProperty(name="Rotation X", default=0.0, subtype='ANGLE', update=update_sdf_callback)
    instance_rot_y: bpy.props.FloatProperty(name="Rotation Y", default=0.0, subtype='ANGLE', update=update_sdf_callback)
    instance_rot_z: bpy.props.FloatProperty(name="Rotation Z", default=0.0, subtype='ANGLE', update=update_sdf_callback)

    step_rot_x: bpy.props.FloatProperty(name="Accum Rot X", default=0.0, subtype='ANGLE', update=update_sdf_callback)
    step_rot_y: bpy.props.FloatProperty(name="Accum Rot Y", default=0.0, subtype='ANGLE', update=update_sdf_callback)
    step_rot_z: bpy.props.FloatProperty(name="Accum Rot Z", default=0.0, subtype='ANGLE', update=update_sdf_callback)
    
    # --- V15: Deform Stack ---
    deform_stack: bpy.props.CollectionProperty(type=SDF_DeformItem)
    deform_stack_index: bpy.props.IntProperty(name="Deform Stack Index", default=0)

    # --- V13: Generic Parameters ---
    p1: bpy.props.FloatProperty(name="Param 1", default=1.0, min=-100.0, max=100.0, update=update_sdf_callback)
    p2: bpy.props.FloatProperty(name="Param 2", default=1.0, min=-100.0, max=100.0, update=update_sdf_callback)
    p3: bpy.props.FloatProperty(name="Param 3", default=1.0, min=-100.0, max=100.0, update=update_sdf_callback)
    p4: bpy.props.FloatProperty(name="Param 4", default=1.0, min=-100.0, max=100.0, update=update_sdf_callback)

    # --- V13: Individual Corrections ---
    ngon_sides: bpy.props.IntProperty(name="Sides", default=6, min=3, max=64, update=update_sdf_callback)

    # --- V13.2: Weld (Merge by Distance) ---
    use_weld: bpy.props.BoolProperty(name="Weld (Merge Verts)", default=True, update=update_sdf_callback)
    weld_threshold: bpy.props.FloatProperty(name="Weld Threshold (Scale)", default=0.001, min=0.0, max=1.0, precision=4, update=update_sdf_callback)

    # --- V7: スタック管理 ---
    sdf_stack: bpy.props.CollectionProperty(type=SDF_StackItem)
    sdf_stack_index: bpy.props.IntProperty(name="Stack Index", default=0, update=update_sdf_callback)
    use_solo: bpy.props.BoolProperty(name="Solo Mode", default=False, update=update_sdf_callback)
