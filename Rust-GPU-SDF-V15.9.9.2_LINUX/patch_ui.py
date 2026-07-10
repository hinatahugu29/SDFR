import codecs

file_path = 'rust_gpu_sdf_addon/ui.py'
with codecs.open(file_path, 'r', 'utf-8') as f:
    code = f.read()

target = '''                op.index = index
                row.prop(item, "start_new_group", text="", toggle=True, emboss=False, icon='LINKED' if not item.start_new_group else 'UNLINKED')'''

insert = '''                op.index = index
                op_dup = row.operator("sdf.duplicate_collection", text="", icon='DUPLICATE', emboss=False)
                op_dup.index = index
                row.prop(item, "start_new_group", text="", toggle=True, emboss=False, icon='LINKED' if not item.start_new_group else 'UNLINKED')'''

code = code.replace(target, insert, 1)

with codecs.open(file_path, 'w', 'utf-8') as f:
    f.write(code)

print('ui.py successfully patched.')
