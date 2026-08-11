# SDF Collectionのグリッド・ミラー不具合修正計画

ユーザーから「コレクション機能が動きつつありますが、グリッドやミラーなどがまだうまく働いていません」との報告がありました。調査の結果、2つの主要な問題を発見しました。

## 原因と分析

1. **Gridが効かない問題 (スタックの登録順序)**
   - `SDF_Collection` はスタックの順序に依存し、「自身より上にあるプリミティブ」に対して複製（Grid/Mirror）を適用します。
   - しかし、新規オブジェクトをスタックに追加する際、Blenderコレクション内の順序（アルファベット順など任意）でそのまま追加していました。
   - このため、Empty（コレクション区切り）がプリミティブより**先**に追加されると、複製対象（`working_group`）が空となり、Gridが全く適用されません。

2. **Mirrorでオブジェクトが消える問題 (負のスケールのバグ)**
   - Mirror処理は内部的に `Matrix.Scale(-1, ...)` を生成し、複製されたオブジェクトには負のスケールが適用されます。
   - Rust/GPU側ではスケールの絶対値を計算せずにそのままバウンディングボックス（AABB）の半幅(`half_ext`)としていました。
   - この結果、スケールが負の場合に `AABB min > max` となり、レイ・インターセクションやDual Contouringで完全にカリングされ、オブジェクトが消滅していました。
   - さらに、WGSLのSDF評価式でも、負のスケールで距離フィールドを割ると符号が反転し、内側・外側が逆転する問題がありました。

## User Review Required

> [!IMPORTANT]
> - この修正により、コレクションのEmpty（レイアウト機能）が**確実**にプリミティブより下に配置されるようになり、スタック機能が直感的に動作するようになります。
> - また、Rust/GPU側のSDFシェーダーを修正するため、修正後は初回のみシェーダーの再コンパイルが走ります。

## Proposed Changes

### Pythonレイヤー (UIとスタック管理)

#### [MODIFY] [engine.py](file:///e:/blender_addon/外部テスト/Rust-GPU-SDF-V15.9.8.1/rust_gpu_sdf_addon/engine.py)
- `sync_sdf_stack()`: 新規オブジェクトを追加する際、`EMPTY` をリストの末尾にソートしてからスタックに追加するように変更。
- `build_element_primitive()`: Auto Domain計算時の `max_s` 算出に `abs()` を適用し、負のスケールでも正しくドメインを拡張するように修正。

### Rust/GPUレイヤー (AABBとSDF評価)

#### [MODIFY] [lib.rs](file:///e:/blender_addon/外部テスト/Rust-GPU-SDF-V15.9.8.1/src/lib.rs)
- `generate_sdf_mesh_internal()` のAABB計算:
  `half_ext` の各成分計算に `.abs()` を適用し、負のスケールが渡されてもAABBの `min <= max` が保証されるように修正。

#### [MODIFY] [sdf.rs](file:///e:/blender_addon/外部テスト/Rust-GPU-SDF-V15.9.8.1/src/sdf.rs)
- `calculate_primitive_sdf()` のスケール評価:
  スケールの絶対値 (`abs()`) と符号 (`sign()`) を分離。空間座標 `p` は符号付きスケールで割り（ミラー反転を再現）、SDFのスケール係数 `s_min` には絶対値を使用するよう修正。また、Deform計算の `max_s` も `.abs()` に変更。

#### [MODIFY] [common.wgsl](file:///e:/blender_addon/外部テスト/Rust-GPU-SDF-V15.9.8.1/src/common.wgsl)
- `evaluate_shape()` のスケール評価:
  WGSLシェーダー内でも `sdf.rs` と同様に絶対値と符号を分離して扱うように変更。`max_s` を `abs()` ベースで算出するように修正。

## Verification Plan

### Automated Tests
1. Pythonスクリプトを適用し、SDFスタックの更新ロジックをリロードします。
2. Rustコードをコンパイル (`cargo build --release`) します。

### Manual Verification
- Blender上でSDF Collection内にプリミティブとEmptyを追加し、自動的にEmptyがスタックの下に配置されGridが機能するか確認します。
- EmptyのMirror (X, Y, Z) をオンにした際、オブジェクトが消えずに正しく鏡面反転されるか確認します。
