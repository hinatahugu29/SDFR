# SDF.R V17.0.1 総合ユーザーマニュアル・完全リファレンスガイド（決定版）

対象バージョン: **Rust-GPU-SDF / SDF.R V17.0.1** | 基準ベース: V17.0.0 / V16.2.2 | 作成日: 2026-10-25  
用途: インストール・基本操作・実践ワークフロー（全9パターン）・UI完全棚卸し・トラブルシューティングを1本に統合した総合リファレンスマニュアル

---

## 本書について

本書は、Blender向け次世代GPU SDFモデリングアドオン **「SDF.R（Rust-GPU-SDF）」バージョン 17.0.1** の総合マニュアルです。  
アドオンの導入・環境設定から、V17.0.0で新設された「3Dビューポート・ギズモ」を駆使した直感モデリング、実践的な制作パターン（基礎4種＋応用5種）、UI全コントロールの完全台帳、そして制作現場でつまずきやすい落とし穴のトラブルシューティングまでを1冊に網羅しています。

---

## 目次

- [第1部: 導入とスタートアップ](#第1部-導入とスタートアップ)
  - [1.1 対応環境とOS別動作要件](#11-対応環境とos別動作要件)
  - [1.2 インストール手順とmacOS Gatekeeper解除](#12-インストール手順とmacos-gatekeeper解除)
  - [1.3 初回起動とウォームアップ（Shaderコンパイル）](#13-初回起動とウォームアップshaderコンパイル)
  - [1.4 アップデートとキャッシュ管理](#14-アップデートとキャッシュ管理)
- [第2部: SDF.Rの基本概念と操作体系](#第2部-sdfrの基本概念と操作体系)
  - [2.1 SDFモデリングの基本原則](#21-sdfモデリングの基本原則)
  - [2.2 操作体系の役割分担（ギズモ vs パネル）](#22-操作体系の役割分担ギズモ-vs-パネル)
  - [2.3 3Dビューポート・ギズモ完全ガイド](#23-3dビューポートギズモ完全ガイド)
  - [2.4 再計算区分の定義](#24-再計算区分の定義)
- [第3部: 実践ワークフロー・作業手順書（全9パターン）](#第3部-実践ワークフロー作業手順書全9パターン)
  - [【基礎編】](#基礎編)
    - [パターン1: 【超速入門】ギズモ直感モデリング（結合・穴あけ・フィレット）](#パターン1-超速入門ギズモ直感モデリング結合穴あけフィレット)
    - [パターン2: 【有機体・クリーチャー造形】スムーズブレンドと混色](#パターン2-有機体クリーチャー造形スムーズブレンドと混色)
    - [パターン3: 【ハードサーフェス・メカ部品】面取りと中空シェル](#パターン3-ハードサーフェスメカ部品面取りと中空シェル)
    - [パターン4: 【対称・幾何学レイアウト】ミラー対称とラジアル配列](#パターン4-対称幾何学レイアウトミラー対称とラジアル配列)
  - [【応用編】](#応用編)
    - [パターン5: 【マルチツリー＆ツリー参照】部品の独立管理とアセンブリ](#パターン5-マルチツリーツリー参照部品の独立管理とアセンブリ)
    - [パターン6: 【Collection Divider】局所ブーリアン階層制御](#パターン6-collection-divider局所ブーリアン階層制御)
    - [パターン7: 【Math Field幾何学装飾】多孔質パターンのくり抜き](#パターン7-math-field幾何学装飾多孔質パターンのくり抜き)
    - [パターン8: 【Deform Stack変形】プロシージャルなねじれ・曲げ・先細り](#パターン8-deform-stack変形プロシージャルなねじれ曲げ先細り)
    - [パターン9: 【イテレーション＆確定】Snapshotマテリアル分離とFinalize](#パターン9-イテレーション確定snapshotマテリアル分離とfinalize)
  - [制作フェーズ別クイックチェックリスト](#制作フェーズ別クイックチェックリスト)
- [第4部: UI & コマンド完全棚卸しリファレンス](#第4部-ui--コマンド完全棚卸しリファレンス)
  - [4.0 Tree（マルチツリー管理）](#40-treeマルチツリー管理)
  - [4.1 Header / Status](#41-header--status)
  - [4.2 Engine Diagnostics](#42-engine-diagnostics)
  - [4.3 Output & Quality](#43-output--quality)
  - [4.4 Post-Process (Smoothing)](#44-post-process-smoothing)
  - [4.5 The Stack](#45-the-stack)
  - [4.6 Material](#46-material)
  - [4.7 Finalize / Output](#47-finalize--output)
  - [4.8 Group Settings: Collection Divider](#48-group-settings-collection-divider)
  - [4.9 Tree Reference（ツリー参照）](#49-tree-referenceツリー参照)
  - [4.10 Primitive Settings](#410-primitive-settings)
  - [4.11 Viewport Gizmos（一覧）](#411-viewport-gizmos一覧)
  - [4.12 Math Field 専用コマンド](#412-math-field-専用コマンド)
  - [4.13 Layout (Instancing)](#413-layout-instancing)
  - [4.14 Deform (Stack)](#414-deform-stack)
  - [4.15 Add New Primitives（全17形状）](#415-add-new-primitives全17形状)
  - [4.16 Object Utilities / Cleanup](#416-object-utilities--cleanup)
  - [4.17 Operator ID 一覧](#417-operator-id-一覧)
- [第5部: 作業上の注意点・既知の問題・逆引きFAQ](#第5部-作業上の注意点既知の問題逆引きfaq)
  - [5.1 作業中に遭遇しやすい落とし穴（SDF特有の挙動）](#51-作業中に遭遇しやすい落とし穴sdf特有の挙動)
  - [5.2 V17.0.0 / V17.0.1 特有の既知の問題と制限事項](#52-v1700--v1701-特有の既知の問題と制限事項)
  - [5.3 トラブルシューティング Q&A（逆引きFAQ）](#53-トラブルシューティング-qa逆引きfaq)

---

# 第1部: 導入とスタートアップ

## 1.1 対応環境とOS別動作要件

### 対応Blenderバージョン
- **推奨:** Blender 4.2 LTS / 4.3 / 5.x 系（Windows / macOS / Linux）
- **下限:** Blender 3.6 LTS 以上（Python 3.10〜3.13環境対応）

### OS別動作要件

| OS | アーキテクチャ | 配布形態 | 必須要件・特有の注意点 |
|---|---|---|---|
| **Windows** | x86_64 | **標準パッケージ** | ・Vulkan 1.2+ または DirectX 12 対応GPU<br>・最新ディスプレイドライバ<br>・Visual C++ 再頒布可能パッケージ |
| **macOS** | Apple Silicon (arm64) | テストビルド | ・**Apple Silicon（M1/M2/M3/M4等）専用**（Intel Mac非対応）<br>・Metalバックエンド<br>・**Gatekeeperセキュリティ警告の解除が必要** |
| **Linux** | x86_64 | テストビルド | ・glibc 2.31 以上<br>・Vulkan対応ドライバ（mesa-vulkan-drivers / NVIDIA）<br>・WSL2（Windows Subsystem for Linux）での動作検証済み |

---

## 1.2 インストール手順とmacOS Gatekeeper解除

### インストール手順
1. 配布パッケージZIPファイル（例: `SDF_R_V17_0_1.zip` 等）を用意します（ZIPを展開・解凍しないでください）。
2. Blenderを起動し、メニューの `編集 (Edit)` > `プリファレンス (Preferences)` を開きます。
3. `アドオン (Add-ons)` タブを選択し、右上の `インストール... (Install...)` ボタンをクリックします。
4. ZIPファイルを選択してインストールします。
5. リストに表示された `SDF.R`（または `Rust-GPU-SDF`）にチェックを入れて有効化します。
6. 3Dビューポートで `N` キーを押し、サイドバーの `SDF.R` タブが表示されることを確認します。

### ⚠️ macOSでのGatekeeperブロック解除手順
macOS版のネイティブバイナリ（`librust_gpu_sdf.dylib`）は未署名のため、初回有効化時に「開発元を検証できないため開けません」という警告が出ることがあります。
1. 警告が出たら一度「キャンセル」をクリックします。
2. macOSの「システム設定」>「プライバシーとセキュリティ」を開きます。
3. 画面下部に「`librust_gpu_sdf.dylib` は開発元を確認できないため使用がブロックされました」と表示されている箇所の **「このまま開く」** をクリックします。
4. Blenderに戻り、再度アドオンのチェックボックスをONにすると正常に有効化されます。

---

## 1.3 初回起動とウォームアップ（Shaderコンパイル）

### ⚠️ 初回起動時の「見かけ上のフリーズ」について
アドオンを有効化し、最初に `Initialize SDF System` を実行した直後、またはキャッシュクリア直後は、**GPUシェーダー（WGSL）のコンパイルとコンピュートパイプラインの構築**がバックグラウンドで実行されます。

この間、**Blenderが一見フリーズ・応答停止したように見えますが、内部で正常に処理が進んでいます。絶対にBlenderを強制終了しないでください。**

#### 所要時間の目安
- **ディスクリートGPU（NVIDIA GeForce RTX, AMD Radeon 等）:**  
  👉 **15秒 〜 45秒程度** で完了します。
- **内蔵GPU（Intel Iris Xe, UHD Graphics, AMD Radeon 680M/780M 等）:**  
  👉 **2分 〜 3分以上（実測194秒など）** かかる場合があります。

> **コンソールでの進行確認:**  
> Blenderメニュー `ウィンドウ (Window)` > `システムコンソール切り替え (Toggle System Console)`（Windows）を開いておくと、
> ```text
> Compiling MC Pipeline...
> Compiling Dual Contouring Pipeline...
> GPU Engine Ready!
> ```
> とログが表示され、完了と同時に画面にメッシュが現れます。

---

## 1.4 アップデートとキャッシュ管理

過去バージョンから更新した場合や、PCのGPUドライバを更新した直後、`Initializing...` から進まなくなったり、クラッシュすることがあります。その場合はシェーダーキャッシュを手動で削除してください。

### キャッシュファイルの保存場所
- **Windows:** `%APPDATA%\Blender Foundation\Blender\<バージョン>\datafiles\rust_gpu_sdf\shader_cache.bin`
- **macOS:** `~/Library/Application Support/Blender/<バージョン>/datafiles/rust_gpu_sdf/shader_cache.bin`
- **Linux:** `~/.config/blender/<バージョン>/datafiles/rust_gpu_sdf/shader_cache.bin`

※ キャッシュファイルを削除しても、次回Blender起動時に自動的に最新のキャッシュが再生成されます。

---

# 第2部: SDF.Rの基本概念と操作体系

## 2.1 SDFモデリングの基本原則

SDF.R（Signed Distance Field Renderer）は、ポリゴンの頂点や面を直接引っ張る従来の手法とは異なり、**「空間の各点における形状表面からの距離（SDF）」** をGPU上で超高速に計算し、メッシュ化する技術です。

```
[プリミティブ配置] ───> [ブーリアン演算 (足す/引く/交差)] ───> [スムーズブレンド (溶かす)] ───> [GPUリアルタイムメッシュ化]
```

- **Union（和）:** 形状同士を合体させます。
- **Subtract（差）:** 形状で削り取り、穴やスリットを開けます。
- **Intersect（積）:** 重なり合っている体積だけを残します。
- **Smooth Blend:** 境界線を柔らかくフィレット・フィードバックさせ、粘土や溶接のように滑らかに一体化させます。

---

## 2.2 操作体系の役割分担（ギズモ vs パネル）

V17.0.0で「3Dビューポート・ギズモ」が搭載されたことにより、SDF.Rのモデリングは劇的にスピードアップしました。

- **3Dビューポート・ギズモ（直感モデリング）:**  
  選択したプリミティブの周囲に出現するカラー矢印やボタンスイッチを使い、**画面上で直接ドラッグ＆クリック**して寸法・角丸・肉厚・スムーズ・演算・プロファイルを即座に変更します。
- **サイドパネル（全体・詳細管理）:**  
  階層順序（The Stack）、解像度・ボクセル密度（Output & Quality）、事後スムージング、マルチツリー管理、マテリアル全体適用などを操作します。

---

## 2.3 3Dビューポート・ギズモ完全ガイド

### ① 共通ギズモ（全プリミティブまたは全ソリッド共通）

| ギズモ表示 | 操作方式 | 対応パラメータ | 対象シェイプ | 詳細挙動・役割 |
|---|---|---|---|---|
| **Fillet / Edge Size** (橙矢印) | オレンジ矢印ドラッグ | `sdf_edge_profile_size` | 角を持つ10種（Box, Cylinder, Hex Prism, Pyramid等） | 角の丸め・面取り幅を直感調整。角のない球やトーラスでは非表示。 |
| **Shell Thickness** (青緑矢印) | シアン矢印ドラッグ | `sdf_shell_thickness` | 全ソリッドプリミティブ | 中空シェルの肉厚を内側方向へドラッグ調整。 |
| **Smoothness** (赤紫矢印) | マゼンタ矢印ドラッグ | `sdf_smoothness` | 全プリミティブ | 他パーツとのブレンド結合半径を調整。 |
| **Operation Switch** | 3つのボタンクリック | `sdf_operation` | 全プリミティブ | **Union / Subtract / Intersect** を切替。アクティブな演算を強調表示。 |
| **Edge Profile Switch** | 5つのボタンクリック | `sdf_blend_profile` | フィレット対応シェイプ | **Round / Sharp / Soft / Tight / Chamfer** を2行配置でワンクリック切替。 |

### ② シェイプ固有の矢印ギズモ（主要10種）

| 形状タイプ | ギズモ矢印（色・軸） | 対応パラメータ | 詳細挙動 |
|---|---|---|---|
| **Torus** | 矢印2本 | Main Radius / Pipe Radius | ドーナツの主半径とチューブ太さを個別ドラッグ。 |
| **Cylinder** | 矢印2本 | Radius / Height | 円柱の底面半径と高さをドラッグ調整。 |
| **Capped Cone** | 矢印3本 | Bottom / Top Radius / Height | 円錐台の底面・上面半径と全高を変形。 |
| **Ellipsoid** | 赤・緑・青の3軸矢印 | Radius X / Radius Y / Radius Z | 楕円体をローカルXYZ軸矢印で個別ストレッチ。 |
| **Rounded Cylinder** | 矢印3本 | Radius / Edge Radius / Height | 円柱の半径、上下角の丸み、全高を調整。 |
| **Pyramid** | 矢印2本 | Base Size / Height | 四角錐の底面サイズと高さを調整。 |
| **Hex Prism** | 矢印2本 | Radius / Height | 正六角柱の半径と高さをドラッグ調整。 |
| **Rounded Box** | 矢印1本 | Roundness | 角丸立方体の全体的な丸み係数を調整。 |
| **Octahedron** | 矢印1本 | Size | 正八面体の全体寸法をスケール調整。 |
| **Cut Sphere** | 矢印1本 | Cut Height | 球を水平に切り落とす高さをドラッグ。 |

---

## 2.4 再計算区分の定義

本書およびUI台帳では、各操作の負荷と挙動を以下の3つに区分しています。

- **Mesh再計算:** SDF評価を行い、GPU上で結果メッシュを再生成する操作（形状変更、ブーリアン、個別カラー変更など）。
- **軽量更新:** メッシュ自体は作り直さず、マテリアル属性や表示モードのみを更新する軽量操作（全体カラー一括適用、ワイヤーフレーム表示など）。
- **表示/管理:** UI上の選択切り替え、階層操作、ツリー管理などの非描画操作。

---

# 第3部: 実践ワークフロー・作業手順書（全9パターン）

## 【基礎編】

### パターン1: 【超速入門】ギズモ直感モデリング（結合・穴あけ・フィレット）
> **想定成果物:** 角が丸められ、滑らかな貫通穴が開いた機械的ブロックパーツ。

```
[初期Box] ──(橙矢印ドラッグ)──> [角丸Box] ──(Cylinder重ね+減算ボタン)──> [穴あきブロック] ──(紫矢印ドラッグ)──> [なめらかな穴の完成]
```

1. **初期化:** Nパネル `SDF.R` で `Initialize SDF System` をクリック。
2. **Box配置:** `Add New Primitives` から `Box` を追加（不要な初期球は削除）。
3. **フィレット調整:** Box周囲の **オレンジ色の矢印ギズモ** を外側へドラッグし、角を丸める。
4. **穴あけ:** `Cylinder` を追加し、`G` キーでBox中央を貫通配置。ビューポート上のOperationボタンから **`Subtract`** をクリック。
5. **穴のブレンド:** Cylinder周囲の **マゼンタ色矢印ギズモ（Smoothness）** をドラッグし、穴の縁を滑らかになじませる。

---

### パターン2: 【有機体・クリーチャー造形】スムーズブレンドと混色
> **想定成果物:** 複数パーツが有機的に融着し、グラデーション混色を持つクリーチャーヘッド素体。

1. **中心核配置:** `Sphere` を追加して頭部の核とする。
2. **引き伸ばしパーツ追加:** `Ellipsoid` を追加し、**赤・緑・青の3軸矢印ギズモ** をドラッグして顎や後頭部状に引き伸ばす。`Capsule` で首を追加。
3. **有機的融着:** 全パーツを `Union` のまま、**マゼンタ矢印ギズモ（Smoothness）** を大きく（`0.4` 〜 `0.8`）ドラッグして境界線を完全に溶かし込む。
4. **部位別カラー混色:** `Primitive Settings` > `Color` で頭部をブルー、突起部をオレンジ等に設定。GPUがブレンド幅に応じて美しいグラデーション混色を自動生成。
5. **仕上げ一括適用:** `Material` > `Apply Material To All` でMetallic/Roughnessを統一。

---

### パターン3: 【ハードサーフェス・メカ部品】面取りと中空シェル
> **想定成果物:** 外側が面取りされ、内部が均一肉厚で中空化されたメカニカルカバー。

1. **外装配置:** `Hex Prism`（六角柱）を追加。
2. **面取り切替:** ビューポート上のEdge Profileボタンから **`Chamfer`** をクリック。オレンジ矢印をドラッグすると直線的な45度面取りになる。
3. **中空シェル化:** **シアン色の矢印ギズモ（Shell Thickness）** を内側へドラッグし、薄肉中空ケース化する。
4. **ネジ受けボス配置:** `Cylinder` を底面内側に立て（`Union`）、Smoothnessを極小（`0.05`）にしてケース内壁とわずかに鋳造接合する。
5. **スリット開孔:** 薄い `Box` を側面に重ね、Operationを `Subtract` にして通気口を開ける。

---

### パターン4: 【対称・幾何学レイアウト】ミラー対称とラジアル配列
> **想定成果物:** 左右対称のビークルボディと、放射状に等間隔配置されたホイールスポーク。

1. **左右対称（Mirror Mode）:** パーツをX軸プラス側に配置し、`Layout (Instancing)` で `Mirror Mode` を **`X`** に設定。反対側にリアルタイム追従する対称形状が出現。
2. **円周配置（Radial Array）:** 中心軸にCylinderを置き、スポーク用の細長いBoxを配置。Boxの `Radial Array Count` を **`6`** に設定すると、60度間隔で放射状に展開される。
3. **連動変形:** 親Boxをスケール・回転すると、6本すべてがリアルタイムに連動。

---

## 【応用編】

### パターン5: 【マルチツリー＆ツリー参照】部品の独立管理とアセンブリ
> **想定成果物:** ボディ、タイヤ、関節が独立メッシュとして共存し、干渉部が溶け合わない高精度メカ。

```
[Tree 0: Body (車体)] 
         ▲
         └── [Tree Reference Empty] ──(参照)──> [Tree 1: Tire (独立タイヤ)]
```

1. **メイン車体制作:** 初期ツリー（`Tree_0`）で車体をモデリング。
2. **タイヤツリー作成:** パネル最上部の **`＋`（Add Tree）** を押し、独立ツリー `Tree_1` を作成してタイヤを作り込む。
3. **ツリー参照配置:** `Tree_0` に戻り、`8-B. Tree Reference` の **`Add Tree Reference`** をクリック。プロパティで `Tree_1` を選択。
4. **Transform複製:** 作成された参照Emptyを前輪位置へ移動し、`Shift + D` で後輪へ複製配置。
5. **独立性の利点:** 通常のSDFでは近接すると勝手に溶けてしまうが、別ツリーのため**境界が溶け合わずシャープな隙間を保って共存**する。

---

### パターン6: 【Collection Divider】局所ブーリアン階層制御
> **想定成果物:** 胴体に干渉せず、腕パーツの内部だけでくり抜きやブレンドが完結する階層モデリング。

1. **Divider挿入:** 腕パーツ群を作成する直前の位置で、`The Stack` の **`＋`（Add Collection Divider）** をクリック。名前を `Arm_Group` に変更。
2. **グループ内構築:** 腕用パーツを追加し、スタック上でDividerの下に配置。この内部で行う `Subtract` や大きな `Smoothness` は **Dividerの内側だけで評価** される。
3. **全体結合:** Divider自体の `Operation`（`Union`）と `Smoothness` を設定し、完成した腕グループを胴体へ一体化結合する。

---

### パターン7: 【Math Field幾何学装飾】多孔質パターンのくり抜き
> **想定成果物:** 外殻の一部がジャイロイド格子（多孔質ラティス）で軽量化・装飾されたSF風パーツ。

1. **ベース配置:** ベースとなる `Box` または `Sphere` を配置。
2. **Math Field追加:** `Add New Primitives` から `Math Field` を追加し、`Math Preset` から **`Gyroid`** を選択して `Compile Math Expression` をクリック。
3. **交差演算（Intersect）:** Math FieldのOperationを **`Intersect`** に切り替えると、ベース形状の体積内部だけに波状多孔質構造が生成される。
4. **外枠結合:** 同サイズのBoxを中空シェル化して `Union` で重ね、「外周はソリッドフレーム、内部はジャイロイド格子」の3Dプリント高機能パーツを完成させる。

---

### パターン8: 【Deform Stack変形】プロシージャルなねじれ・曲げ・先細り
> **想定成果物:** 螺旋状にねじれながら先端に向かって鋭利に先細るクリーチャーのツノ／ドリル。

1. **原型配置:** `Cylinder` または `Hex Prism` を追加。
2. **Deform 1 (Taper):** `13. Deform (Stack)` から `Taper` を追加し、先端に向かって鋭角に細くする。
3. **Deform 2 (Twist):** 続いて `Twist` を追加し、軸に沿ってドリル状に激しくねじ曲げる。
4. **Deform 3 (Bend):** さらに `Bend` を追加し、全体を三日月状に大きく湾曲させる。
5. **非破壊性の確認:** スタックとして保持されているため、後から元の半径やねじれ角だけをいつでも微調整可能。

---

### パターン9: 【イテレーション＆確定】Snapshotマテリアル分離とFinalize
> **想定成果物:** 互いに干渉しないカラーバリエーション保存モデルと、クリーンな確定メッシュ。

1. **案A制作とSnapshot保存:** ライブツリーで形状を作り、マテリアル色をレッドにする。`7. Finalize / Output` の **`Snapshot Mesh`** をクリックして静的メッシュを生成。
2. **★V17.0.1 の安全仕様（案B作成）:** ライブツリーに戻り、マテリアル色をブルーに変えて案Bを作る。**V17.0.1ではマテリアルが独立複製されるため、案Aは赤い色のまま完全に保持される。**
3. **法線仕上げ:** 最終案決定後、**`Fix Normals`** を押してSDF数学的勾配による最高品質の法線を頂点にベイク。
4. **確定（Finalize）:** **`Finalize (Bake All)`** をクリック。結果メッシュがBlender標準メッシュとして確定され、元プリミティブ群は自動的に非表示の履歴コレクションへ退避される。

---

## 制作フェーズ別クイックチェックリスト

| フェーズ | チェック項目 | 推奨アクション |
|---|---|---|
| **造形初期** | 画面が重く感じないか？ | `Output & Quality` の Preset を `Low` または `Medium` にしておく。 |
| **形状結合時** | 接合部が不自然に溶けすぎていないか？ | マゼンタ矢印ギズモで `Smoothness` を絞るか、`Collection Divider` を挟む。 |
| **ハードサーフェス時** | 角が丸まりすぎて機械感が出ていないか？ | ビューポート上のボタンで `Edge Profile` を `Chamfer` または `Tight` に切り替える。 |
| **パーツ近接時** | 別パーツとして並べたいのに溶け合ってしまう | `Add SDF Tree` で別ツリーにし、`Tree Reference` で配置する。 |
| **確定前** | シェーディングに違和感がないか？ | `Fix Normals` を実行し、法線ベクトルを最高品質に更新する。 |
| **試作保存時** | 過去の試作案の色が巻き込まれて変化しないか？ | **V17.0.1対応済み**。安心して `Snapshot Mesh` を活用可能。 |

---

# 第4部: UI & コマンド完全棚卸しリファレンス

## 4.0 Tree（マルチツリー管理）

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|---|---|---|---|---|
| Tree | ドロップダウン `sdf_scene_props.active_tree_index` | 編集対象のSDFツリーを選ぶ。以下のパネル全体が選択ツリー専用の内容に切り替わる。 | 表示/管理 | ビューポートでパーツを選ぶだけでも自動切替。 |
| ＋（新規ツリー追加） | ボタン `sdf.add_tree` | 空の新規SDFツリー（コレクションと結果メッシュ）を作成しアクティブ化。 | 表示/管理 | 別パーツ・背景などを独立作成する際に使用。 |
| −（ツリー削除） | ボタン `sdf.delete_tree` | アクティブなツリーを削除する。 | 表示/管理 | ツリーが1つしかない場合は削除不可。 |
| Tree Name | テキスト `tree.name` | アクティブツリーの表示名・コレクション名を変更。 | 表示/管理 | 結果メッシュや参照Emptyの名前にも連動。 |

## 4.1 Header / Status

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|---|---|---|---|---|
| Initialize SDF System | ボタン `sdf.init_scene` | 初期SDFツリー（コレクション、Sphere、結果メッシュ）を作成して利用準備。 | Mesh再計算 | シーンにSDF環境がないときに大きく表示。 |
| GPU: Ready / Updating | ステータス表示 | GPUバックエンド（Rust / WGPU）の稼働状態を表示。 | 表示/管理 | 非同期更新中は Updating 表示。 |
| Live Update | トグル `props.live_update` | パラメータやTransform変更を結果メッシュへ自動反映するか制御。 | 表示/管理 | 重いシーンでは一時的にOFF推奨。 |
| Auto Wireframe | トグル `props.auto_wireframe` | プリミティブ選択時にワイヤーフレームを自動表示するか制御。 | 軽量更新 | 形状の配置や境界の確認に便利。 |
| Stats / Info | 情報ラベル | プリミティブ数、解像度、頂点数、GPU処理時間などを表示。 | 表示/管理 | ボトルネック特定に活用。 |

## 4.2 Engine Diagnostics

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|---|---|---|---|---|
| Run GPU Benchmark | ボタン `sdf.benchmark` | 現在のSDFツリーに対してGPUベンチマークを実行し平均処理時間を計測。 | Mesh再計算 | グリッド解像度等に応じた負荷テスト用。 |
| Backend Info | テキスト | 使用中のGPUアダプタ名、Backend API（Vulkan / Metal / DX12等）を表示。 | 表示/管理 | ネイティブDLLの読み込み確認用。 |
| Engine Log Level | 選択 `props.log_level` | コンソール出力のログ詳細度（Error / Warn / Info / Debug / Trace）を設定。 | 表示/管理 | トラブルシューティング時に使用。 |

## 4.3 Output & Quality

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|---|---|---|---|---|
| Resolution Preset | 選択 `props.resolution_preset` | 解像度プリセット（Low / Medium / High / Ultra / Custom）。 | Mesh再計算 | 作業中はMedium、最終確認時はHigh/Ultra推奨。 |
| Grid Resolution | 数値 `props.grid_resolution` | Customプリセット時のボクセル解像度（各軸の分割数）。 | Mesh再計算 | 上げると細部が精密になるがGPUメモリ消費増。 |
| Adaptive Mesh | トグル `props.use_adaptive` | 平坦部のポリゴンを間引き、曲面に密度を集中させる適応型メッシュを有効化。 | Mesh再計算 | ポリゴン数を抑えつつシャープなエッジを保持。 |
| Bounding Box Mode | 選択 `props.bbox_mode` | バウンディングボックスの計算方式（Auto / Manual / Tight）。 | Mesh再計算 | 通常はAuto推奨。端切れ時はManualかPadding調整。 |
| BBox Padding | 数値 `props.bbox_padding` | Auto BBox計算時の余白マージン倍率。 | Mesh再計算 | 変形やスムーズで広がる形状の端切れを防止。 |

## 4.4 Post-Process (Smoothing)

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|---|---|---|---|---|
| Enable Smoothing | トグル `props.enable_smoothing` | 生成メッシュに対する事後スムージング処理（Laplacian / Taubin）を有効化。 | Mesh再計算 | マーチングキューブ特有の微小段差を軽減。 |
| Smoothing Iterations | 数値 `props.smoothing_iterations` | スムージングの反復適用回数。 | Mesh再計算 | 回数を増やすと滑らかになるが角が丸まる。 |
| Smoothing Factor | 数値 `props.smoothing_factor` | 1ステップあたりのスムージング強度。 | Mesh再計算 | 微調整用。通常は0.2〜0.5程度。 |

## 4.5 The Stack

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|---|---|---|---|---|
| Stack UIList | リスト `tree.stack_items` | 現在のSDFツリーを構成するプリミティブおよびDividerの階層順一覧。 | 表示/管理 | 上から下へ順番にブーリアン評価される。 |
| ▲ / ▼（移動ボタン） | ボタン `sdf.stack_move` | 選択アイテムのスタック内実行順序を上下に移動。 | Mesh再計算 | 演算の適用順が変わるため形状が変化。 |
| ＋（Divider追加） | ボタン `sdf.add_collection_divider` | グループ境界となるCollection Dividerを追加。 | Mesh再計算 | サブツリーとしてカプセル化し局所ブレンド。 |
| −（アイテム削除） | ボタン `sdf.remove_stack_item` | 選択中のプリミティブまたはDividerをスタックから削除。 | Mesh再計算 | 3Dビューポート上のオブジェクトも連動削除。 |
| Active Item Indicator | ラジオ/選択 | ビューポート選択とStack選択を双方向同期。 | 表示/管理 | パラメータがPrimitive Settingsに即時反映。 |

## 4.6 Material

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|---|---|---|---|---|
| Setup Material | ボタン `sdf.setup_material` | 頂点カラー（Color Attribute）を反映する標準PBRシェーダーノードを構築。 | 軽量更新 | マテリアル作成・初期化用。 |
| Reset Shader Nodes | ボタン `sdf.reset_material` | シェーダーノードを初期のクリーンな状態に初期化。 | 軽量更新 | 独自ノード追加後に標準へ戻す際使用。 |
| Apply Color To All | ボタン `sdf.apply_color_all` | 指定した単一カラーをツリー内の全プリミティブへ一括適用。 | 軽量更新 | 全体一色化のため軽量更新で完了。 |
| Apply Material To All | ボタン `sdf.apply_material_all` | 指定したMetallic / Roughnessをツリー内の全プリミティブへ一括適用。 | 軽量更新 | 全体の質感を統一。 |
| Transmission Warning | 警告表示 | Transmissionはプリミティブ個別ではなくマテリアル全体値である旨の注記。 | 表示/管理 | 個別透過率分けは非対応。 |

## 4.7 Finalize / Output

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|---|---|---|---|---|
| Fix Normals | ボタン `sdf.update_normals` | SDF勾配から計算した高品質法線を結果メッシュに再計算適用。 | Mesh再計算 | レンダリング前の法線仕上げ確認用。 |
| Force Update | ボタン `sdf.generate_mesh` | Live Update OFF時などに、手動で結果メッシュを強制再計算。 | Mesh再計算 | 重い編集後の反映用。 |
| Snapshot Mesh | ボタン `sdf.bake_mesh` | 現在のSDF結果から静的なメッシュコピーを複製作成（Live環境は維持）。 | 表示/管理 | **V17.0.1改善:** メッシュと同時に**マテリアル自身も独立複製**されるため、Live変更の影響を受けない。 |
| Finalize (Bake All) | ボタン `sdf.finalize` | SDF結果を通常メッシュとして確定し、元プリミティブを履歴コレクションへ退避。 | Mesh再計算/確定 | **V17.0.1改善:** バックアップマテリアルが独立複製され、オブジェクト名が安全管理される。 |

## 4.8 Group Settings: Collection Divider

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|---|---|---|---|---|
| Name | テキスト `item.name_override` | Stack上のDivider表示名を変更。 | Mesh再計算 | グループの識別用（頭部、胴体、腕など）。 |
| Operation | 選択 `item.operation` | グループ全体をメインツリーへ結合するブーリアン演算。 | Mesh再計算 | グループ合成結果の全体に対する演算を指定。 |
| Blend Profile | 選択 `item.blend_profile` | グループ境界のブレンドスタイル（Round / Chamfer等）。 | Mesh再計算 | 接合部の丸み形状を決定。 |
| Smoothness | 数値 `item.smoothness` | グループ境界のブレンド半径。 | Mesh再計算 | グループ全体を滑らかに馴染ませる。 |

## 4.9 Tree Reference（ツリー参照）

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|---|---|---|---|---|
| Add Tree Reference | ボタン `sdf.add_tree_ref` | 別ツリーを取り込む参照Emptyをアクティブツリー内に作成。 | Mesh再計算 | 作成されたEmptyはTransform（移動・回転・拡縮）可能。 |
| Referenced Tree | ドロップダウン `obj.sdf_ref_tree` | 参照先となるSDFツリーを指定。 | Mesh再計算 | 共通パーツを複数箇所から再利用。 |
| Operation / Smoothness | 各設定 | 参照ツリーをメインツリーへ結合する際の演算とスムーズ量。 | Mesh再計算 | 通常プリミティブと同様に設定可能。 |

## 4.10 Primitive Settings

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|---|---|---|---|---|
| Shape | ドロップダウン `obj.sdf_shape_type` | 選択プリミティブの形状タイプを変更。 | Mesh再計算 | Transformを維持したまま別の幾何形状へ切替。 |
| Operation | ボタン切替 `obj.sdf_operation` | ブーリアン演算（Union / Subtract / Intersect）。 | Mesh再計算 | **ギズモ対応**: ビューポート上のボタンでも切替可能。 |
| Blend Profile | 選択 `obj.sdf_blend_profile` | エッジ丸み形状（Round / Sharp / Soft / Tight / Chamfer）。 | Mesh再計算 | **ギズモ対応**: ビューポート上のボタンでも切替可能。 |
| Chamfer Factor | 数値 `obj.sdf_chamfer_factor` | Blend ProfileがChamferの場合の面取り比率。 | Mesh再計算 | 機械的な面取り接合を作成。 |
| Smoothness | 数値 `obj.sdf_smoothness` | 隣接プリミティブとのブレンド半径。 | Mesh再計算 | **ギズモ対応**: マゼンタ矢印ドラッグで調整可能。 |
| Fillet / Edge Size | 数値 `obj.sdf_edge_profile_size` | プリミティブ固有の角丸め・フィレット幅。 | Mesh再計算 | **ギズモ対応**: オレンジ矢印ドラッグで調整可能。 |
| Shell Thickness | 数値 `obj.sdf_shell_thickness` | 中空（シェル）構造の肉厚。 | Mesh再計算 | **ギズモ対応**: シアン矢印ドラッグで調整可能。 |
| Shape Specific Parameters | 数値スライダー | 半径、高さ、内径、外径など形状ごとの固有寸法。 | Mesh再計算 | **ギズモ対応**: 主要10形状は専用矢印でドラッグ可能。 |
| Color | カラーピッカー `obj.sdf_color` | 個別プリミティブの表面カラー。 | Mesh再計算 | 重なり部分はブレンド幅に応じて混色される。 |
| Metallic / Roughness | 数値スライダー | 個別プリミティブの金属感および表面粗さ。 | Mesh再計算 | PBR頂点属性にベイク。 |

## 4.11 Viewport Gizmos（一覧）

### 共通ギズモ
- **Fillet / Edge Size (橙矢印):** 角丸・面取り幅をドラッグ調整（角を持つ10形状）。
- **Shell Thickness (青緑矢印):** 中空肉厚をドラッグ調整（全ソリッド）。
- **Smoothness (赤紫矢印):** ブレンド半径をドラッグ調整（全形状）。
- **Operation Switch (3ボタン):** Union / Subtract / Intersect をワンクリック切替。
- **Edge Profile Switch (5ボタン):** Round / Sharp / Soft / Tight / Chamfer をワンクリック切替。

### シェイプ固有矢印ギズモ（主要10種）
- **Torus:** Main Radius / Pipe Radius
- **Cylinder:** Radius / Height
- **Capped Cone:** Bottom Radius / Top Radius / Height
- **Ellipsoid:** Radius X / Y / Z（RGB 3軸カラー矢印）
- **Rounded Cylinder:** Radius / Edge Radius / Height
- **Pyramid:** Base Size / Height
- **Hex Prism:** Radius / Height
- **Rounded Box:** Roundness
- **Octahedron:** Size
- **Cut Sphere:** Cut Height

## 4.12 Math Field 専用コマンド

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|---|---|---|---|---|
| Expression | テキスト `obj.sdf_math_expr` | 数式SDFを記述するテキスト入力（例: `length(p) - 1.0`）。 | Mesh再計算 | GLSL風数式で陰関数曲面を生成。 |
| Compile Math Expression | ボタン `sdf.compile_math_expr` | 入力数式をバイトコード化してRustエンジンへ転送。 | Mesh再計算 | 構文エラー時はUI上にエラー箇所を表示。 |
| Math Preset | 選択 | Gyroid, Schwarz P, Neovius, Clebsch等のプリセット読込。 | Mesh再計算 | 複雑な周期曲面をワンクリック読込。 |

## 4.13 Layout (Instancing)

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|---|---|---|---|---|
| Mirror Mode | トグル/選択 `obj.sdf_mirror_mode` | 軸（X / Y / Z）に対するリアルタイムミラー複製。 | Mesh再計算 | メッシュを増やさずSDF座標で折り返す。 |
| Radial Array Count | 数値 `obj.sdf_radial_count` | 円周方向への回転配列コピー数。 | Mesh再計算 | ギア、スポーク等の放射状配置。 |
| Linear Repeat | 数値 `obj.sdf_repeat_count` / `offset` | 直線方向への反復周期配置。 | Mesh再計算 | 格子やルーバー形状の生成。 |

## 4.14 Deform (Stack)

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|---|---|---|---|---|
| Add Deform Modifier | メニュー `sdf.add_deform` | 変形モディファイア（Elongate / Twist / Bend / Taper / Noise）を追加。 | Mesh再計算 | 複数変形をスタック順に重ねがけ可能。 |
| Twist Angle | 数値 | 軸に沿ったねじれ回転角度。 | Mesh再計算 | ドリル、螺旋形状。 |
| Bend Curvature | 数値 | 曲げ変形の曲率半径。 | Mesh再計算 | パイプや角の湾曲。 |
| Taper Factor | 数値 | 先端に向かう先細り比率。 | Mesh再計算 | 爪やコーン状変形。 |

## 4.15 Add New Primitives（全17形状）

| 形状名 | shape_type | 主な固有パラメータ | 特徴・用途 |
|---|---|---|---|
| **Sphere** | `sphere` | Radius | 完全な球体。基本形状。 |
| **Box** | `box` | Size X, Y, Z, Fillet | 直方体。エッジ丸め・フィレット対応。 |
| **Cylinder** | `cylinder` | Radius, Height, Fillet | 円柱。上下端フィレット対応。 |
| **Torus** | `torus` | Main Radius, Pipe Radius | ドーナツ形状。リング・パイプ用。 |
| **Capsule** | `capsule` | Radius, Height | 丸薬形状。骨格や手足のベース。 |
| **Cone** | `cone` | Radius, Height | 円錐。先端が尖ったパーツ。 |
| **Capped Cone** | `capped_cone` | Bottom Radius, Top Radius, Height | 上面平坦な円錐台。テーパー軸。 |
| **Rounded Box** | `rounded_box` | Size, Roundness | 全体がなめらかに丸まった直方体。 |
| **Hex Prism** | `hex_prism` | Radius, Height, Fillet | 正六角柱。ボルト頭やハニカム構造。 |
| **Octahedron** | `octahedron` | Size, Fillet | 正八面体。結晶や宝石形状。 |
| **Pyramid** | `pyramid` | Base Size, Height, Fillet | 四角錐。ピラミッド形状。 |
| **Ellipsoid** | `ellipsoid` | Radius X, Y, Z | 3軸楕円体。オーガニック形状の素体。 |
| **Rounded Cylinder** | `rounded_cylinder` | Radius, Edge Radius, Height | 端面が丸い円柱。 |
| **Capped Torus** | `capped_torus` | Main Radius, Pipe Radius, Arc Angle | 円弧状に切り取られたトーラス（ハンドル等）。 |
| **Cut Sphere** | `cut_sphere` | Radius, Cut Height | 平らに切り落とされた半球・カット球。 |
| **N-gon Prism** | `ngon_prism` | Radius, Height, Sides, Fillet | 任意の多角柱（3角形〜12角形等）。 |
| **Math Field** | `math_field` | Math Expression | 数式入力によるプロシージャル陰関数曲面。 |

## 4.16 Object Utilities / Cleanup

| 表示名 | 種別 | 内容 | 再計算 | 補足 |
|---|---|---|---|---|
| Move to SDF Collection | ボタン `sdf.move_to_sdf_collection` | 選択オブジェクトをアクティブSDFコレクションへ移動。 | Mesh再計算 | 外部オブジェクトのツリー編入用。 |
| Sync Curve to SDF | ボタン `sdf.sync_curve` | ベジェカーブ制御点からSDFパイプ列を自動生成同期。 | Mesh再計算 | ケーブル、触手等のカーブモデリング用。 |
| Purge Orphan SDF Data | ボタン `sdf.purge_orphans` | 削除されたプリミティブの残骸や不要プロパティをパージ。 | 表示/管理 | ファイル軽量化とエラー予防。 |
| Reload Native DLL | ボタン `sdf.reload_dll` | バックエンドRustネイティブバイナリを再ロード。 | 表示/管理 | クラッシュ復旧や開発中の確認用。 |

## 4.17 Operator ID 一覧

| Operator ID | UI表示ラベル | 概要・役割 |
|---|---|---|
| `sdf.init_scene` | Initialize SDF System | 初期SDFコレクションと結果メッシュの生成 |
| `sdf.add_primitive` | Add SDF Primitive | プリミティブをツリーへ追加（Undo完全対応） |
| `sdf.add_tree` | Add SDF Tree | 新しい独立SDFツリーを追加（マルチツリー） |
| `sdf.delete_tree` | Delete SDF Tree | アクティブツリーを削除 |
| `sdf.set_active_tree` | Set Active SDF Tree | 編集ツリーを切り替え |
| `sdf.add_tree_ref` | Add Tree Reference | 別ツリーの参照Emptyを追加 |
| `sdf.stack_move` | Move Stack Item | スタック内での順序を上下移動 |
| `sdf.add_collection_divider` | Add Collection Divider | グループ境界Dividerを追加 |
| `sdf.remove_stack_item` | Remove Stack Item | スタック項目およびオブジェクトを削除 |
| `sdf.bake_mesh` | Snapshot Mesh | 静的メッシュコピーの作成（**V17.0.1: マテリアル独立複製**） |
| `sdf.finalize` | Finalize (Bake All) | SDF結果のメッシュ確定と履歴退避（**V17.0.1: マテリアル独立複製**） |
| `sdf.update_normals` | Fix Normals | 高品質法線の再計算適用 |
| `sdf.generate_mesh` | Force Update | SDF結果メッシュの手動強制生成 |
| `sdf.setup_material` | Setup Material | 標準PBRシェーダーノードの構築 |
| `sdf.reset_material` | Reset Shader Nodes | シェーダーノードの標準状態リセット |
| `sdf.apply_color_all` | Apply Color To All | 全体色の一括適用（軽量更新） |
| `sdf.apply_material_all` | Apply Material To All | Metallic / Roughnessの一括適用（軽量更新） |
| `sdf.gizmo_set_operation` | Set Operation (Gizmo) | ビューポート上のボタングリッドから演算切替（**V17.0.0新規**） |
| `sdf.gizmo_set_edge_profile` | Set Edge Profile (Gizmo) | ビューポート上のボタンからプロファイル切替（**V17.0.0新規**） |
| `sdf.compile_math_expr` | Compile Math Expression | 数式SDFのコンパイルとエンジン転送 |
| `sdf.add_deform` | Add Deform Modifier | 変形モディファイアの追加 |
| `sdf.move_to_sdf_collection` | Move to SDF Collection | オブジェクトをSDFコレクションへ編入 |
| `sdf.sync_curve` | Sync Curve to SDF | BlenderカーブからのSDFパイプ生成 |
| `sdf.purge_orphans` | Purge Orphan SDF Data | 孤立プロパティと不要データのパージ |
| `sdf.reload_dll` | Reload Native DLL | Rustネイティブバイナリの再読み込み |
| `sdf.benchmark` | Run GPU Benchmark | GPUメッシュ生成のベンチマーク計測 |

---

# 第5部: 作業上の注意点・既知の問題・逆引きFAQ

## 5.1 作業中に遭遇しやすい落とし穴（SDF特有の挙動）

### ① プリミティブの順序と「Subtractが効かない」問題
- **現象:** `Cylinder` を追加して `Subtract`（削り取り）にしたのに、穴が開かない。
- **原因:** SDF.Rのスタックは「上から下へ」評価されます。本体（`Union`）より上に `Subtract` を置いても削る相手が存在しません。
- **対策:** `The Stack` 上で、`Subtract` プリミティブを削りたい形状より **「下」** に移動（▼ボタン）させてください。

### ② 意図しないパーツまで削れてしまう「誤爆貫通」
- **現象:** 腕のパーツに開けた穴が、遠く離れた胴体まで突き抜けて削ってしまう。
- **原因:** 平坦なスタックでは、Subtractは自分より上にあるすべての形状に作用します。
- **対策:** `Collection Divider` でグループ化・カプセル化するか、腕を `別ツリー（Add Tree）` にして `Tree Reference` で合体させてください。

### ③ BBox（バウンディングボックス）の端切れ
- **現象:** 大きく引き伸ばした形状や、大きなSmoothnessで広がった部分の端が平らに切れてしまう。
- **原因:** SDFのGPU計算領域（Bounding Box）の外側に形状がはみ出しているためです。
- **対策:** `Output & Quality` の `BBox Padding`（余白倍率）を `1.2` 〜 `1.5` に引き上げるか、`Bounding Box Mode` を `Manual` にして手動拡大してください。

### ④ Radial Array（放射状配列）の端が欠ける
- **現象:** `Radial Array Count` を増やした際、回転角度を大きくすると端が削ぎ落とされる。
- **原因:** 空間を角度スライス（`360° / Count`）に折りたたんで計算するため、パーツがスライスの角度幅をはみ出すとクリッピングされます。
- **対策:** パーツの回転量を抑えるか、`Count` を適切に調整してください。

### ⑤ プレビューの負荷とFPS低下
- **対策:** 造形中は解像度を `Low` または `Medium` に設定し、大量に変形・移動を行う際は一時的に **`Live Update` を OFF** にして作業してください。

---

## 5.2 V17.0.0 / V17.0.1 特有の既知の問題と制限事項

- **ギズモ未対応（パネル専用）のパラメータ:**  
  Capped Torus の Arc Angle（回転角度）、N-gon Prism の辺数（整数ステップ）、Deform Stack（変形モディファイア）、個別ブール関係値はギズモ未対応です。サイドパネルから設定してください。
- **ギズモ矢印の挙動（Smoothness）:**  
  他のプリミティブと接触していない単体パーツでは、Smoothness矢印を動かしても外観変化が現れません（交差した瞬間に反映されます）。
- **旧ファイルのマテリアル互換性（V17.0.1）:**  
  V17.0.0以前に作成・保存されたファイル内の既存Snapshotメッシュは旧仕様（共有マテリアル）のままです。最新仕様（独立マテリアル）にするにはV17.0.1上で再度 `Snapshot Mesh` を実行してください。

---

## 5.3 トラブルシューティング Q&A（逆引きFAQ）

### Q1. アドオン有効化時にエラー（ImportError / DLL load failed）が出る
- **Windows:** Visual C++ 再頒布可能パッケージを更新し、GPUディスプレイドライバを最新化してください。
- **macOS:** Apple Silicon Mac専用です。「第1部 1.2」の手順でGatekeeperのブロックを解除してください。
- **Linux:** glibc 2.31以上か、およびVulkanドライバが正常動作しているか確認してください。

### Q2. 画面が真っ暗のまま進まない、または `GPU: Updating` のまま止まる
- 初回起動またはキャッシュ削除直後の **Shader Compile中** です。特に内蔵GPUの場合は2〜3分待機してください。
- 5分以上待っても変化がない場合は、Blenderを閉じ、`shader_cache.bin` を手動削除して再起動してください。

### Q3. Transmission（透過ガラス）を設定したのに透けない
- 3Dビューポートが **「マテリアルプレビュー」または「レンダー」** になっているか確認してください（ソリッド表示では透けません）。また、Transmissionはマテリアル全体で1つの共通値です。

### Q4. 生成されたメッシュの角に細かいギザギザ・ジャギーが出る
- `Output & Quality` の解像度を上げるか、`Post-Process (Smoothing)` の **`Enable Smoothing` を ON** にしてください。さらに `Fix Normals` を押すと最高品質の法線が適用されます。

### Q5. Finalizeした後に元のSDF編集に戻したい
- `Finalize (Bake All)` 実行時、元プリミティブ群は **非表示の履歴コレクション（`SDF_History_...`）** に自動退避されています。アウトライナーで表示状態に戻すか、作業途中で必ず **`Snapshot Mesh`** を使って節目節目でバックアップを残してください。
