import codecs

file_path = 'rust_gpu_sdf_addon/__init__.py'
with codecs.open(file_path, 'r', 'utf-8') as f:
    code = f.read()

target = '''    operators.SDF_OT_bake_mesh,'''
insert = '''    operators.SDF_OT_duplicate_collection,
    operators.SDF_OT_bake_mesh,'''

code = code.replace(target, insert, 1)

with codecs.open(file_path, 'w', 'utf-8') as f:
    f.write(code)

print('__init__.py successfully patched.')
