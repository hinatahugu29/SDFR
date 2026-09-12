# SDF.R V16拡張計画: カーブ・押し出し・回転体の実装構想 (V15.9.9向け統合検討)

ユーザーより、既存の提案書 `SDF_R_Curve_Extension_Plan.md` を現在の `Rust-GPU-SDF-V15.9.9` プロジェクトへ統合するための検討依頼を受けました。まずはコードの発行を行わず、どのようにこのプロジェクトに組み込むかの具体的な設計とアプローチをすり合わせます。

## 概要

海外からの要望にもあった「押し出し（Extrude）」「回転体（Lathe）」「カーブ（Curves）」を、現在のSDF.Rのアーキテクチャ（WGSL + Rustコア）の枠組み内で効率的に実装します。
今回は「レベル1：数学的な基本カーブ」および「シンプルな2D形状の3D化」にスコープを絞り、既存の固定サイズデータ構造（`GpuPrimitive`）を維持したまま最小限の変更で最大の効果を得るアプローチをとります。

## User Review Required

> [!IMPORTANT]
> - 本計画はデータ構造 (`GpuPrimitive`) を大きく変更しないアプローチ（`extra_params` などのパッキングによる流用）をとります。これによりパフォーマンスやメモリレイアウトへの影響を最小限に抑えます。この方針で進めて問題ないか確認をお願いします。
> - 現時点での優先順位（Extrudeを先にするか、Bezier Curveを先にするか等）や、UI上での見せ方にご希望があれば教えてください。

## Proposed Changes

現在のV15.9.9のファイル構造に基づく、具体的な変更予定箇所は以下の通りです。

### WGSL層 (Shader / GPU 計算)

#### [MODIFY] [src/common.wgsl](file:///g:/blender_addon/外部テスト/Rust-GPU-SDF-V15.9.9/src/common.wgsl)
- **2D SDF関数群の追加**: `sdBox2D`, `sdCircle2D`, `sdHexagon2D` 等。
- **押し出し (Extrude) 関数 (`opExtrude`)**: 2D距離を元にZ方向の厚みを持たせる関数。
- **回転体 (Lathe) 関数 (`opLathe`)**: 2DプロファイルをY軸周りに回転させる関数。
- **数学的基本カーブ (`sdBezier`)**: 3つの制御点で定義される2次ベジェ曲線の距離関数。

### Rust層 (Core Engine)

#### [MODIFY] [src/primitive.rs](file:///g:/blender_addon/外部テスト/Rust-GPU-SDF-V15.9.9/src/primitive.rs)
- `ShapeType` 列挙型に新規IDを割り当て (`ExtrudedShape`, `LathedShape`, `BezierCurve` など)。

#### [MODIFY] [src/sdf.rs](file:///g:/blender_addon/外部テスト/Rust-GPU-SDF-V15.9.9/src/sdf.rs)
- `calculate_primitive_sdf()` にCPU側でのバウンディングボックス(AABB)計算用ロジック（ベジェ曲線が収まる範囲など）を追加。

### Python層 (UI & Data Management)

#### [MODIFY] [rust_gpu_sdf_addon/properties.py](file:///g:/blender_addon/外部テスト/Rust-GPU-SDF-V15.9.9/rust_gpu_sdf_addon/properties.py)
- `shape_type` (Enum) の選択肢に新形状を追加。
- `bezier_point_b`, `bezier_point_c`, `extrude_depth`, `lathe_offset` などのプロパティ定義を追加。

#### [MODIFY] [rust_gpu_sdf_addon/ui.py](file:///g:/blender_addon/外部テスト/Rust-GPU-SDF-V15.9.9/rust_gpu_sdf_addon/ui.py)
- 選択された `shape_type` に応じて、Extrude/Lathe用のパラメータや、Bezier用のコントロールポイント入力UIを表示するようにレイアウトを調整。

#### [MODIFY] [rust_gpu_sdf_addon/engine.py](file:///g:/blender_addon/外部テスト/Rust-GPU-SDF-V15.9.9/rust_gpu_sdf_addon/engine.py) / [rust_gpu_sdf_addon/handlers.py](file:///g:/blender_addon/外部テスト/Rust-GPU-SDF-V15.9.9/rust_gpu_sdf_addon/handlers.py)
- 新しい形状のドメイン自動拡張（AABB最大半径の計算）に対応するためのロジック追加。特にベジェ曲線の場合、3点が含まれるAABBの計算式を適用。

## Verification Plan
1. **WGSL単体テスト**: `common.wgsl` に追加した関数が既存のコンパイルを壊さないか確認。
2. **Rustビルド検証**: 追加した `ShapeType` とパラメータパッキングが正しくビルドできるか確認。
3. **Blender上での描画確認**: Python側から新規形状を追加し、期待通りに3D描画（Extrude, Lathe, Bezier）が行われるかを確認。
