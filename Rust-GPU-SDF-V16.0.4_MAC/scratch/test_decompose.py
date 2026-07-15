import mathutils

m = mathutils.Matrix.Scale(-1.0, 4, (1.0, 0.0, 0.0))
loc, rot, scale = m.decompose()
with open(r'e:\blender_addon\外部テスト\Rust-GPU-SDF-V15.9.8.1\scratch\test_decompose_out.txt', 'w') as f:
    f.write(f"Det: {m.determinant()}\n")
    f.write(f"Loc: {loc}\n")
    f.write(f"Rot: {rot}\n")
    f.write(f"Scale: {scale}\n")

    recomposed = mathutils.Matrix.Translation(loc) @ rot.to_matrix().to_4x4() @ mathutils.Matrix.Diagonal(scale).to_4x4()
    f.write(f"Recomposed:\n{recomposed}\n")
