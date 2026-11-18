# SDF.R V17.0.1 UI / Command Inventory

対象バージョン: **Rust-GPU-SDF / SDF.R V17.0.1** | 基準ベース: V17.0.0 / V16.2.2 | 作成日: 2026-10-25  
用途: UIに表出している全パネル・コントロール・ビューポートギズモ・オペレーターの棚卸し資料（マニュアル執筆用リファレンス）

---

## 🚀 V17.0.0 〜 V17.0.1 の主要ハイライト

- **3Dビューポート・ギズモ（Viewport Gizmos）の新規導入（V17.0.0）:**  
  3Dビューポート上で選択したSDFプリミティブの周囲に、直接操作できるカラー矢印（Arrow Gizmo）やボタンスイッチ（Button Gizmo）が表示されます。サイドパネルの数値スライダーに触れずに、フィレット、中空の厚み、スムーズ半径、演算種別、プロファイル、各形状固有サイズを直感的にドラッグ＆クリック操作できるようになりました。
- **Snapshot Mesh / Finalize のマテリアル完全分離（V17.0.1）:**  
  `Snapshot Mesh`（静的メッシュ複製）や `Finalize (Bake All)`（通常メッシュ化確定）を実行した際、メッシュだけでなくマテリアル自身も独立複製されるよう改善されました。ライブSDFツリーのカラー変更やリセットを行っても、作成済みフリーズモデルの外観が変わってしまう問題が解消されています。

---

> **再計算区分の見方:**  
> - **Mesh再計算**: SDF評価を行い、GPU上で結果メッシュを再生成する操作。  
> - **軽量更新**: メッシュ自体は作り直さず、マテリアル属性や表示モードのみを更新する軽量操作。  
> - **表示/管理**: UI上の選択切り替え、階層操作、ツリー管理などの非描画操作。

---

