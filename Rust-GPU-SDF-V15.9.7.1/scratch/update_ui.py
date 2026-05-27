import os
path = "rust_gpu_sdf_addon/ui.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()
content = content.replace('chamfer_smooth", text="Smooth"', 'chamfer_smooth", text="係数"')
with open(path, "w", encoding="utf-8") as f:
    f.write(content)
