import sys
import py_compile
import os

addon_files = [
    "rust_gpu_sdf_addon/__init__.py",
    "rust_gpu_sdf_addon/properties.py",
    "rust_gpu_sdf_addon/ui.py",
    "rust_gpu_sdf_addon/operators.py",
    "rust_gpu_sdf_addon/handlers.py",
    "rust_gpu_sdf_addon/engine.py",
    "rust_gpu_sdf_addon/constants.py",
    "rust_gpu_sdf_addon/shader.py",
]

print("=== Syntax Check ===")
has_error = False
for f in addon_files:
    try:
        py_compile.compile(f, doraise=True)
        print(f"OK: {f}")
    except py_compile.PyCompileError as e:
        print(f"ERROR in {f}:")
        print(e)
        has_error = True

if has_error:
    sys.exit(1)
else:
    print("All python files compiled successfully!")
    sys.exit(0)
