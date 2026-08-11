bl_info = {
    "name": "SDFusion MONSTER Edition",
    "author": "Antigravity",
    "version": (0, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Monster",
    "description": "GPU Accelerated SDF Modeling Engine",
    "category": "Mesh",
}

import bpy
import time
from . import monster_logic

# Global engine instance for performance
_engine = None

def get_engine():
    global _engine
    if _engine is None:
        _engine = monster_logic.MonsterEngine()
    return _engine

def update_monster(self, context):
    if context.scene.monster_auto_run:
        bpy.ops.monster.generate()

class MONSTER_OT_generate(bpy.types.Operator):
    bl_idname = "monster.generate"
    bl_label = "Generate Monster Mesh"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        monster_engine = get_engine()
        
        # Get settings from UI
        res = scene.monster_res
        domain = scene.monster_domain
        smooth = scene.monster_smooth
        
        # Collect Deform Params
        # Packed as: [flags, param_y, param_z, param_w]
        # Flag bits for dt: 2=Bend, 3=Twist, 4=Taper
        deform1 = [0, 0, 0, 0]
        if abs(scene.monster_bend) > 0.001:
            deform1[0] |= 2  # Bend (dt=2)
            deform1[1] = scene.monster_bend
        if abs(scene.monster_twist) > 0.001:
            deform1[0] |= (3 << 6) # Twist (2nd slot, dt=3)
            # Twist/Taper params would need more complex packing, but for now we simplify
        
        # Collect Layout Params
        # Flag bits: 1=Mirror, 2=Radial
        layout1 = [0, 0, 0, 0]
        if scene.monster_mirror:
            layout1[0] |= 1
            layout1[1] = 0.0 # offset
        if scene.monster_radial_count > 1:
            layout1[0] |= 2
            layout1[0] |= (scene.monster_radial_count << 12)
            layout1[2] = scene.monster_radial_radius
        
        # Target object
        target_obj = None
        if scene.monster_use_selected and context.active_object:
            target_obj = context.active_object
        
        # Base primitives
        prims = []
        
        # Default sphere only if no mesh is selected
        if not target_obj:
            prims.append({
                'type': 'sphere',
                'center': [0, 0, 0],
                'rotation': [0, 0, 0, 1],
                'radius': 1.0,
                'size': [1, 1, 1],
                'op': 0, 
                'smooth': smooth,
                'color': [1, 0.4, 0.1], # Monster Orange
                'metallic': 0.1,
                'roughness': 0.4,
                'noise_strength': 0.0,
                'noise_scale': 1.0,
                'deform1': deform1,
                'layout1': layout1
            })
        
        verts, indices = monster_engine.generate_mesh(
            primitives_data=prims,
            resolution=res,
            domain_size=domain,
            domain_center=[0, 0, 0],
            symmetry=0,
            mesh_obj=target_obj,
            smooth=smooth,
            deform1=deform1,
            layout1=layout1
        )
        
        if verts:
            obj = monster_logic.create_blender_mesh("MonsterResult", verts, indices)
            context.view_layer.objects.active = obj
            obj.select_set(True)
        
        return {'FINISHED'}

class MONSTER_PT_panel(bpy.types.Panel):
    bl_label = "SDFusion MONSTER"
    bl_idname = "MONSTER_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Monster'
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # --- Header ---
        row = layout.row(align=True)
        row.label(text="MONSTER ENGINE", icon='MODIFIER')
        
        # --- Core Settings ---
        col = layout.column(align=True)
        box = col.box()
        box.label(text="Engine Pipeline", icon='NODE_COMPOSITING')
        box.prop(scene, "monster_res", text="Voxel Res")
        box.prop(scene, "monster_domain", text="World Scale")
        
        # --- Mesh Integration ---
        box = col.box()
        box.label(text="Mesh SDF Integration", icon='MESH_DATA')
        box.prop(scene, "monster_use_selected", text="Enable BVH Mesh")
        box.prop(scene, "monster_smooth", text="Fusion Smooth")
        
        # --- Deform Stack ---
        box = col.box()
        box.label(text="Deform Stack", icon='MOD_SIMPLEDEFORM')
        grid = box.grid_flow(columns=2, align=True)
        grid.prop(scene, "monster_bend")
        grid.prop(scene, "monster_twist")
        grid.prop(scene, "monster_taper")
        
        # --- Layout Stack ---
        box = col.box()
        row = box.row()
        row.label(text="Array Layout", icon='MOD_ARRAY')
        row.prop(scene, "monster_mirror", toggle=True, icon='MOD_MIRROR')
        
        if scene.monster_radial_count > 1:
            sub = box.column(align=True)
            sub.prop(scene, "monster_radial_count")
            sub.prop(scene, "monster_radial_radius")
        
        layout.separator()
        
        # --- Execute ---
        row = layout.row(align=True)
        row.scale_y = 1.5
        row.prop(scene, "monster_auto_run", text="LIVE MODE", icon='RECOVER_LAST', toggle=True)
        
        row = layout.row()
        row.scale_y = 2.0
        row.operator("monster.generate", text="MONSTER GENERATE", icon='PLAY')

def register():
    bpy.utils.register_class(MONSTER_OT_generate)
    bpy.utils.register_class(MONSTER_PT_panel)
    
    bpy.types.Scene.monster_res = bpy.props.IntProperty(name="Resolution", default=64, min=32, max=512, update=update_monster)
    bpy.types.Scene.monster_domain = bpy.props.FloatProperty(name="Domain Size", default=4.0, min=0.1, max=100.0, update=update_monster)
    bpy.types.Scene.monster_use_selected = bpy.props.BoolProperty(name="Use Selected", default=False, update=update_monster)
    bpy.types.Scene.monster_smooth = bpy.props.FloatProperty(name="Smoothness", default=0.2, min=0.0, max=2.0, update=update_monster)
    bpy.types.Scene.monster_auto_run = bpy.props.BoolProperty(name="Auto Run", default=False)
    
    # Deform
    bpy.types.Scene.monster_bend = bpy.props.FloatProperty(name="Bend", default=0.0, min=-5.0, max=5.0, update=update_monster)
    bpy.types.Scene.monster_twist = bpy.props.FloatProperty(name="Twist", default=0.0, min=-10.0, max=10.0, update=update_monster)
    bpy.types.Scene.monster_taper = bpy.props.FloatProperty(name="Taper", default=0.0, min=-1.0, max=1.0, update=update_monster)
    
    # Layout
    bpy.types.Scene.monster_mirror = bpy.props.BoolProperty(name="Mirror", default=False, update=update_monster)
    bpy.types.Scene.monster_radial_count = bpy.props.IntProperty(name="Radial Count", default=1, min=1, max=32, update=update_monster)
    bpy.types.Scene.monster_radial_radius = bpy.props.FloatProperty(name="Radial Radius", default=2.0, update=update_monster)

def unregister():
    bpy.utils.unregister_class(MONSTER_OT_generate)
    bpy.utils.unregister_class(MONSTER_PT_panel)
    
    del bpy.types.Scene.monster_res
    del bpy.types.Scene.monster_domain
    del bpy.types.Scene.monster_use_selected
    del bpy.types.Scene.monster_smooth
    del bpy.types.Scene.monster_bend
    del bpy.types.Scene.monster_twist
    del bpy.types.Scene.monster_taper
    del bpy.types.Scene.monster_mirror
    del bpy.types.Scene.monster_radial_count
    del bpy.types.Scene.monster_radial_radius

if __name__ == "__main__":
    register()
