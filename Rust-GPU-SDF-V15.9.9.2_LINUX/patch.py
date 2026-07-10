import codecs

file_path = 'rust_gpu_sdf_addon/ui.py'
with codecs.open(file_path, 'r', 'utf-8') as f:
    code = f.read()

target1 = '''                if empty_props.layout_use_jitter:'''
insert1 = '''                if empty_props.layout_use_radial or empty_props.layout_use_spiral:
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

                if empty_props.layout_use_jitter:'''

code = code.replace(target1, insert1, 1)

target2 = '''                # Advanced Rotation (Individual & Step)
                col_rot = box.column(align=True)
                col_rot.label(text="Rotation (Indiv & Accum):", icon='FILE_REFRESH')
                row = col_rot.row(align=True)
                row.prop(props, "instance_rot_x", text="X")
                row.prop(props, "instance_rot_y", text="Y")
                row.prop(props, "instance_rot_z", text="Z")
                row = col_rot.row(align=True)
                row.prop(props, "step_rot_x", text="X")
                row.prop(props, "step_rot_y", text="Y")
                row.prop(props, "step_rot_z", text="Z")'''

insert2 = '''                # Advanced Rotation (Individual & Step)
                if props.layout_use_radial or props.layout_use_spiral:
                    col_rot = box.column(align=True)
                    col_rot.label(text="Rotation (Indiv & Accum):", icon='FILE_REFRESH')
                    row = col_rot.row(align=True)
                    row.prop(props, "instance_rot_x", text="X")
                    row.prop(props, "instance_rot_y", text="Y")
                    row.prop(props, "instance_rot_z", text="Z")
                    row = col_rot.row(align=True)
                    row.prop(props, "step_rot_x", text="X")
                    row.prop(props, "step_rot_y", text="Y")
                    row.prop(props, "step_rot_z", text="Z")'''

code = code.replace(target2, insert2, 1)

with codecs.open(file_path, 'w', 'utf-8') as f:
    f.write(code)

print('ui.py successfully patched.')