## 目次
- [0. Tree（マルチツリー管理）](#0-treeマルチツリー管理)
- [1. Header / Status](#1-header--status)
- [2. Engine Diagnostics](#2-engine-diagnostics)
- [3. Output & Quality](#3-output--quality)
- [4. Post-Process (Smoothing)](#4-post-process-smoothing)
- [5. The Stack](#5-the-stack)
- [6. Material](#6-material)
- [7. Finalize / Output (V17.0.1更新)](#7-finalize--output-v1701更新)
- [8. Group Settings: Collection Divider](#8-group-settings-collection-divider)
- [8-B. Tree Reference（ツリー参照）](#8-b-tree-referenceツリー参照)
- [9. Primitive Settings](#9-primitive-settings)
- [10. Viewport Gizmos（V17新機能）](#10-viewport-gizmosv17新機能)
- [11. Math Field 専用コマンド](#11-math-field-専用コマンド)
- [12. Layout (Instancing)](#12-layout-instancing)
- [13. Deform (Stack)](#13-deform-stack)
- [14. Add New Primitives](#14-add-new-primitives)
- [15. Object Utilities / Cleanup](#15-object-utilities--cleanup)
- [16. Operator ID 一覧](#16-operator-id-一覧)

---

## 0. Tree（マルチツリー管理）

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|---|---|---|---|---|
| Tree | ドロップダウン `sdf_scene_props.active_tree_index` | 編集対象のSDFツリーを選ぶ。以下のパネル全体（Parts / Stack / Quality / Material）が選択ツリー専用の内容に切り替わる。 | 表示/管理 | ビューポートでパーツを選ぶだけでも、そのパーツが属するツリーへ自動的に切り替わる。 |
| ＋（新規ツリー追加） | ボタン `sdf.add_tree` | 空の新規SDFツリー（コレクションと結果メッシュ）を作成し、アクティブにする。 | 表示/管理 | 背景や別パーツを独立したツリーとして作るときに使う。 |
| −（ツリー削除） | ボタン `sdf.delete_tree` | アクティブなツリーを削除する。 | 表示/管理 | ツリーが1つしかない場合は削除不可。元に戻す場合はUndo。 |
| Tree Name | テキスト `tree.name` | アクティブツリーの表示名・コレクション名を変更する。 | 表示/管理 | 結果メッシュや参照Emptyの名前にも反映される。 |

---

## 1. Header / Status

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|---|---|---|---|---|
| Initialize SDF System | ボタン `sdf.init_scene` | 初期SDFツリー（コレクション、Sphere、結果メッシュ）を作成して利用準備を整える。 | Mesh再計算 | シーンにSDF環境がまだ存在しないときに大きく表示される。 |
| GPU: Ready / Updating | ステータス表示 | GPUバックエンド（Rust / WGPU）の稼働状態を表示。 | 表示/管理 | 非同期更新中は Updating 表示となる。 |
| Live Update | トグル `props.live_update` | パラメータやTransform変更を結果メッシュへ自動反映するかを切り替える。 | 表示/管理 | ON時は編集ごとに自動でMesh再計算が走る。重いシーンでは一時的にOFF推奨。 |
| Auto Wireframe | トグル `props.auto_wireframe` | プリミティブ選択時にワイヤーフレームを自動表示するか制御。 | 軽量更新 | 形状の配置や境界の確認に便利。 |
| Stats / Info | 情報ラベル | プリミティブ数、グリッド解像度、頂点数、GPU処理時間などを表示。 | 表示/管理 | パフォーマンスのボトルネック特定に活用。 |

---

## 2. Engine Diagnostics

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|---|---|---|---|---|
| Run GPU Benchmark | ボタン `sdf.benchmark` | 現在のSDFツリーに対してGPUベンチマークを実行し、平均処理時間を計測。 | Mesh再計算 | グリッド解像度やプリミティブ数に応じた負荷テスト用。 |
| Backend Info | テキスト | 使用中のGPUアダプタ名、Backend API（Vulkan / Metal / DX12等）を表示。 | 表示/管理 | ネイティブDLLの読み込み確認用。 |
| Engine Log Level | 選択 `props.log_level` | コンソール出力のログ詳細度（Error / Warn / Info / Debug / Trace）を設定。 | 表示/管理 | トラブルシューティング時に使用。 |

---

## 3. Output & Quality

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|---|---|---|---|---|
| Resolution Preset | 選択 `props.resolution_preset` | 解像度プリセット（Low / Medium / High / Ultra / Custom）。 | Mesh再計算 | 作業中はMedium、最終確認時はHigh/Ultra等へワンクリックで切り替え。 |
| Grid Resolution | 数値 `props.grid_resolution` | Customプリセット時のボクセル解像度（各軸の分割数）。 | Mesh再計算 | 数値を上げると細部が精密になるがGPUメモリと計算時間が増加。 |
| Adaptive Mesh | トグル `props.use_adaptive` | 平坦部のポリゴンを間引き、曲面に密度を集中させる適応型メッシュを有効化。 | Mesh再計算 | ポリゴン数を抑えつつシャープなエッジを保つ。 |
| Bounding Box Mode | 選択 `props.bbox_mode` | バウンディングボックスの計算方式（Auto / Manual / Tight）。 | Mesh再計算 | 通常はAuto推奨。余白不足で端が切れる場合はManualやPaddingを調整。 |
| BBox Padding | 数値 `props.bbox_padding` | Auto BBox計算時の余白マージン倍率。 | Mesh再計算 | 変形やスムーズブレンドで外側に広がる形状の端切れを防止。 |

---

## 4. Post-Process (Smoothing)

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|---|---|---|---|---|
| Enable Smoothing | トグル `props.enable_smoothing` | 生成メッシュに対する事後スムージング処理（Laplacian / Taubin）を有効化。 | Mesh再計算 | マーチングキューブ特有の微細な段差やジャギーを軽減。 |
| Smoothing Iterations | 数値 `props.smoothing_iterations` | スムージングの反復適用回数。 | Mesh再計算 | 回数を増やすと滑らかになるが、エッジが丸まり体積がわずかに縮む傾向がある。 |
| Smoothing Factor | 数値 `props.smoothing_factor` | 1ステップあたりのスムージング強度。 | Mesh再計算 | 微調整用。通常は0.2〜0.5程度。 |

---

## 5. The Stack

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|---|---|---|---|---|
| Stack UIList | リスト `tree.stack_items` | 現在のSDFツリーを構成するプリミティブおよびCollection Dividerの階層順一覧。 | 表示/管理 | 上から下へ順番にブーリアン評価される。ドラッグや上下ボタンで順序変更可能。 |
| ▲ / ▼（移動ボタン） | ボタン `sdf.stack_move` | 選択アイテムのスタック内実行順序を上下に移動する。 | Mesh再計算 | ブーリアン演算の適用順が変わるため形状が変化する。 |
| ＋（Divider追加） | ボタン `sdf.add_collection_divider` | グループ境界となるCollection Dividerを追加する。 | Mesh再計算 | パーツ群をサブツリーとしてカプセル化し、局所的なブレンドを可能にする。 |
| −（アイテム削除） | ボタン `sdf.remove_stack_item` | 選択中のプリミティブまたはDividerをスタックから削除する。 | Mesh再計算 | 3Dビューポート上のオブジェクトも連動して削除される。 |
| Active Item Indicator | ラジオ/選択 | ビューポートでの選択とStack上での選択を双方向同期。 | 表示/管理 | クリックしたアイテムのパラメータがPrimitive Settingsに即座に表示。 |

---

## 6. Material

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|---|---|---|---|---|
| Setup Material | ボタン `sdf.setup_material` | 頂点カラー（Color Attribute）を反映する標準PBRシェーダーノードを構築する。 | 軽量更新 | マテリアルが存在しない場合やリセット時にワンクリックで作成。 |
| Reset Shader Nodes | ボタン `sdf.reset_material` | シェーダーノードを初期のクリーンな状態に初期化する。 | 軽量更新 | 独自ノード追加後に標準状態に戻したい場合に使用。 |
| Apply Color To All | ボタン `sdf.apply_color_all` | 指定した単一カラーをツリー内の全プリミティブへ一括適用する。 | 軽量更新 | 全体の色味を統一する際に便利。全体一色化のため軽量更新で済む。 |
| Apply Material To All | ボタン `sdf.apply_material_all` | 指定したMetallic / Roughnessをツリー内の全プリミティブへ一括適用する。 | 軽量更新 | 全体の質感を統一する。 |
| Transmission Warning | 警告表示 | Transmissionはプリミティブ個別ではなくマテリアル全体（Whole-material）の値である旨の注記。 | 表示/管理 | 個別プリミティブごとの透過率分けは非対応。 |

---

## 7. Finalize / Output (V17.0.1更新)

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|---|---|---|---|---|
| Fix Normals | ボタン `sdf.update_normals` | SDF勾配から計算した高品質法線を結果メッシュに再計算して適用する。 | Mesh再計算 | レンダリング前の法線シェーディング仕上げ確認用。 |
| Force Update | ボタン `sdf.generate_mesh` | Live Update OFF時などに、手動でSDF結果メッシュを強制再計算する。 | Mesh再計算 | 重い編集を行った後の反映に使用。 |
| Snapshot Mesh | ボタン `sdf.bake_mesh` | 現在のSDF結果から静的なメッシュコピーを複製作成する（Live編集環境はそのまま保持）。 | 表示/管理 | **V17.0.1改善:** メッシュ複製と同時に**マテリアル自身も独立複製**されるようになり、フリーズ後のモデル色がLiveツリーの編集によって変化しない。 |
| Finalize (Bake All) | ボタン `sdf.finalize` | SDF結果を独立した通常メッシュとして確定し、元プリミティブを履歴コレクションへ退避する。 | Mesh再計算/確定 | **V17.0.1改善:** バックアップマテリアルが独立複製され、`SDF_Result` オブジェクト名が安全に管理される。対象はアクティブツリー1本のみ。 |

---

## 8. Group Settings: Collection Divider

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|---|---|---|---|---|
| Name | テキスト `item.name_override` | Stack上のCollection Divider表示名を変更する。 | Mesh再計算 | グループの識別用（頭部、胴体、腕など）。 |
| Operation | 選択 `item.operation` | グループ全体をメインツリーへ結合するブーリアン演算（Union / Subtract / Intersect）。 | Mesh再計算 | グループ内の複数パーツを合成した結果をメインツリーに対してどう演算するかを指定。 |
| Blend Profile | 選択 `item.blend_profile` | グループ境界のブレンドスタイル（Round / Sharp / Soft / Tight / Chamfer）。 | Mesh再計算 | グループ全体と外側との接合部の丸み形状を決定。 |
| Smoothness | 数値 `item.smoothness` | グループ境界のブレンド半径。 | Mesh再計算 | グループ全体を大きな単位で滑らかに馴染ませる。 |

---

## 8-B. Tree Reference（ツリー参照）

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|---|---|---|---|---|
| Add Tree Reference | ボタン `sdf.add_tree_ref` | 別ツリーを取り込む参照Emptyをアクティブツリー内に作成する。 | Mesh再計算 | 作成されたEmptyはTransform（位置・回転・拡縮）可能。 |
| Referenced Tree | ドロップダウン `obj.sdf_ref_tree` | 参照先となるSDFツリーを指定する。 | Mesh再計算 | 共通パーツ（タイヤ、手足、ボルト等）を複数箇所から再利用できる。 |
| Operation / Smoothness | 各設定 | 参照ツリーをメインツリーへ結合する際のブーリアン演算とスムーズ量。 | Mesh再計算 | 通常のプリミティブと同様に結合挙動をカスタマイズ可能。 |

---

## 9. Primitive Settings

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|---|---|---|---|---|
| Shape | ドロップダウン `obj.sdf_shape_type` | 選択プリミティブの形状タイプを変更する（Sphere, Box, Cylinder等）。 | Mesh再計算 | 既存のTransformや階層順序を保ったまま別の幾何形状へ即座に変更可能。 |
| Operation | ボタン切替 `obj.sdf_operation` | ブーリアン演算を指定（Union / Subtract / Intersect）。 | Mesh再計算 | **ギズモ対応**: 3Dビューポート上のボタンスイッチでもワンクリック切替可能。 |
| Blend Profile | 選択 `obj.sdf_blend_profile` | エッジ・接合部の丸み形状（Round / Sharp / Soft / Tight / Chamfer）。 | Mesh再計算 | **ギズモ対応**: 3Dビューポート上のボタンスイッチでも切替可能。 |
| Chamfer Factor | 数値 `obj.sdf_chamfer_factor` | Blend ProfileがChamferの場合の面取り比率。 | Mesh再計算 | 機械的なテーパー・面取り接合を作成する。 |
| Smoothness | 数値 `obj.sdf_smoothness` | 隣接プリミティブとのブレンド半径（滑らかさ）。 | Mesh再計算 | **ギズモ対応**: ビューポート上のマゼンタ矢印ドラッグでも直接調整可能。 |
| Fillet / Edge Size | 数値 `obj.sdf_edge_profile_size` | プリミティブ固有の角丸め・フィレット幅。 | Mesh再計算 | **ギズモ対応**: ビューポート上のオレンジ矢印ドラッグでも直接調整可能。 |
| Shell Thickness | 数値 `obj.sdf_shell_thickness` | 中空（シェル）構造の肉厚。0の場合は完全なソリッド。 | Mesh再計算 | **ギズモ対応**: ビューポート上のシアン矢印ドラッグでも直接調整可能。 |
| Shape Specific Parameters (p1〜p4) | 数値スライダー | 半径、高さ、内径、外径など形状ごとの固有寸法パラメータ。 | Mesh再計算 | **ギズモ対応**: 主要10シェイプはビューポート上の専用矢印で直接ドラッグ可能。 |
| Color | カラーピッカー `obj.sdf_color` | 個別プリミティブの表面カラー。 | Mesh再計算 | パーツ同士が重なり合う部分はブレンド半径に応じてグラデーション混色される。 |
| Metallic / Roughness | 数値 `obj.sdf_metallic` / `sdf_roughness` | 個別プリミティブの金属感および表面の粗さ。 | Mesh再計算 | PBRマテリアル属性として頂点属性にベイクされる。 |

---

## 10. Viewport Gizmos（V17新機能）

### 共通ギズモ（全プリミティブまたは全ソリッド共通）

| ギズモ表示 | 操作方式 | 対応パラメータ | 対象シェイプ | 詳細挙動・役割 |
|---|---|---|---|---|
| **Fillet / Edge Size** (橙矢印) | オレンジ矢印ドラッグ | `sdf_edge_profile_size` | 角を持つ10種（Box, Cylinder, Hex Prism, Pyramid, Tapered Cylinder, N-gon Prism, Rounded Cylinder, Capped Torus, Octahedron, Cut Sphere） | 角の丸め・面取り幅を直感調整。球やトーラスなど角のない滑らかな形状では非表示。 |
| **Shell Thickness** (青緑矢印) | シアン矢印ドラッグ | `sdf_shell_thickness` | 全ソリッドプリミティブ | 中空シェルの肉厚を内側方向へドラッグ調整。 |
| **Smoothness** (赤紫矢印) | マゼンタ矢印ドラッグ | `sdf_smoothness` | 全プリミティブ | 他パーツとのブレンド結合半径をドラッグ調整。単体で重なりがない場合も数値は変化。 |
| **Operation Switch** | 3つのボタンクリック | `sdf_operation` | 全プリミティブ | **Union / Subtract / Intersect** を切替。アクティブな演算は強調表示、他は薄暗く表示。 |
| **Edge Profile Switch** | 5つのボタンクリック | `sdf_blend_profile` | フィレット対応シェイプ | **Round / Sharp / Soft / Tight / Chamfer** の5種を2行配置でワンクリック切替。 |

### シェイプ固有の矢印ギズモ（主要10種）

| 形状タイプ | ギズモ矢印（色・軸） | 対応パラメータ | 詳細挙動 |
|---|---|---|---|
| **Torus** | 矢印2本 | Main Radius / Pipe Radius | ドーナツ全体の主半径と、チューブの太さをそれぞれ独立してドラッグ。 |
| **Cylinder** | 矢印2本 | Radius / Height | 円柱の底面半径と高さをドラッグ調整。 |
| **Capped Cone** | 矢印3本 | Bottom Radius / Top Radius / Height | 円錐台の底面半径、上面半径、全高を直感的に変形。 |
| **Ellipsoid** | 赤・緑・青の3軸矢印 | Radius X / Radius Y / Radius Z | 楕円体の各軸方向の半径をローカルXYZ軸矢印で個別ストレッチ。 |
| **Rounded Cylinder** | 矢印3本 | Radius / Edge Radius / Height | 円柱の半径、上下角の丸み半径、全高を調整。 |
| **Pyramid** | 矢印2本 | Base Size / Height | 四角錐の底面サイズと高さを調整。 |
| **Hex Prism** | 矢印2本 | Radius / Height | 正六角柱の半径と高さをドラッグ調整。 |
| **Rounded Box** | 矢印1本 | Roundness | 角丸立方体の全体的な丸み係数を調整。 |
| **Octahedron** | 矢印1本 | Size | 正八面体の全体寸法をスケール調整。 |
| **Cut Sphere** | 矢印1本 | Cut Height | 球を水平に切り落とすカット位置をドラッグ。 |

> **ギズモ未対応（サイドパネル専用）の項目:**  
> - **Capped Torus の Arc Angle**（回転角度パラメータのため矢印ではなくダイヤル型ギズモを要検討）  
> - **N-gon Prism の辺数**（整数ステップ値のため増減ボタンスタイルが要検討）  
> - **Deform Stack の各項目**（Elongate, Bend, Twist, Taper はリスト構造のためパネル操作）  
> - **ブール関係パラメータ**（2オブジェクト間の個別交差ブレンド設定）

---

## 11. Math Field 専用コマンド

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|---|---|---|---|---|
| Expression | テキスト `obj.sdf_math_expr` | 数式SDFを記述するテキスト入力（例: `length(p) - 1.0`）。 | Mesh再計算 | GLSL風の数式で任意の陰関数曲面を生成可能。 |
| Compile Math Expression | ボタン `sdf.compile_math_expr` | 入力した数式をパース・バイトコード化してRustエンジンへ転送。 | Mesh再計算 | 構文エラーがある場合はUI上にエラー箇所を表示。 |
| Math Preset | 選択 | Gyroid, Schwarz P, Neovius, Clebsch等の数学的プリセット数式を読込。 | Mesh再計算 | 複雑な周期曲面や多項式曲面をワンクリックで実験できる。 |

---

## 12. Layout (Instancing)

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|---|---|---|---|---|
| Mirror Mode | トグル/選択 `obj.sdf_mirror_mode` | ローカルまたはグローバル軸（X / Y / Z）に対するリアルタイムミラー複製。 | Mesh再計算 | 左右対称キャラクターやメカのモデリングに必須。メッシュポリゴンを増やさずSDF内で折り返す。 |
| Radial Array Count | 数値 `obj.sdf_radial_count` | 円周方向への回転配列コピー数。 | Mesh再計算 | ギア、スポーク、花弁などの放射状配置を生成。 |
| Linear Repeat | 数値 `obj.sdf_repeat_count` / `offset` | 直線方向への反復周期配置。 | Mesh再計算 | 格子、リブ、ルーバー形状を効率的に生成。 |

---

## 13. Deform (Stack)

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|---|---|---|---|---|
| Add Deform Modifier | メニュー `sdf.add_deform` | 選択プリミティブに変形オペレーターを追加（Elongate / Twist / Bend / Taper / Noise）。 | Mesh再計算 | 複数の変形をスタック順に重ねがけ可能。 |
| Twist Angle | 数値 | 軸に沿ったねじれ回転角度。 | Mesh再計算 | ドリル、ロープ、螺旋形状の作成。 |
| Bend Curvature | 数値 | 曲げ変形の曲率半径。 | Mesh再計算 | パイプの曲がり、角の湾曲など。 |
| Taper Factor | 数値 | 先端に向かう先細り比率。 | Mesh再計算 | 爪、角、コーン状への段階的変形。 |

---

## 14. Add New Primitives

| ボタン表示 | shape_type | 主な固有パラメータ | 再計算 | 形状の特徴・用途 |
|---|---|---|---|---|
| **Sphere** | `sphere` | Radius | Mesh再計算 | 完全な球体。基本形状。 |
| **Box** | `box` | Size X, Y, Z, Fillet | Mesh再計算 | 直方体。エッジ丸め・フィレット対応。 |
| **Cylinder** | `cylinder` | Radius, Height, Fillet | Mesh再計算 | 円柱。上下端のフィレット対応。 |
| **Torus** | `torus` | Main Radius, Pipe Radius | Mesh再計算 | ドーナツ形状。リング・パイプ用。 |
| **Capsule** | `capsule` | Radius, Height | Mesh再計算 | 丸薬形状。骨格や手足のベース。 |
| **Cone** | `cone` | Radius, Height | Mesh再計算 | 円錐。先端が尖ったパーツ。 |
| **Capped Cone** | `capped_cone` | Bottom Radius, Top Radius, Height | Mesh再計算 | 上面が平坦な円錐台。テーパー軸。 |
| **Rounded Box** | `rounded_box` | Size, Roundness | Mesh再計算 | 全体がなめらかに丸まった直方体。 |
| **Hex Prism** | `hex_prism` | Radius, Height, Fillet | Mesh再計算 | 正六角柱。ボルト頭やハニカム構造。 |
| **Octahedron** | `octahedron` | Size, Fillet | Mesh再計算 | 正八面体。結晶や宝石形状。 |
| **Pyramid** | `pyramid` | Base Size, Height, Fillet | Mesh再計算 | 四角錐。ピラミッド形状。 |
| **Ellipsoid** | `ellipsoid` | Radius X, Y, Z | Mesh再計算 | 3軸楕円体。オーガニック形状の素体。 |
| **Rounded Cylinder** | `rounded_cylinder` | Radius, Edge Radius, Height | Mesh再計算 | 端面が丸い円柱。 |
| **Capped Torus** | `capped_torus` | Main Radius, Pipe Radius, Arc Angle | Mesh再計算 | 円弧状に切り取られたトーラス（ハンドル等）。 |
| **Cut Sphere** | `cut_sphere` | Radius, Cut Height | Mesh再計算 | 平らに切り落とされた半球・カット球。 |
| **N-gon Prism** | `ngon_prism` | Radius, Height, Sides, Fillet | Mesh再計算 | 任意の多角柱（3角形〜12角形等）。 |
| **Math Field** | `math_field` | Math Expression | Mesh再計算 | 数式入力によるプロシージャル陰関数曲面。 |

---

## 15. Object Utilities / Cleanup

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|---|---|---|---|---|
| Move to SDF Collection | ボタン `sdf.move_to_sdf_collection` | 選択したBlenderオブジェクトを現在のアクティブSDFツリーのコレクションへ移動。 | Mesh再計算 | 外部からインポートしたオブジェクトをSDFツリーへ組み込む。 |
| Sync Curve to SDF | ボタン `sdf.sync_curve` | Blenderのベジェカーブ/パスの制御点からSDFパイプ・カプセル列を自動生成・同期。 | Mesh再計算 | ケーブル、パイピング、触手などのカーブベースモデリング用。 |
| Purge Orphan SDF Data | ボタン `sdf.purge_orphans` | 削除されたプリミティブの残骸や不要なSDFカスタムプロパティをクリーンアップ。 | 表示/管理 | ファイルサイズの軽量化とエラー予防。 |
| Reload Native DLL | ボタン `sdf.reload_dll` | バックエンドのRustネイティブバイナリ（DLL / dylib / so）を再ロード。 | 表示/管理 | クラッシュ復旧や開発中の動作確認用。 |

---

## 16. Operator ID 一覧

| Operator ID | UI表示ラベル | 概要・役割 | 最新版補足 |
|---|---|---|---|
| `sdf.init_scene` | Initialize SDF System | 初期SDFコレクションと結果メッシュの生成 | シーン初期化 |
| `sdf.add_primitive` | Add SDF Primitive | プリミティブをツリーへ追加 | Undo完全対応 |
| `sdf.add_tree` | Add SDF Tree | 新しい独立SDFツリーを追加 | マルチツリー |
| `sdf.delete_tree` | Delete SDF Tree | アクティブツリーを削除 | マルチツリー |
| `sdf.set_active_tree` | Set Active SDF Tree | 編集ツリーを切り替え | 自動切替連動 |
| `sdf.add_tree_ref` | Add Tree Reference | 別ツリーの参照Emptyを追加 | インスタンス合成 |
| `sdf.stack_move` | Move Stack Item | スタック内での順序を上下移動 | 評価順変更 |
| `sdf.add_collection_divider` | Add Collection Divider | グループ境界Dividerを追加 | 局所ブレンド |
| `sdf.remove_stack_item` | Remove Stack Item | スタック項目およびオブジェクトを削除 | クリーン連動 |
| `sdf.bake_mesh` | Snapshot Mesh | 静的メッシュコピーの作成 | **V17.0.1: マテリアル独立複製** |
| `sdf.finalize` | Finalize (Bake All) | SDF結果のメッシュ確定と履歴退避 | **V17.0.1: マテリアル独立複製** |
| `sdf.update_normals` | Fix Normals | 高品質法線の再計算適用 | 法線最適化 |
| `sdf.generate_mesh` | Force Update | SDF結果メッシュの手動強制生成 | Live OFF時反映 |
| `sdf.setup_material` | Setup Material | 標準PBRシェーダーノードの構築 | 頂点カラー連携 |
| `sdf.reset_material` | Reset Shader Nodes | シェーダーノードの標準状態リセット | クリーン化 |
| `sdf.apply_color_all` | Apply Color To All | 全体色の一括適用 | 軽量更新 |
| `sdf.apply_material_all` | Apply Material To All | Metallic / Roughnessの一括適用 | 軽量更新 |
| `sdf.gizmo_set_operation` | Set Operation (Gizmo) | ビューポート上のボタングリッドから演算切替 | **V17.0.0新規** |
| `sdf.gizmo_set_edge_profile` | Set Edge Profile (Gizmo) | ビューポート上のボタンからプロファイル切替 | **V17.0.0新規** |
| `sdf.compile_math_expr` | Compile Math Expression | 数式SDFのコンパイルとエンジン転送 | Math Field |
| `sdf.add_deform` | Add Deform Modifier | Elongate / Twist / Bend 等の変形追加 | Deform Stack |
| `sdf.move_to_sdf_collection` | Move to SDF Collection | オブジェクトをSDFコレクションへ編入 | 編入機能 |
| `sdf.sync_curve` | Sync Curve to SDF | BlenderカーブからのSDFパイプ生成 | カーブ同期 |
| `sdf.purge_orphans` | Purge Orphan SDF Data | 孤立プロパティと不要データのパージ | クリーンアップ |
| `sdf.reload_dll` | Reload Native DLL | Rustネイティブバイナリの再読み込み | 開発・デバッグ |
| `sdf.benchmark` | Run GPU Benchmark | GPUメッシュ生成のベンチマーク計測 | 性能診断 |
