# SDF-R (Rust-GPU-SDF) Technical Specification & Evolution Log
**Version: 15.9 (Cumulative Update)**

## 1. プロジェクト概要
SDF-Rは、RustとGPU（WGSL）を高度に組み合わせた、Blender向け次世代SDF（Signed Distance Field）モデリングエンジンです。プレビューの軽快さと、最終メッシュ生成の正確性を両立させることを目的としています。

## 2. コア・テクノロジースタック
- **Logic**: Rust (v1.80+)
- **GPU API**: wgpu (Vulkan / DirectX 12 / Metal 対応)
- **Shader**: WGSL (WebGPU Shading Language)
- **Host Interface**: Python 3.10/3.11 (PyO3によるバインディング)
- **Algorithms**: Sparse Dual Contouring / Marching Cubes (可変選択式)

---

## 3. バージョン V15.9 における到達点
V15.9では、長年の課題であった「ビューポートの見た目と最終メッシュの不一致」を完全に解消し、製品レベルの信頼性を確保しました。

### 3.1 数学的なスケーリング同期 (Multiplicative Scaling)
SDFプリミティブのサイズ計算において、従来の「加算方式」から「乗算方式」へ移行し、Blenderのスケール操作と完全同期させました。
- **計算式**: `distance = (length(p / scale) - radius) * min_scale`
- **利点**: 非一様なスケール（楕円体など）を適用しても、プレビューとメッシュが1:1で一致します。

### 3.2 UIレスポンスの最適化 (Evaluated vs Original)
BlenderのDepsgraph（依存関係グラフ）のラグ問題を解消しました。
- **設計方針**: 行列（Transform）は `Evaluated` から、パラメータ（Union/Subtract/Radius等）は `Original` から取得。
- **成果**: 加減算の切り替えボタンを押した瞬間に、再評価を待たずにメッシュが即座に更新されます。

---

## 4. プリミティブ・データ構造
PythonからRustエンジンへは、1プリミティブあたり「15ピクセル分（64 floats）」のデータがパッキングされて送られます。

| データスロット | 格納内容 | 備考 |
| :--- | :--- | :--- |
| `center_and_shape` | xyz: 中心座標, w: 形状タイプ | sphere(0), box(1), etc. |
| `rotation` | xyzw: クォータニオン | |
| `size_and_op` | xyz: スケール, w: 演算タイプ | Union(0), Subtract(1), etc. |
| `params` | x: radius, y: smooth, zw: mat/rough | V15.9の同期コア |
| `noise_params` | x: strength, y: scale, zw: color(RG) | |
| `layout_data` | 4 slots: Mirror, Radial, Grid, Jitter | 複雑な配置ロジック |
| `deform_data` | 4 slots: Bend, Twist, Taper, etc. | 動的デフォームスタック |

---

## 5. デフォーム・パイプラインの順序
正確な形状生成のため、以下の順序で空間が評価されます。
1. **Local Space Transform**: オブジェクトの座標・回転の逆変換。
2. **Layout Stacking**: Mirror -> Radial -> Grid -> Jitter の順で空間を反復。
3. **Deform Stack**: 最大4つまでのデフォーマーを直列に適用。
4. **Distance Evaluation**: `common.wgsl` による距離関数計算。
5. **Final Scaling**: `min_scale` を乗算してグローバル空間の距離に復元。

---

## 6. ビルドと配備
### 6.1 Rustバイナリの構築
```powershell
$env:PYO3_PYTHON = "path/to/python.exe"
cargo build --release
```
生成された `rust_gpu_sdf.dll` を `rust_gpu_sdf.pyd` にリネームしてアドオンフォルダへ配置します。

### 6.2 シェーダーの変更
`common.wgsl` を変更した場合は、必ずRustバイナリの再ビルドが必要です。これは実行速度を最大化するために、シェーダーソースがバイナリにインライン化されているためです。

---

## 7. 今後のロードマップ
- **V16.x**: ユーザー定義MeshのSDF化（SDF Baker）の安定性向上。
- **V17.x**: マルチOS対応（GitHub ActionsによるMac/Linux自動ビルドの導入）。
- **Performance**: 大規模シーンにおけるBVH（Bounding Volume Hierarchy）の更なる最適化。

---
*Documented by Antigravity on 2026-05-03*
