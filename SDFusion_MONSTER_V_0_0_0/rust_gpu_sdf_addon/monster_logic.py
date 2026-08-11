import bpy
import bmesh
import numpy as np
import os
import time

try:
    from . import sdfusion_monster
except ImportError:
    # Fallback for development
    sdfusion_monster = None

class MonsterEngine:
    def __init__(self):
        self.is_initialized = False
        self.last_vertices = None
        self.last_indices = None

    def initialize(self):
        if not self.is_initialized:
            if sdfusion_monster:
                res = sdfusion_monster.init_gpu()
                print(f"Monster Engine: {res}")
                self.is_initialized = True
            else:
                print("Monster Engine: Error - Rust binary not found.")

    def extract_mesh_data(self, obj):
        if obj.type != 'MESH':
            return None
        
        # Get evaluated mesh for modifiers
        depsgraph = bpy.context.evaluated_depsgraph_get()
        obj_eval = obj.evaluated_get(depsgraph)
        mesh = obj_eval.to_mesh()
        
        mesh.calc_loop_triangles()
        
        vertices = []
        for v in mesh.vertices:
            p = obj.matrix_world @ v.co
            vertices.append([p.x, p.y, p.z, 1.0])
            
        indices = []
        for tri in mesh.loop_triangles:
            indices.append([tri.vertices[0], tri.vertices[1], tri.vertices[2]])
            
        obj_eval.to_mesh_clear()
        return vertices, indices

    def generate_mesh(self, primitives_data, resolution, domain_size, domain_center, symmetry, mesh_obj=None, smooth=0.1, deform1=[0,0,0,0], layout1=[0,0,0,0]):
        if not self.is_initialized:
            self.initialize()
        
        if not sdfusion_monster:
            return None, None

        # Convert primitive data to Rust SdfPrimitive objects
        rust_prims = []
        for p in primitives_data:
            rp = sdfusion_monster.SdfPrimitive(
                p['type'],
                p['center'],
                p['rotation'],
                p['radius'],
                p['size'],
                p['op'],
                p['smooth'],
                p['color'],
                p['metallic'],
                p['roughness'],
                p['noise_strength'],
                p['noise_scale'],
                p.get('layout1', [0,0,0,0]),
                p.get('layout2', [0,0,0,0]),
                p.get('layout3', [0,0,0,0]),
                p.get('layout4', [0,0,0,0]),
                p.get('extra', [0,0,0,0]),
                p.get('deform1', [0,0,0,0]),
                p.get('deform2', [0,0,0,0]),
                p.get('deform3', [0,0,0,0]),
                p.get('deform4', [0,0,0,0])
            )
            rust_prims.append(rp)
            
        # Add selected mesh as a Monster primitive if provided
        if mesh_obj:
            res = self.extract_mesh_data(mesh_obj)
            if res:
                mv, mi = res
                flat_v = []
                for v in mv:
                    flat_v.extend([v[0], v[1], v[2], 1.0])
                flat_i = [idx for tri in mi for idx in tri]
                
                # Calculate AABB
                v_coords = [v for v in mv]
                if v_coords:
                    min_v = [min(v[i] for v in v_coords) for i in range(3)]
                    max_v = [max(v[i] for v in v_coords) for i in range(3)]
                    center = [(min_v[i] + max_v[i]) * 0.5 for i in range(3)]
                    size = [(max_v[i] - min_v[i]) * 0.5 for i in range(3)]
                else:
                    center, size = [0,0,0], [1,1,1]
                
                monster_prim = sdfusion_monster.SdfPrimitive(
                    "mesh",
                    center, [0,0,0,1], 0.0, size, 0, smooth, [1,1,1], 0.0, 0.5, 0.0, 1.0,
                    layout_data1=layout1,
                    deform_data1=deform1,
                    vertices=flat_v,
                    indices=flat_i
                )
                rust_prims.append(monster_prim)

        # Call GPU generation
        start_time = time.time()
        print(f"Monster Engine: Starting GPU Pipeline (Res: {resolution}, Prims: {len(rust_prims)})")
        
        verts, indices = sdfusion_monster.generate_mesh_gpu(
            rust_prims,
            resolution,
            domain_size,
            domain_center,
            symmetry
        )
        duration = time.time() - start_time
        v_count = len(verts) // 11
        i_count = len(indices)
        
        print(f"Monster Engine: Completed in {duration:.4f}s")
        print(f"  - Output Vertices: {v_count}")
        print(f"  - Output Triangles: {i_count // 3}")
        
        return verts, indices

def create_blender_mesh(name, vertices, indices):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    # Vertices are packed as [x, y, z, r, g, b, met, rou, nx, ny, nz]
    v_count = len(vertices) // 11
    coords = []
    for i in range(v_count):
        coords.append((vertices[i*11], vertices[i*11+1], vertices[i*11+2]))
    
    mesh.from_pydata(coords, [], [indices[i:i+3] for i in range(0, len(indices), 3)])
    mesh.update()
    
    # Add vertex colors and attributes
    # TODO: Implement attribute transfer
    
    return obj
