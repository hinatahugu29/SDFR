# SDF.R V16.1.0 Comprehensive User Guide

対象: Rust-GPU-SDF / SDF.R V16.1.0  
用途: 公式チュートリアル、操作マニュアル、機能棚卸し、動画台本の下敷き  
作成日: 2026-07-22（V16.0.7版）  
更新日: 2026-07-26（V16.1.0対応）

---

## はじめに

SDF.Rは、Blender上でSDF、つまりSigned Distance Fieldを使ったモデリングを行うためのアドオンです。通常のメッシュモデリングのように頂点、辺、面を直接編集するのではなく、Sphere、Box、Cylinder、Math Fieldなどの数学的な形状をStackに積み、それらをUnion、Subtract、Intersectで合成し、必要に応じてSmoothness、Edge、Layout、Deform、Layer Boundaryを加えながら形を作ります。

V16.1.0からは、これに加えて**Blender標準のカーブで描いたパスをそのままSDF形状にする**Curve Syncが使えます。数値で指定しづらい形は手で描く、という選択肢が増えました。

このドキュメントは、単なるボタン一覧ではなく、読めばSDF.Rの作業の流れが想像でき、実際に触り始められることを目標にしています。各UIの意味、再計算の起き方、どの場面でどの機能を使うべきか、V16.1.0で追加されたCurve Sync、V16.0.7で重要なLayer BoundaryやMath Fieldの使いどころまで、できるだけ網羅的に整理します。

SDF.Rは、小さな単機能ツールというより、Blender内にSDFベースの非破壊モデリング環境を追加するアドオンです。そのため、最初は少し情報量が多く見えます。ただし基本の考え方はシンプルです。

1. New SDF Workspaceで作業場所を作る。
2. Primitiveを追加する（またはCurve Syncでカーブを取り込む）。
3. Stack上で順番とOperationを調整する。
4. Resolution、Domain、MC/DC、Preview Qualityで見え方と負荷を調整する。
5. Math Field、Layer Boundary、Layout、Deformで複雑な形に発展させる。
6. Snapshot Meshで案を残し、Finalizeで通常メッシュとして確定する。

---

## このドキュメントの棚卸し方針

このマニュアルは、次の順番で機能を整理しています。

1. まずSDF.Rの基本思想を説明し、Stack、Primitive、Operation、Output Meshの関係を理解できるようにする。
2. 次に、インストール、初回起動、Workspace作成、最短操作という順番で、実際に触り始めるための導線を作る。
3. その後、UIの上から下へ順番に、Header、Diagnostics、Output & Quality、Post-Process、Stack、Material、Finalizeを棚卸しする。
4. 選択中Primitiveに出る設定として、Shape、Operation、Blend、Noise、Color、Material、Edge、Shellを整理する。
5. すべてのPrimitive typeを一覧化し、それぞれの用途とパラメータを説明する。
6. V16.1.0の新機能であるCurve Syncを、2つの登録方法とビューポート表示の仕様まで含めて独立章として整理する。
7. V16系の中心機能であるMath Fieldを独立章として深掘りする。
8. V16.0.7の重要機能であるLayer Boundaryを、Collection Dividerの基本から実制作例まで含めて整理する。
9. Layout、Group Layout、Deform Stack、Material、Snapshot、Finalizeを、制作フローに接続して説明する。
10. 最後に、実制作ワークフロー、パフォーマンス、トラブルシューティング、確定前チェックリスト、Operator ID、用語集で補強する。

網羅確認として、V16.1.0のUI棚卸し資料と実装上のPrimitive type、Operator IDを照合しています。読むだけで全操作を完全に暗記する必要はありませんが、困ったときに該当章へ戻れば、どの機能を何のために使うか判断できる構成を目指しています。

---

## 目次

1. SDF.Rの基本思想
2. 対応環境とインストール
3. 最短クイックスタート
4. UI全体の地図
5. Header / Status
6. Engine Diagnostics
7. Output & Quality
8. Post-Process
9. The Stack
10. Collection Divider / Layer Boundary
11. Primitive Settings
12. Add New Primitives
13. Curve Sync（Blenderカーブ連携）
14. Math Field
15. Layout / Instancing
16. Deform Stack
17. Material Workflow
18. Snapshot Mesh / Finalize / Cleanup
19. 実制作ワークフロー集
20. パフォーマンス調整
21. トラブルシューティング
22. 確定前チェックリスト
23. Operator ID一覧
24. 用語集

---

## 1. SDF.Rの基本思想

### SDFとは

SDFは、空間上の各点が形状の表面からどれくらい離れているかを表す関数です。値が0の場所が表面、負の場所が内側、正の場所が外側です。SDF.Rでは、この距離関数をGPU/Rust側で評価し、最終的にMarching CubesやDual Contouringで通常のBlenderメッシュへ変換します。

ユーザー側で意識するポイントは、難しい数式ではありません。SDF.Rでは、形状を「部品」として追加し、Stack上で「足す」「削る」「重なった部分だけ残す」を指定していきます。

### SDF.Rの中心概念

SDF.Rで最も重要なのは、次の5つです。

| 概念 | 意味 |
|----|----|
| Workspace | SDF作業用のCollectionと結果メッシュをまとめた作業空間 |
| Primitive | Sphere、Box、Cylinder、Math FieldなどのSDF形状 |
| Stack | Primitiveを評価する順番のリスト |
| Operation | Union、Subtract、Intersectの合成方法 |
| Output Mesh | SDF評価結果から生成される通常メッシュ |

この5つが分かると、SDF.R全体がかなり見通しやすくなります。

### Stackは順番が重要

SDF.RはStackの上から下へ評価されます。Unionだけなら順番の影響は比較的小さいですが、SubtractやIntersectが入ると順番で結果が大きく変わります。

例:

```text
01 Sphere / Union
02 Box / Subtract
```

この場合は、SphereからBoxの重なり部分を削ります。

```text
01 Box / Union
02 Sphere / Subtract
```

この場合は、BoxからSphereの重なり部分を削ります。同じ2つの形状でも、ベースになる形が変わるため、結果が違います。

### 作業中は軽く、最後だけ重く

SDF.Rでは、Resolutionを上げるほど品質は上がりますが、計算負荷も増えます。最初から高解像度で詰めるより、作業中はLowまたは中程度のResolutionで形を決め、最後にHighやLive Normalsを使って確認する流れが向いています。

おすすめの考え方:

| フェーズ | 設定 |
|----|----|
| ラフ造形 | Low、Preview Quality Low/Mid、Live Normals OFF |
| 形状確認 | 中程度のRes、必要に応じてForce Update |
| 仕上げ | High、Live Normals ON、Post-Process検討 |
| 保存/比較 | Snapshot Mesh |
| 確定 | Finalize (Bake) |

---

## 2. 対応環境とインストール

### 対応OS

V16.1.0では、Windows版が標準パッケージです。macOSとLinux向けには専用のexperimental test buildがあり、V16.1.0では3プラットフォームすべてが揃っています。

| OS | 配布ファイル例 | アーキテクチャ | 状態 |
|----|----|----|----|
| Windows | `SDF_R_16_1_0.zip` | x86-64 | 標準 |
| macOS | `SDF_R_16_1_0_MAC.zip` | Apple Silicon (arm64) | experimental test build |
| Linux | `SDF_R_16_1_0_LINUX.zip` | x86-64 | experimental test build |

macOS/Linux版は、Windows版と同じPython/UI構成をベースにしつつ、それぞれのOS向けnative moduleを含むテストビルドです。ユーザー向けには、環境差があり得ることを明記しておくと安全です。

注意点が2つあります。

- **macOS版はApple Silicon (arm64) 専用**です。Intel Macでは動作しません。
- **macOS版は署名されていません。** 有効化時にGatekeeperにブロックされた場合は、一度キャンセルし、「システム設定 > プライバシーとセキュリティ」を開いて、`rust_gpu_sdf.so` に関する表示の「このまま開く」をクリックしてから、Blenderで再度有効化してください。

### Blenderバージョン

Blender 3.6 LTS、4.x、5.x系を想定します。実際の見え方やUIの細部はBlender側のバージョンで多少変わることがあります。

### インストール手順

1. 配布ZIPをダウンロードします。
2. Blenderを起動します。
3. `Edit > Preferences > Add-ons` を開きます。
4. `Install...` を押します。
5. ZIPファイルを選択します。
6. `SDF-R` または `Rust-GPU-SDF` のアドオンを有効化します。
7. 3D Viewportで `N` キーを押し、Sidebarの `SDF-R` タブを開きます。

### アップデート時の注意

前バージョンから更新する場合、古いshader cacheが残っていると初期化が長くなったり、Initializingから進まないように見えることがあります。その場合はBlenderを閉じ、SDF.Rのshader cacheを削除してから再起動します。

Windowsの例:

```text
%APPDATA%\Blender Foundation\Blender\<Blender version>\datafiles\rust_gpu_sdf\shader_cache.bin
```

削除しても次回起動時に再生成されます。GPUやドライバを変更した直後も、cache削除が有効です。

**V16.0.xからV16.1.0へ更新する場合は、この手順を必ず行ってください。** V16.1.0ではGPUシェーダーのコードが変更されているため、古いcacheが残っていると初期化に失敗する可能性があります。

### 初回起動とWarm-up

初回利用時やcache削除後は、GPU shaderやcompute pipelineの準備で時間がかかることがあります。Blenderが一時的に反応しづらく見える場合がありますが、通常は少し待つと完了します。

目安:

| 状況 | 起きること |
|----|----|
| 初回起動 | Shader compile / cache作成で待ち時間が出る |
| DC初回利用 | Dual Contouring側のpipeline compileが走る場合がある |
| GPU/driver変更後 | 古いcacheと不整合が出る場合がある |

---

## 3. 最短クイックスタート

ここでは、SDF.Rの感覚を掴むために、SphereからBoxを削る最小手順を紹介します。

### Step 1: Workspaceを作る

1. 3D Viewportで `N` キーを押します。
2. `SDF-R` タブを開きます。
3. `New SDF Workspace` を押します。

これで、作業用の `SDF_Collection` と結果メッシュ用の `SDF_Result` が作られます。すでに作業中のSDF Workspaceがある場合は、履歴側へ退避されることがあります。

### Step 2: Sphereを追加する

`Add New Primitives` から `Sphere` を押します。

Sphereは最も基本的なSDF Primitiveです。追加後、ViewportにはSDFソースオブジェクトとGhost Preview、または結果メッシュが表示されます。

### Step 3: Boxを追加して削る

1. `Box` を追加します。
2. BoxをSphereに重なる位置へ移動します。
3. BoxのOperationを `Subtract` にします。
4. 必要に応じて `Smoothness` を調整します。

BoxがSphereから削られます。Smoothnessを上げると、切り口が柔らかくなります。Smoothnessを0に近づけると、くっきりした切り口に近づきます。

### Step 4: Force Updateする

Live UpdateがONなら多くの変更は自動反映されます。反映されない場合や、Live UpdateをOFFにして作業していた場合は `Force Update` を押します。

### Step 5: SnapshotまたはFinalizeする

まだ試行錯誤したい場合は `Snapshot Mesh` を押します。現在の結果だけが静的メッシュとして複製され、SDF Workspaceは編集可能なまま残ります。

最終的に通常メッシュとして確定したい場合は `Finalize (Bake)` を押します。

---

## 4. UI全体の地図

SDF.RのUIは、おおむね次の順番で並んでいます。

| セクション | 主な役割 |
|----|----|
| Header / Status | Live Update、Mesh表示、Ghost表示、GPU状態、新規Workspace |
| Engine Diagnostics | エンジン状態、ログ、mesh health、backend確認 |
| Output & Quality | Resolution、Domain、Preview、Curve Sync Guide Width、MC/DC、Weld、Live Normals |
| Post-Process | Geometry Nodes後処理の追加と調整 |
| The Stack | Primitive、Curve Sync、Collection Dividerの順番、Operation、Solo、削除 |
| Material | 標準ノード作成、一括Color、Metallic、Roughness、Transmission |
| Finalize / Output | Force Update、Fix Normals、Snapshot、Finalize |
| Group Settings | Collection Divider選択時のLayer BoundaryやGroup Layout |
| Primitive Settings | 選択Primitiveの形状、演算、色、形状パラメータ |
| Curve Sync Settings | 同期カーブ / Curve Refプロキシ選択時のPipe Radius、Subdiv、Operation、色 |
| Math Field | Formula、Preset、Mask、Boundary、Axis、Phase |
| Layout | Mirror、Radial、Spiral、Grid、Jitter |
| Deform | Elongate、Bend、Twist、Taper |
| Add New Primitives | 新規Primitive追加、Curve Ref追加 |
| Object Utilities / Cleanup | Wire/Solid、Move to SDF、All Clear |

はじめて触る場合は、すべてを一度に覚える必要はありません。まずは `New SDF Workspace`、`Add New Primitives`、`The Stack`、`Output & Quality`、`Force Update`、`Snapshot Mesh` だけで基本操作ができます。

---

## 5. Header / Status

HeaderはSDF.Rパネルの一番上にある、作業状態を切り替える場所です。

### Live Update

`Live Update` は、パラメータ変更やオブジェクトTransform変更を自動で結果へ反映するトグルです。

ONに向く場面:

- Primitive数が少ない。
- Resolutionが低め。
- 形を動かしながら反応を確認したい。

OFFに向く場面:

- Math Fieldが重い。
- PrimitiveやLayoutが多い。
- 高Resolutionで作業している。
- 連続で複数の設定を変えてから一度だけ更新したい。

Live UpdateをOFFにした場合、変更後に `Force Update` を押して手動反映します。

### Mesh icon

結果メッシュ `SDF_Result` の表示や生成系ワークフローを切り替えるためのトグルです。重い作業中は結果メッシュを隠し、Ghost Preview中心で編集すると軽くなります。

### Wire / Bounds icon

SDF Primitiveとして使っているソースオブジェクトの表示をWireやBounds系へ切り替えます。これは主にViewportの見やすさを調整する機能で、SDF結果そのものの形状を変えるものではありません。

### Ghost icon

GPU Ghost Previewの表示を切り替えます。Ghost Previewは、メッシュ化前のSDF結果を軽く確認するための表示です。

使い方の目安:

| 状況 | おすすめ |
|----|----|
| 軽く形を探りたい | Ghost ON、Mesh OFF |
| 最終メッシュの表面を確認したい | Mesh ON、Ghostは必要に応じて |
| 表示が混ざって見にくい | GhostまたはMeshの片方だけON |

### GPU: Ready / Updating

GPUエンジンの状態表示です。

| 表示 | 意味 |
|----|----|
| Ready | エンジンが利用可能 |
| Updating | メッシュ生成や更新処理中 |
| Initializing / Warming-up | 初期化やshader compile中 |

Updating中は次の操作がすぐ反映されないことがあります。特に高ResolutionやMath Fieldでは、少し待ってから確認します。

### New SDF Workspace

新しいSDF作業空間を作成します。初回作業はここから始めます。

作成される代表的なデータ:

| データ | 役割 |
|----|----|
| `SDF_Collection` | SDF Primitiveを格納するCollection |
| `SDF_Result` | SDF評価結果の出力メッシュ |
| Stack | 評価順序とOperationを保持 |

---

## 6. Engine Diagnostics

Engine Diagnosticsは、通常のモデリングでは常に開く必要はありません。ただし、結果が出ない、重い、欠ける、初期化で止まって見える、MC/DCやbackendの状態を確認したい、といった場合に役立ちます。

### 表示される主な情報

| 項目 | 意味 |
|----|----|
| GPU status | Ready、Updatingなどのエンジン状態 |
| Last Mesh diagnostics | 直近のmesh生成結果やhealth |
| Backend | Auto、GPU Chunked MC、CPU Chunked MCなど |
| Resolution | 現在の生成解像度 |
| Log path | 診断ログの確認先 |

### Perf

Performance logを出します。Preview、depsgraph、mesh生成などのタイミングを追いたいときに使います。通常ユーザー向けというより、重いケースの調査や開発者への報告に向きます。

### Mesh

Mesh生成のdebug logを出します。空結果、容量制限、backend選択、chunked fallbackなどを確認したいときに使います。

### Layout

Layout、Collection Divider、Layer Boundary、Radial/Grid/Mirrorなどの展開を調べるためのdebug logです。Group LayoutやLayer Boundaryの結果が想定と違うときに有効です。

### Diagnosticsを見るべき状況

| 症状 | 見るところ |
|----|----|
| 結果が空になる | Last Mesh diagnostics、Domain、Resolution |
| 高Resで失敗する | Protect Partial Mesh、Auto Safe Retry、Backend |
| Layer Boundaryが効いていないように見える | Layout log、Stack順序 |
| 更新が遅い | Perf log、Preview Quality、Resolution |

---

## 7. Output & Quality

Output & Qualityは、SDF.Rの品質と負荷を決める中心セクションです。

### Low / High

`Low` と `High` はResolution presetを切り替えるボタンです。

| ボタン | 用途 |
|----|----|
| Low | 作業中の軽い確認 |
| High | 最終確認、Snapshot、Finalize前の品質確認 |

`L-Val` と `H-Val` で、それぞれのプリセット値を変更できます。

### Res

`Res` はSDFグリッド解像度です。値が大きいほど細かい形状を拾いやすくなりますが、処理は重くなります。

目安:

| Res | 用途 |
|----|----|
| 32-64 | ラフ、配置検討 |
| 96-160 | 通常作業 |
| 192-256 | 仕上げ確認 |
| 512以上 | 大規模/高品質検証、処理負荷に注意 |

実用上は、最初から高Resで作るより、低Resで形を決めてから上げる方が快適です。

### Domain

`Domain` はSDF計算領域の大きさです。形状がDomainの外へ出ると、端が切れたように欠けることがあります。

`Auto Domain` がONなら、Stack内の形状に合わせて自動拡張されます。通常はON推奨です。

Domainを見直すべき状況:

- 形が途中で切れる。
- Deform後の先端が欠ける。
- Layoutで複製した外側の形が消える。
- Math FieldのExtentやObject Scaleを大きくした。

### Preview Quality

Ghost Preview側の品質です。これは最終メッシュのResolutionとは別です。

| Preview Quality | 用途 |
|----|----|
| Low | 軽い編集 |
| Mid | 通常確認 |
| High | DeformやMath Fieldのプレビュー欠けを減らす |

Ghost Previewの見え方が荒くても、最終メッシュはResとmeshing algorithmで決まります。

### Symmetry X/Y/Z

SDF計算全体に対して対称化をかけます。LayoutのMirrorとは別物です。

| 機能 | 違い |
|----|----|
| Symmetry | 計算結果全体を指定軸で対称化する |
| Layout Mirror | 選択PrimitiveまたはGroupを複製配置する |

対称の造形を素早く作るときはSymmetry、個別部品の反復配置を作るときはLayout Mirrorが向きます。

### Marching Cubes

Marching Cubesは標準的なSDFメッシュ生成方式です。

向く形:

- 有機的な形状
- 滑らかなブレンド
- 液体、粘土、キャラクターのラフ
- Math Fieldの複雑な構造

特徴:

- 安定しやすい。
- 丸い形が自然。
- ハードサーフェスの鋭い角は少し丸くなりやすい。

### Dual Contouring

Dual Contouringは、硬いエッジや平面を残したい場合に向くメッシュ生成方式です。

向く形:

- Box中心の形
- ハードサーフェス
- 機械部品風の形
- 角を残したいくり抜き

特徴:

- シャープなエッジを出しやすい。
- 初回利用時にcompileが走ることがある。
- 複雑な交差や高密度パターンではMarching Cubesの方が自然に見える場合もある。

### Backend

Backendはmesh生成の処理経路です。

| Backend | 用途 |
|----|----|
| Auto | 通常推奨。必要に応じてfallback |
| GPU Chunked MC | GPUでchunk分割しながらMC生成 |
| GPU Chunked DC | 実験的。chunk境界が見える可能性あり |
| CPU Chunked MC | CPU側でchunk分割しながらMC生成 |

通常はAutoでよいです。高Resolution、大Domain、多数Primitive、Math Fieldの重い構成で失敗する場合にChunked系を検討します。

### Chunk / Seam / From

Chunked生成時の詳細設定です。

| 項目 | 意味 |
|----|----|
| Chunk | 分割単位の大きさ |
| Seam | chunk境界のweld調整 |
| From | 指定Res以上で自動chunk化する開始値 |

Chunkedは安定性のための機能です。見た目のために最初から使うものではなく、大きなシーンで通常生成が厳しい場合の助けとして考えると分かりやすいです。

### Weld (Merge)

近接頂点を統合します。主に頂点整理やchunk境界の軽減に使います。

注意:

- 値を上げすぎると形状が潰れることがあります。
- 美観調整の万能機能ではありません。
- 表面の滑らかさはLive NormalsやPost-Processも合わせて考えます。

### Live Normals (Heavy)

高品質な法線を生成時に計算し、表示を滑らかにします。重いですが、最終確認では有効です。

作業中:

- OFFで軽くする。

仕上げ:

- ONにして面の見え方を確認する。

### Auto-enable Live Normals on High

High presetへ切り替えたときにLive Normalsを自動ONにします。仕上げ確認の手間を減らすための機能です。

### Protect Partial Mesh

空結果や容量不足など、危険な生成結果をそのまま適用しないように保護します。通常ON推奨です。

### Auto Safe Retry

問題が起きた場合、より安全な低解像度で再試行する機能です。高解像度で失敗しても、完全に作業が止まりにくくなります。

### Chunked CPU/GPU Fallback

通常生成が厳しい場合に、chunked backendへ逃がすためのfallbackです。大規模メッシュ、高Res、広Domainで有効です。

---

## 8. Post-Process

Post-Processは、SDF計算そのものではなく、生成された結果メッシュに対する後段処理です。`Setup Post Process` から `GeoRemesh_R` Geometry Nodesモディファイアを追加できます。

### Setup Post Process

`SDF_Result` にGeometry Nodesベースの後処理を追加します。エッジの乱れ、少し荒い面、メッシュ化後の見た目を整えたいときに使います。

### 使うタイミング

Post-Processは、最初からONにして形を作るより、形が固まってから見た目を整える段階で使うのが向いています。

おすすめの流れ:

1. SDF形状を作る。
2. Res、MC/DC、Weld、Live Normalsを確認する。
3. それでも表面の見え方を整えたい場合にPost-Processを使う。
4. 後処理あり/なしをSnapshotで比較する。

### Weldとの違い

| 機能 | 役割 |
|----|----|
| Weld | 近接頂点の統合、頂点整理 |
| Live Normals | 表示・レンダリング上の法線改善 |
| Post-Process | 後段Geometry Nodesによる見た目調整 |

Weldを強くしすぎて形を崩すより、役割を分けて調整する方が安全です。

---

## 9. The Stack

The StackはSDF.Rの中心です。ここにはPrimitiveとCollection Dividerが並び、上から下へ評価されます。

### Stack行の要素

| UI | 意味 |
|----|----|
| 色チップ | PrimitiveのColor |
| Object名 | 対応するSDF Objectを選択 |
| Operation | Union / Subtract / Intersect |
| Enabled | その項目を評価に含めるか |
| Up / Down | 評価順を変更 |
| Solo | 選択中項目だけ確認 |
| X | Stackから削除 |
| Add Collection Divider | グループ区切りを追加 |

### 色チップ

Primitiveの個別Colorを変更します。SDF.Rでは境界の色ブレンドにも関わるため、個別色の変更はmesh再計算を伴うことがあります。

作業中はPrimitiveごとに色を分けると構造が見やすくなります。仕上げで統一感を出したい場合は `Apply Color All` が便利です。

### Object名クリック

Stack行のObject名をクリックすると、Viewport上の対応Objectを選択できます。複雑なStackでは、どのPrimitiveがどこに効いているか分からなくなりやすいので、この同期機能はよく使います。

### Operation

Operationは、Primitiveがそれまでの結果にどう作用するかを決めます。

| Operation | 意味 | 例 |
|----|----|----|
| Union | 足す | SphereにCapsuleをつける |
| Subtract | 削る | Boxで穴を開ける |
| Intersect | 重なった部分だけ残す | Math FieldをCylinder範囲だけにする |

### Enabled

そのStack項目を一時的に無効化します。削除せずに比較したいときに便利です。

### Up / Down

Stack順を移動します。SubtractやIntersectの結果は順序に強く依存します。

例:

```text
01 Box / Union
02 Cylinder / Subtract
03 Sphere / Union
```

この場合、CylinderはBoxを削ったあと、Sphereはその結果に足されます。Sphereも削りたい場合は、SphereをCylinderより上に置くなど、順序を変える必要があります。

### Solo

選択中のStack項目だけを確認します。複雑な構成で「このPrimitiveが何をしているのか」を調べるときに役立ちます。

### X / Remove

Stack項目を削除します。Collection Dividerを削除する場合は、関連するグループ構成にも注意します。削除前にSnapshot Meshで状態を残しておくと安心です。

---

## 10. Collection Divider / Layer Boundary

Collection Dividerは、Stack内にグループの区切りを作るためのEmpty/Dividerです。特にLayer Boundaryとして使うことで、SDF.Rの表現力が大きく広がります。

### Collection Dividerの基本

`Add Collection Divider` を押すと、Stack内にDividerが追加されます。DividerはPrimitiveではありませんが、Stack上でグループの開始位置やレイヤー境界として機能します。

主な用途:

- Stackを読みやすく分ける。
- 複数Primitiveをグループとして扱う。
- Group Layoutをかける。
- Layer Boundaryでローカル評価範囲を作る。

### Group Settings

Dividerを選択すると、Group Settingsが表示されます。

| 項目 | 意味 |
|----|----|
| Name | Stack上のDivider名 |
| Layer Boundary | Divider以下をローカルLayerとして評価 |
| Break Parent | 親子/グループのつながりを区切る |
| Group Layout | Mirror、Radial、Spiral、Grid、Jitterをグループへ適用 |

### Duplicate Collection

Collection Dividerと、その対象グループを複製します。複雑な装飾パーツやパターンを作り、まとまりごと増やしたい場合に便利です。

### Break Parent

親子関係やグループのつながりを区切ります。Group Layoutや複製の単位を調整するための整理機能として考えると分かりやすいです。

### Layer Boundaryの考え方

通常のStackでは、IntersectやSubtractはそれ以前の結果全体に作用します。これは強力ですが、「装飾パターンだけを切りたい」「本体は削りたくない」という場面では不便です。

Layer BoundaryをONにしたDivider以下では、その範囲を一度ローカルLayerとして評価し、できあがったLayer結果を最後に全体へUnionします。

イメージ:

```text
Global Base
  +
(Layer Boundary内で作ったLocal Layer)
```

### Layer Boundaryの典型例

```text
01 Box / Union
02 Sphere / Subtract
== Collection 1 == / Layer Boundary ON
03 Math Field / Union
04 Cylinder / Intersect
```

このStackでは、BoxとSphereで本体を作り、その下のLayer Boundary内でMath Fieldを作ります。CylinderのIntersectは本体全体を切るのではなく、Layer内のMath Fieldにだけ効きます。

結果の考え方:

```text
(Box - Sphere) union (Math Field intersect Cylinder)
```

### Layer Boundaryが向く用途

- 本体はそのままで、模様だけを丸く切り抜く。
- Math Fieldを特定範囲にだけ出す。
- 装飾帯を本体に重ねる。
- 複数のPattern Layerを管理する。
- SubtractやIntersectの影響範囲を限定する。

### 注意点

Layer Boundaryは非常に強力ですが、Stackの読み方が少し変わります。意図が分かるようにDivider名を変えるのがおすすめです。

例:

```text
== Layer: Gyroid Band ==
== Layer: Radial Holes ==
== Layer: Surface Pattern ==
```

---

## 11. Primitive Settings

Primitiveを選択すると、そのPrimitiveの詳細設定が表示されます。ここでShape、Operation、Smoothness、Color、Material、Noise、Edge、Shell、Layout、Deformなどを調整します。

### Shape

選択中Primitiveの形状タイプです。SphereをBoxへ変えるように、後からShapeを変更できます。

### Operation

Stack上のOperationと同じです。Union、Subtract、Intersectを選びます。

### Blend Profile

Blend Profileは、Smoothnessが効いている部分の接続感を変えます。

| Profile | 印象 |
|----|----|
| Round | 標準的な丸いブレンド |
| Sharp | 角へ引き締まるようなブレンド |
| Soft | やわらかく広いブレンド |
| Tight | 深く締まった接続 |
| Chamfer | 平面的な面取り風の接続 |

### Chamfer Factor

Blend ProfileがChamferの場合に使う係数です。面取りの硬さや滑らかさを調整します。

### Smoothness

形状同士のつながりや、Subtract/Intersect境界の柔らかさを調整します。

目安:

| 値 | 印象 |
|----|----|
| 0.0 | くっきり |
| 0.05-0.2 | 控えめな丸み |
| 0.25-0.6 | なめらかな融合 |
| 0.7以上 | 大きく溶け合う、有機的 |

Smoothnessを上げすぎると、意図しない場所まで溶けることがあります。まず小さめの値から調整します。

### Noise / Scale

Primitive表面にノイズ変形を加えます。

| 項目 | 意味 |
|----|----|
| Noise | 変形の強さ |
| Scale | ノイズの細かさ |

用途:

- 岩肌風の表面。
- 有機的なゆらぎ。
- 完全な幾何形状を崩す。
- 抽象造形に情報量を足す。

### Color

Primitive個別の色です。SDF.Rでは生成メッシュにColor属性として渡されます。Setup Nodesを使うと、結果メッシュのMaterialでその色を読み取れます。

個別Colorは、ブレンド境界の色にも関わるため、正しい見え方にはmesh再計算が必要です。

### Color Mode

新規Primitive追加時の色割り当て方法です。

| Mode | 意味 |
|----|----|
| Fixed Palette | 内蔵パレットを順番に使う |
| Auto Hue | Hueを自動で回しながら色を作る |
| Single Color | 指定したBase Colorで追加する |

作業中に部品を見分けたい場合はFixed PaletteやAuto Hue、最初から統一色で作りたい場合はSingle Colorが向きます。

### Metallic / Roughness

Primitive個別のmaterial属性です。

| 項目 | 意味 |
|----|----|
| Metallic | 金属度 |
| Roughness | 粗さ |

これらはMaterial > Setup Nodesで作られる標準ノードと組み合わせて使います。

### Shape Parameters

ShapeごとのRadius、Height、Roundnessなどです。詳細は「Add New Primitives」で一覧化します。

### Edge

Primitive単体のエッジ処理です。Blend Profileが「Primitive同士の接続」の質感を調整するのに対し、Edgeは「Primitive自体の角」の処理に近いです。

| Edge | 印象 |
|----|----|
| Round | 標準的な丸め |
| Sharp | 引き締まった角 |
| Soft | 柔らかい角 |
| Tight | 角を残しつつ締める |
| Chamfer | 面取り |

Math FieldではEdgeは表示されません。

### Edge Size

Edge処理の大きさです。上げると角の処理が目立ちます。上げすぎると形の比率が変わるため、最初は小さめにします。

### Edge Chamfer Smoothness

EdgeがChamferの場合の滑らかさです。

### Shell (Hollow)

Primitiveを中空化します。SDF的には距離の絶対値を使って殻を作るイメージです。

| 値 | 意味 |
|----|----|
| 0 | 通常のソリッド |
| 0より大きい | 指定厚みの殻 |

用途:

- 薄い外殻。
- 管状、殻状の形。
- 切断したときに厚みを見せる形。

注意:

- Shellにより外側にも内側にも厚みが出るため、見た目のサイズが少し変わることがあります。
- SubtractやIntersectと組み合わせると複雑になるため、Resolutionを上げて確認します。

---

## 12. Add New Primitives

SDF.R V16.1.0のPrimitiveは、通常の幾何形状、Math Field、そしてカーブ系に分けられます。

| ボタン | shape_type | 主なパラメータ | 用途 |
|----|----|----|----|
| Sphere | `sphere` | Radius | 基本球、有機形状のベース |
| Box | `box` | Object Scale | 箱、ハードサーフェス、マスク |
| R-Box | `rounded_box` | Roundness | 角丸箱、プロダクト形状 |
| Torus | `torus` | Main Radius / Pipe Radius | リング、チューブ |
| Cylinder | `cylinder` | Radius / Height (Half) | 円柱、穴開け、軸形状 |
| Capsule | `capsule` | Radius / Height (Half) | 両端が丸い棒、骨格、有機接続 |
| Hex | `hex_prism` | Radius / Height (Half) | 六角柱、ナット風、パターン |
| Pyramid | `pyramid` | Base Size / Height | 四角錐、尖った形 |
| Taper | `capped_cone` | Bottom Radius / Top Radius / Height | 円錐台、先細り形状 |
| N-gon | `ngon_prism` | Radius / Sides / Height | 多角柱、任意角数の柱 |
| Ellipsoid | `ellipsoid` | Radius X/Y/Z | 楕円体、有機形状 |
| R-Cylinder | `rounded_cylinder` | Radius / Edge Radius / Height | 角丸円柱、ボタン、ケース |
| C-Torus | `capped_torus` | Main Radius / Pipe Radius / Angle | 部分トーラス、C字形 |
| Octahedron | `octahedron` | Size | 八面体、結晶形状 |
| Cut Sphere | `cut_sphere` | Cut Height | 切断球、ドーム |
| Math Field | `math_field` | Scale / Thickness / Bias / Extent | Gyroid、Schwarz P/Dなど |
| Bezier | `bezier_curve` | Point B / Point C / Start R / End R | テーパー付き曲線、角、爪、触手 |
| Curve Ref | （Primitiveではない） | Target Curve / Pipe Radius ほか | Blenderカーブを参照してパイプ化 |

`Curve Ref` だけは他と性質が異なり、新しい形状を作るのではなく「シーン内のBlenderカーブを参照するプロキシ」を追加します。詳細は「13. Curve Sync」で扱います。

### Sphere

最も基本的なPrimitiveです。Smooth Unionとの相性がよく、有機的な形のラフに向きます。

使いどころ:

- キャラクターや有機形状の塊。
- 液体的な接続。
- Subtract用の丸いくり抜き。
- Math Fieldの外形マスク。

### Box

Object Scaleで大きさを決める箱です。Hard Surfaceやマスク用途に強いPrimitiveです。

使いどころ:

- ベース形状。
- Subtract用の直線的な切り欠き。
- Math Fieldを箱状に閉じ込める。
- Layer Boundary内の範囲制御。

### Rounded Box

角が丸い箱です。プロダクトデザイン的な形や、角を柔らかくしたケース形状に向きます。

主なパラメータ:

- Roundness

### Torus

リング状のPrimitiveです。Main Radiusが全体の半径、Pipe Radiusがチューブ部分の太さです。

使いどころ:

- リング。
- パイプ。
- 装飾帯。
- Subtractで溝を作る。

### Cylinder

円柱です。Subtractと組み合わせることで穴開けに頻繁に使います。

使いどころ:

- 円柱パーツ。
- ボタン、軸、穴。
- Hard Surfaceのくり抜き。
- Math Fieldの円柱マスク。

### Capsule

両端が丸い棒状のPrimitiveです。Sphere同士をつなぐような有機形状に向いています。

使いどころ:

- 骨格。
- 枝、触手、チューブ。
- Smooth Unionでの柔らかい接続。

### Hex Prism

六角柱です。機械的なパターンやナット形状に向きます。

### Pyramid

四角錐です。尖った形、抽象形状、装飾パーツに使えます。

### Tapered Cylinder

上下で半径の違う円柱です。円錐台、先細りパーツ、ノズルのような形に向きます。

### N-gon Prism

Sidesで角数を変えられる多角柱です。三角柱から多角形柱まで扱えます。

### Ellipsoid

X/Y/Z方向に半径を持つ楕円体です。Object Scaleとは別に形状パラメータとして楕円を作れます。

### Rounded Cylinder

角が丸い円柱です。ボタン、キャップ、パーツの端処理に向きます。

### Capped Torus

一部が切られたトーラスです。C字形、湾曲したチューブ、装飾弧に使えます。

### Octahedron

八面体です。結晶、シャープな装飾、抽象的な構造に向きます。

### Cut Sphere

平面で切られた球です。ドーム、半球風の形、平らな面を持つ丸いパーツに使えます。

### Math Field

周期的な数理フィールドです。V16系の中心機能で、Gyroid、Schwarz P、Schwarz DなどをFormulaから選択します。詳細は「14. Math Field」で扱います。

### Bezier

V16.1.0で追加された、3次元の2次ベジェ曲線です。制御点を数値で指定するタイプの曲線Primitiveで、Blenderのカーブオブジェクトは使いません。

| 項目 | 意味 |
|----|----|
| Point B (Mid) | 中間の制御点 |
| Point C (End) | 終点 |
| Start R | 始点側の半径 |
| End R | 終点側の半径 |

始点はPrimitive自身の原点です。オブジェクトを動かせば曲線全体が追従します。Start RとEnd Rを別々に指定できるため、根元が太く先端が細い形を1つのPrimitiveで作れます。

使いどころ:

- 角、爪、牙のようなテーパー形状。
- 触手、しっぽ。
- 数値で管理したい湾曲したパーツ。

Layout（Radial、Mirrorなど）やDeform Stackとも組み合わせられます。手で自由に描きたい場合は「13. Curve Sync」のほうが向いています。

---

## 13. Curve Sync（Blenderカーブ連携）

V16.1.0で追加された機能です。Blender標準のカーブオブジェクトで描いたパスを、そのままSDF形状として扱えます。生成されるのは「別のメッシュ」ではなくSDFそのものなので、他のPrimitiveと同じようにUnion、Subtract、Intersectでき、Smoothnessで滑らかに溶け合わせることもできます。

これまでSDF.Rの形状はすべて数値で指定する必要がありました。ケーブル、取っ手、蔓、配管のような「手で描いたほうが早い」形状を、Blenderのカーブツールでそのまま作れるようになったのが、この機能の狙いです。

### 登録方法は2通り

Curve Syncには、目的に応じて2つの登録方法があります。どちらも同じシーンで併用できます。

| 方法 | 操作 | 向く場面 |
|----|----|----|
| コレクションに入れる | カーブを選択して `Move to SDF`、またはOutlinerでSDF Collectionへドラッグ | そのカーブがSDF形状を作るためだけに存在する場合 |
| Curve Ref（参照） | `Add New Primitives` の `Curve Ref` を押し、`Target Curve` にカーブを指定 | カーブをアニメーションやGeometry Nodesと共有したい場合 |

#### 方法A: コレクションに入れる

1. `Shift+A > Curve` でカーブを作ります。
2. カーブを選択したまま `Move to SDF` を押します。
3. The Stackに `Curve Sync` アイテムとして並びます。

カーブ本体がSDF Collectionのメンバーになるため、Collection Dividerを動かすとカーブも追従します。

#### 方法B: Curve Ref（参照）

1. `Add New Primitives` の `Curve Ref` を押します。小さなプロキシがStackに追加されます。
2. プロキシを選択し、`Target Curve` でシーン内の任意のカーブを指定します。

ボタンを押した時点でカーブが選択されていれば、自動で割り当てられます。

この方式では、元のカーブは移動も変更もされません。アニメーションやGeometry Nodesで使っているカーブをそのまま参照できます。

また、設定がプロキシ側に保存されるため、**同じカーブを複数のCurve Refから参照し、それぞれ別の太さ・色・Operationにする**ことができます。1本のパスから太いパイプと細い溝を同時に作る、といった使い方が可能です。

### Curve Sync Settings

同期中のカーブ、またはCurve Refプロキシを選択すると表示されます。

| 項目 | 意味 |
|----|----|
| Target Curve | 参照先のカーブ（Curve Refのみ） |
| Edit '<カーブ名>' | 対象カーブを選択して編集モードへ入る |
| Pipe Radius | 生成されるパイプの太さ |
| Subdiv Samples | パスのサンプリング密度。急なカーブほど上げると追従がよくなる |
| Operation | Union / Subtract / Intersect |
| Smoothness | 他の形状との接続のなめらかさ |
| Color / Metallic / Roughness | カーブごとのマテリアル属性 |

`Edit` ボタンは、対象カーブを選択してそのまま編集モードに入ります。他のオブジェクトを編集中でも安全に抜けてから切り替わるので、Outlinerからカーブを探す必要がありません。

### 対応するカーブの種類

| 種類 | 対応 |
|----|----|
| Bezier | 完全対応。ハンドルも反映され、`Subdiv Samples` が効きます |
| Poly | 完全対応。制御点をそのまま使います |
| NURBS | Blender側の評価を使用。**`Subdiv Samples` は効きません**。カーブ側の `Resolution Preview U` で調整します |
| 閉じたカーブ（Cyclic） | 対応。始点と終点が繋がったループになります |

カーブにBevelやExtrudeを設定していると、パスではなく面が生成されるため、Curve Syncは粗い近似にフォールバックします。**Curve Syncで使うカーブは、Bevelなしの素のパスにしておくのが確実です。**

### ビューポート表示について（重要）

リアルタイムのGhost Previewでは、Curve Syncは**カーブに沿った色付きのガイド線**として表示されます。パイプの正確な形状は表示されません。

これは意図的な仕様です。Ghost Previewはレイマーチング方式で、1本のレイのステップごとに全Primitiveを評価します。カーブを大量のパイプ断片に展開してPreviewに載せると、カーブを追加するたびにビューポート全体が重くなってしまいます。そのためCurve Syncについては、軽量なガイド線表示に割り切っています。

| 見たいもの | 操作 |
|----|----|
| パスの位置と本数 | Ghost Previewのガイド線でそのまま確認できる |
| 実際のパイプ形状、太さ、ブレンド | `Show Result Mesh` をONにする、または `Force Update` を押す |

ガイド線の太さは、Output & Qualityの `Curve Sync Guide Width` で調整できます（1〜10）。ガイド線はGPUの単純な線描画なので、太くしても負荷はほとんど変わりません。

### Stack順序に注意

Curve Syncも他のPrimitiveと同じく、**Stackの順番に従って評価されます**。

SubtractやIntersectは「それより上にあるもの」に対して働くため、Curve SyncをSubtractにする場合は、削られる側の形状をStack上でCurve Syncより上に置く必要があります。Stackの一番上にSubtractのCurve Syncを置いても、削る対象がないため何も起きません。

### 使いどころ

- ケーブル、チューブ、配管
- 取っ手、フレーム、ワイヤー
- 蔓、枝、有機的なうねり
- Subtractにして、本体に溝やスリットを彫る
- Intersectにして、パスに沿った領域だけを残す

### Bezier Curve Primitiveとの使い分け

Curve Syncとは別に、V16.1.0では `Bezier` プリミティブも追加されています。

| | Curve Sync | Bezier Primitive |
|----|----|----|
| 形の決め方 | Blenderのカーブツールで描く | 制御点を数値で指定 |
| 制御点の数 | 自由 | 2点（中間点と終点。始点はオブジェクト原点） |
| 太さ | 一定（Pipe Radius） | 始点と終点で個別指定（テーパー可） |
| Layout / Deform | 非対応（v1スコープ） | 対応 |
| 向く場面 | 手で描きたい自由なパス | テーパーのついた角・爪・触手など |

手で自由に描きたいときはCurve Sync、数値で管理したいテーパー形状や、配列・変形と組み合わせたいときはBezier Primitiveが向きます。

---

## 14. Math Field

Math FieldはV16系の重要機能です。以前のGyroid Fieldをより汎用化し、Formulaを選んで複数のTPMS系パターンを使える形になっています。

### Math Fieldでできること

- Gyroidのような周期構造を作る。
- Schwarz P / Schwarz Dのような別パターンを試す。
- Box、Sphere、CylinderのMaskで有限範囲に閉じ込める。
- Thicknessで壁の厚みを調整する。
- Biasで面の出方をずらす。
- Axis X/Y/Zで軸ごとの密度を変える。
- Use Previous as Maskで直前Primitiveの中へ詰める。
- Layer Boundaryと組み合わせて、本体を壊さず装飾範囲だけ制御する。

### Formula

| Formula | 印象 |
|----|----|
| Gyroid | 流れのある連続的な周期構造 |
| Schwarz P | 規則性が強く、構造的 |
| Schwarz D | 斜め方向やDiamond的なリズムが出やすい |

最初はGyroidで動きを理解し、その後Schwarz P/Dを試すと違いが分かりやすいです。

### Preset

PresetはScale、Thickness、Extentなどをまとめて初期設定するための機能です。

| Preset | 用途 |
|----|----|
| Custom | 現在値を維持 |
| Fine | 細かいセル、薄め |
| Medium | 標準的なバランス |
| Coarse | 大きめのセル |
| Thick | 厚い壁 |
| Shell | オフセット感のあるシェル状 |

Presetを選んだ後に手動でScaleやThicknessを微調整できます。

### Mask

Math Fieldの範囲を切る形です。

| Mask | 意味 |
|----|----|
| Box | Extentを箱の半サイズとして使う |
| Sphere | Extentを球の半径として使う |
| Cylinder | Extentを円柱の半径/半高さとして使う |

MaskはMath Fieldの形そのものを有限範囲にするための基本設定です。より複雑な範囲制御にはUse Previous as MaskやLayer Boundaryを使います。

### Boundary

Mask境界付近の挙動を制御します。

| Boundary | 印象 |
|----|----|
| Fade | 境界に向かってなだらかに消える |
| Open | 境界で開いた切断になる |
| Box Clip | 境界で閉じたクリップに近い |

見せたい作例によって適したBoundaryは変わります。装飾として端をきれいに見せたい場合は、複数試して比較します。

### Phase

周期フィールドの位相をずらします。Objectを動かさず、穴や稜線の位置だけをずらしたいときに使います。

使いどころ:

- 正面に穴が来すぎる場合にずらす。
- 切断面にきれいなパターンを出す。
- 同じFormulaでも表情を変える。

### Axis X/Y/Z

軸ごとのField密度を調整します。Objectを非均一Scaleした場合、Patternが伸びて見えることがあります。その場合はAxisを調整します。

### Auto Match Scale

Object Scaleの絶対値をAxis X/Y/Zへ反映し、Math Fieldの世界空間密度を合わせやすくするボタンです。

使う場面:

1. Math Fieldを追加する。
2. Object ScaleでX/Y/Zの比率を変える。
3. Patternが伸びて見える。
4. `Auto Match Scale` を押す。
5. Axis X/Y/ZがObject Scaleに近い値へ調整される。

### Scale / Thickness / Bias / Extent

| パラメータ | 意味 |
|----|----|
| Scale | セル密度、周期の細かさ |
| Thickness | 壁厚 |
| Bias | 面の出方、オフセット |
| Extent | Mask範囲、Fieldの広がり |

Scaleを上げると細かいパターンになりますが、細かい形状を拾うにはResolutionも必要になります。Scaleだけ上げてResが低いと、パターンが潰れたり欠けたりします。

### Use Previous as Mask

選択中のMath Fieldを直前のPrimitiveでマスクするための便利ボタンです。

典型的な流れ:

```text
01 Box / Union
02 Math Field / Intersect
```

手順:

1. Boxを追加し、外形にしたい大きさへ調整する。
2. Math Fieldを追加する。
3. Math Fieldを選択する。
4. `Use Previous as Mask` を押す。

これで、直前のBoxを外形マスクとしてMath Fieldを使いやすくなります。

### Math FieldとLayer Boundary

Math FieldはLayer Boundaryと非常に相性がよいです。通常のIntersectは過去の形状全体に効いてしまいますが、Layer Boundary内でIntersectすれば、Math Field Layerだけを切れます。

おすすめ構成:

```text
01 Body Box / Union
02 Body Cut Sphere / Subtract
== Layer: Pattern == / Layer Boundary ON
03 Math Field / Union
04 Cylinder Mask / Intersect
```

この場合、本体は削らず、Math FieldだけをCylinder範囲に限定できます。

---

## 15. Layout / Instancing

Layoutは、PrimitiveまたはGroupを数学的に複製配置する機能です。実際に大量のBlenderオブジェクトを作るのではなく、SDF評価時にインスタンス展開するため、試行錯誤しやすいのが特徴です。

LayoutはPrimitiveにも、Collection DividerのGroupにも使えます。

### Mirror

指定軸でミラー複製します。

| 項目 | 意味 |
|----|----|
| X/Y/Z | ミラーする軸 |
| Offset | 対称面からの距離 |

左右対称パーツや、同じ穴を両側に置きたい場合に使います。

### Radial

円周上に複製します。

| 項目 | 意味 |
|----|----|
| Count | 個数 |
| Radius | 円の半径 |
| Axis | 回転軸 |

使いどころ:

- 放射状の穴。
- リング装飾。
- 歯車風のパターン。
- 複数パーツの円形配置。

### Spiral

Radialに高さ方向のPitchを加えた螺旋配置です。

| 項目 | 意味 |
|----|----|
| Count | 個数 |
| Radius | 半径 |
| Pitch | 1周または配置に伴う高さ方向のずれ |
| Axis | 螺旋軸 |

使いどころ:

- 螺旋階段風の構造。
- 巻き付く装飾。
- 有機的な連続配置。

### Grid

格子状に複製します。

| 項目 | 意味 |
|----|----|
| Count X/Y/Z | 各軸の個数 |
| Spacing X/Y/Z | 各軸の間隔 |

使いどころ:

- 穴の配列。
- パーツの規則的な反復。
- ラティスやパネル状パターン。

### Jitter

配置にランダムな揺らぎを加えます。

| 項目 | 意味 |
|----|----|
| Seed | ランダムの種 |
| Strength | 揺らぎの強さ |

均一すぎる配置を少し崩したいときに使います。強すぎるとパターンの意図が崩れるので、小さめから調整します。

### Rotation (Indiv & Accum)

Layoutインスタンスごとの回転を制御します。

| 項目 | 意味 |
|----|----|
| Rotation X/Y/Z | 各インスタンスにかける基本回転 |
| Accum Rot X/Y/Z | インスタンスごとに蓄積される回転 |

RadialやSpiralでは、Accum Rotを使うと配置に動きが出ます。

#### 大きな回転角をかけたときの制限

Radial / Spiralは、空間を等角度のスライスに折りたたむ方式でインスタンスを作っています。そのため、**あるコピーが自分のスライスをはみ出すほど回転すると、はみ出した部分が欠けることがあります。**

目安として、蓄積された回転量が `180° ÷ Count` を超えるあたりから欠けが出はじめます。Countが6なら30°前後が境目です。Accum Rotはインスタンスが進むごとに蓄積されるため、後ろのインスタンスほど影響を受けやすくなります。

欠けが出た場合の対処:

| 対処 | 内容 |
|----|----|
| 回転量を下げる | Accum Rotを小さくする |
| Countを増やす | 1スライスあたりの角度が狭くなるが、はみ出し量に対する余裕は増える |
| Group Layoutを使う | Collection Dividerでグループ化し、Group Layout側で配置する |

なお、V16.1.0では**回転を組み合わせた際にジオメトリが欠ける別のバグ（バウンディング計算の誤り）を修正済み**です。Radial Axisを X / Y にしたときの欠けも併せて直っています。以前のバージョンで諦めた配列があれば、再確認する価値があります。

### Primitive LayoutとGroup Layoutの違い

| 種類 | 対象 |
|----|----|
| Primitive Layout | 選択Primitive単体 |
| Group Layout | Collection Divider以下のまとまり |

複数のPrimitiveで作った小さな部品をまとめて円形配置したい場合はGroup Layoutが向きます。

---

## 16. Deform Stack

Deform Stackは、Primitiveに対して空間変形を順番に適用する機能です。BlenderのModifier Stackに少し似ていますが、SDF空間上で評価されるため、後から形状やOperationと組み合わせて調整できます。

### 基本操作

| UI | 意味 |
|----|----|
| + | Deformを追加 |
| - | 選択中Deformを削除 |
| Up / Down | Deform順序を入れ替える |
| Enabled | 一時的に有効/無効 |
| Type | Elongate / Bend / Twist / Taper |

Deformは最大2つまで追加できます。順番は結果に影響します。

例:

```text
Twist -> Bend
```

と

```text
Bend -> Twist
```

は違う結果になります。

### Elongate

X/Y/Z方向へ空間を伸ばす変形です。

使いどころ:

- Sphereを長い丸い形へ伸ばす。
- Capsule的な印象を別Primitiveに与える。
- 有機形状の比率調整。

### Bend

指定軸まわりに曲げます。

主な項目:

| 項目 | 意味 |
|----|----|
| Axis | 曲げ軸 |
| Angle | 曲げ角度 |
| Origin Offset | 曲げ中心のずれ |

使いどころ:

- CylinderやCapsuleを曲げる。
- 有機的な枝やチューブ。
- 直線的な部品に動きを出す。

### Twist

指定軸に沿ってねじります。

使いどころ:

- TorusやCylinderのねじれ。
- Math FieldではなくPrimitive自体の流れを作る。
- 抽象形状に動きを加える。

### Taper

先細り、または太さ変化を与える変形です。

使いどころ:

- 柱や棒の先端を細くする。
- 有機形状に成長方向を出す。
- ハードサーフェス部品に角度感を加える。

### Origin Offset

変形の基準位置をずらします。例えば、棒の中心ではなく端を基準に曲げたい場合に使います。

---

## 17. Material Workflow

SDF.Rは、PrimitiveごとのColor、Metallic、Roughnessを生成メッシュへ属性として渡します。Materialセクションでは、それらを読み取る標準ノードの作成や、一括適用ができます。

### Setup Nodes

`Setup Nodes` は、SDF.RのColor、Metallic、Roughness属性を読み取る標準マテリアルノードを作成します。

使うタイミング:

- 生成メッシュにPrimitive色を反映したい。
- Metallic/Roughnessを使いたい。
- SnapshotやFinalize前に見た目を確認したい。

### Reset

標準ノード構成へ戻します。共有Metallic / Roughness / Transmission / IORも初期値へ戻ります。

### Base Color + Apply Color All

すべてのPrimitiveへ同じColorを適用します。個別色の境界ブレンドを再評価するより軽く済むため、仕上げ時に全体を統一したいときに便利です。

使い方:

1. Base Colorを選ぶ。
2. `Apply Color All` を押す。
3. 必要に応じてSnapshotで色案を残す。

### Metallic / Roughness + Apply Material All

すべてのPrimitiveへ同じMetallic/Roughnessを適用します。V16.1.0からは、同じボタンでTransmission / IORもマテリアルへ適用されます。

| 項目 | 意味 | 適用範囲 |
|----|----|----|
| Metallic | 金属度 | Primitiveごと（頂点属性） |
| Roughness | 表面の粗さ | Primitiveごと（頂点属性） |
| Transmission | ガラスのような透過 | **マテリアル全体** |
| IOR | 屈折率（Transmissionが0より大きいときのみ有効。ガラスは1.45前後） | **マテリアル全体** |

### Transmission / IOR（V16.1.0）

Color、Metallic、Roughnessは頂点属性として保存されるため、Primitiveごとに違う値を持てます。一方**Transmissionはマテリアル全体に対する1つの値**です。同じSDFオブジェクトの中で「この部分だけガラス、他は不透明」という指定は現時点ではできません。

使う手順:

1. `Setup Nodes` を押してSDFマテリアルを作成する（未作成だと書き込み先がないため反映されません）。
2. Transmissionを上げる。必要ならIORを調整する。
3. `Apply Material All` を押す。
4. ビューポートを **Material Preview** または **Rendered** に切り替えて確認する。

Ghost Previewは屈折を再現しないため、Transmissionの効果はGhost Preview上では確認できません。

### 個別色と一括色の使い分け

| 操作 | 向く場面 |
|----|----|
| 個別Color | 作業中の構造把握、色分け作品 |
| Apply Color All | 仕上げ確認、一体感を出す |
| 個別Metallic/Roughness | パーツごとに質感を変える |
| Apply Material All | 全体の質感をまとめる |

### 制作中のおすすめ

1. 作業中はPrimitiveごとに色を分ける。
2. StackやBooleanの効き方を把握する。
3. 形が固まったらApply Color Allで統一色を試す。
4. Metallic/Roughnessを調整する。
5. Snapshot Meshで素材案を残す。

---

## 18. Snapshot Mesh / Finalize / Cleanup

### Fix Normals

高品質法線を再計算して適用します。表面表示やレンダリング時の見え方が気になる場合に使います。

### Force Update

現在のSDF設定から結果メッシュを手動で再生成します。

使う場面:

- Live UpdateをOFFにしていた。
- 設定変更後に明示更新したい。
- 反映が遅れているように見える。
- 仕上げ前に確実に最新状態へしたい。

### Snapshot Mesh

現在のSDF結果から静的メッシュコピーを作ります。Live SDF Workspaceは維持されます。

用途:

- 案を保存する。
- Material案を比較する。
- Math Fieldの密度違いを横に並べる。
- Layer Boundary範囲の違いを残す。
- Finalize前の保険を作る。

おすすめ:

重要な変更前にはSnapshot Meshを押しておくと安心です。SDF.Rは非破壊的に作業できますが、試行錯誤の節目を見える形で残すと制作判断がしやすくなります。

### Finalize (Bake)

SDF結果を通常メッシュとして確定します。Live編集を終える操作です。

Finalize前に確認すること:

- Resは十分か。
- Domainで欠けていないか。
- MC/DCの選択は適切か。
- Live NormalsやPost-Processの有無を確認したか。
- Snapshot Meshで案を残したか。
- Stack名やLayer Boundaryの意味が分かる状態か。

### Wire/Solid

選択オブジェクトの表示をWire/Solid系で切り替えます。SDF計算自体には影響しません。

### Move to SDF

選択中のBlenderオブジェクトをSDF_Collectionへ移し、SDF Primitiveとして扱います。形状推定は名前や対応情報に依存するため、標準Primitive追加ほど確実ではありません。既存オブジェクトをSDFワークフローへ整理したい場合に使います。

### Include Baked Results

All Clear時に、確定済みや履歴のメッシュも削除対象に含めるかを決めます。

### All Clear

SDF関連データを削除します。Include Baked ResultsがONの場合、履歴や確定済み結果も対象になります。強い掃除操作なので、必要なSnapshotやFinalize結果がある場合は注意します。

---

## 19. 実制作ワークフロー集

### Workflow 1: Sphere + Boxで基本操作を覚える

目的:

SDF.Rの基本である「足す、削る、Smoothnessを調整する」を覚えます。

手順:

1. `New SDF Workspace` を押す。
2. `Sphere` を追加する。
3. `Box` を追加する。
4. BoxをSphereに重ねる。
5. BoxのOperationを `Subtract` にする。
6. Smoothnessを0.0、0.1、0.3程度で比較する。
7. `Force Update` で結果を更新する。
8. `Snapshot Mesh` で状態を残す。

見るべきポイント:

- Stack順で結果が変わる。
- Smoothnessで切り口が変わる。
- Live Update ON/OFFで作業感が変わる。

### Workflow 2: Organic Smooth Blend

目的:

SDFらしい滑らかな有機形状を作ります。

手順:

1. Sphereを中心に置く。
2. CapsuleやSphereを追加して周囲に配置する。
3. すべてUnionにする。
4. Smoothnessを0.25から0.8程度で調整する。
5. Blend ProfileをRoundやSoftで比較する。
6. Noiseを少し加えて自然さを出す。
7. High + Live Normalsで確認する。

向く用途:

- キャラクターのラフ。
- 粘土的な造形。
- 液体、枝、骨格。
- 抽象的な丸いオブジェクト。

### Workflow 3: Hard Surface Cut

目的:

BoxやCylinderを使い、ハードサーフェス風の形を作ります。

手順:

1. Boxをベースにする。
2. Cylinderを追加し、Subtractにする。
3. Cylinderを移動/回転して穴を作る。
4. EdgeをChamferまたはTightにする。
5. Smoothnessは低めにする。
6. Dual Contouringへ切り替える。
7. WeldやLive Normalsを調整する。

見るべきポイント:

- DCは角を残しやすい。
- Smoothnessを上げすぎるとハード感が消える。
- EdgeとBlend Profileを分けて考える。

### Workflow 4: Boxの中にMath Fieldを入れる

目的:

Math Fieldを外形に閉じ込めた構造体を作ります。

手順:

1. Boxを追加し、外形サイズを決める。
2. Math Fieldを追加する。
3. Math Fieldを選択し、`Use Previous as Mask` を押す。
4. FormulaをGyroid、Schwarz P、Schwarz Dで比較する。
5. Scaleでセル密度を調整する。
6. Thicknessで壁厚を調整する。
7. Phaseで見せたい位置を調整する。
8. 必要ならAuto Match Scaleを押す。

注意:

Scaleを細かくするほど、Resも上げないと形が拾えません。作業中は粗め、仕上げで高Resにします。

### Workflow 5: Layer Boundaryで装飾だけ切る

目的:

本体を壊さず、装飾LayerだけをIntersectで制御します。

手順:

1. BoxやRounded Boxで本体を作る。
2. `Add Collection Divider` を押す。
3. Dividerの `Layer Boundary` をONにする。
4. Divider以下にMath Fieldを追加する。
5. さらにCylinderを追加し、Intersectにする。
6. Cylinderを動かしてMath Fieldの見える範囲を調整する。

Stack例:

```text
01 Rounded Box / Union
02 Cylinder / Subtract
== Layer: Gyroid Window == / Layer Boundary ON
03 Math Field / Union
04 Cylinder Mask / Intersect
```

見るべきポイント:

- Cylinder Maskは本体を切らない。
- Layer内のMath Fieldだけを切る。
- 装飾の範囲制御に向く。

### Workflow 6: Group Layoutで反復装飾を作る

目的:

複数Primitiveで作った小さな部品を、グループとしてRadialやGrid配置します。

手順:

1. Capsule + Sphereなどで小さなパーツを作る。
2. まとまりの前にCollection Dividerを置く。
3. Dividerを選択する。
4. Group LayoutのRadialをONにする。
5. CountとRadiusを調整する。
6. RotationやAccum Rotで向きを整える。
7. Jitterを少し加える。

向く用途:

- 装飾パーツの円形配置。
- 放射状の穴。
- SFパーツ。
- アクセサリー的な繰り返し。

### Workflow 7: Snapshotで案を比較する

目的:

作業を戻せる安心感を作り、形状案を比較します。

手順:

1. 形がよくなった時点でSnapshot Mesh。
2. Math FieldのScaleを変える。
3. もう一度Snapshot Mesh。
4. Layer BoundaryのMask範囲を変える。
5. さらにSnapshot Mesh。
6. 複数案を並べて見比べる。
7. 採用案をFinalizeする。

おすすめ:

Material、Math Field、Post-Processの比較ではSnapshotがとても有効です。

### Workflow 8: 仕上げMaterial

目的:

形状の完成後、作品として見えるように色と質感を整えます。

手順:

1. `Setup Nodes` を押す。
2. 作業色が残っている場合はBase Colorを選ぶ。
3. `Apply Color All` を押す。
4. Metallic/Roughnessを調整する。
5. `Apply Material All` を押す。
6. High + Live Normalsで確認する。
7. Snapshot Meshで素材案を残す。

### Workflow 9: Ghost Preview中心で軽く編集する

目的:

重いシーンでも制作テンポを保ちます。

手順:

1. Mesh iconをOFFにする。
2. Ghost iconをONにする。
3. Preview QualityをLowまたはMidにする。
4. PrimitiveやLayoutを編集する。
5. 形が決まったらMesh iconをONに戻す。
6. Force Updateする。

### Workflow 10: 高Resolutionで失敗する場合

目的:

大規模メッシュを安全に生成します。

手順:

1. Diagnosticsを開く。
2. Last Mesh diagnosticsを確認する。
3. Resを一段下げる。
4. Protect Partial MeshをONにする。
5. Auto Safe RetryをONにする。
6. AutoまたはChunked Backendを試す。
7. Chunk / Seamを調整する。

### Workflow 11: カーブで有機的なパーツを足す（V16.1.0）

目的:

本体にケーブルや蔓のようなパーツを、手で描いて足します。

手順:

1. 本体となる形状をStackに作っておく。
2. `Shift+A > Curve > Bezier` でカーブを追加し、大まかな形に整える。
3. カーブを選択したまま `Curve Ref` を押す。Target Curveに自動で割り当てられる。
4. `Pipe Radius` で太さを決める。
5. `Smoothness` を上げて、本体との接続をなじませる。
6. 形を微調整したくなったら `Edit` ボタンで編集モードに入り、制御点を動かす。
7. Ghost Previewはガイド線表示なので、実形状は `Show Result Mesh` をONにして確認する。
8. 必要なら `Color` を変えて、本体と区別する。

ポイント:

- カーブが複雑なら `Subdiv Samples` を上げる。ただし上げすぎると評価コストが増える。
- 本体に溝を彫りたい場合は `Operation` をSubtractにする。**その際、削られる本体がStack上でCurve Syncより上にあることを確認する。**

### Workflow 12: 1本のカーブから太さ違いのパーツを作る（V16.1.0）

目的:

同じパスに沿って、太いパイプと細い溝を同時に作ります。

手順:

1. カーブを1本用意する（SDF Collectionに入れる必要はない）。
2. `Curve Ref` を追加し、Target Curveにそのカーブを指定。Pipe Radiusを太めに、OperationはUnion。
3. もう一度 `Curve Ref` を追加し、**同じカーブ**を指定。Pipe Radiusを細めに、OperationはSubtract。
4. Stack順で、Union側がSubtract側より上にあることを確認する。

設定はカーブ本体ではなくプロキシ側に保存されるため、この使い分けが可能です。カーブを編集すれば両方が同時に追従します。

---

## 20. パフォーマンス調整

### 重くなる主な要因

| 要因 | 影響 |
|----|----|
| 高Resolution | メッシュ生成が重くなる |
| 広Domain | 評価範囲が増える |
| 多数Primitive | SDF評価が増える |
| Math Field | 細かい周期構造で負荷が増える |
| LayoutのCount増加 | インスタンス評価が増える |
| Live Normals | 法線計算が重い |
| DC | 初回compileや複雑形状で負荷が出る場合 |

### 軽くする順番

1. Resを下げる。
2. Mesh iconをOFFにし、Ghost Preview中心にする。
3. Preview QualityをLowにする。
4. Live UpdateをOFFにし、Force Updateで手動更新する。
5. Live NormalsをOFFにする。
6. Layout Countを一時的に下げる。
7. Math FieldのScaleを粗くする。
8. Domainを必要以上に大きくしない。

### 最終確認時だけ重くする

最終出力前にだけ、次を行います。

1. High presetへ切り替える。
2. Live NormalsをONにする。
3. MC/DCを比較する。
4. 必要ならPost-Process。
5. Snapshot Mesh。
6. Finalize。

---

## 21. トラブルシューティング

### Q. 初回起動やLive Update開始時に固まったように見える

GPU shaderやpipelineのcompileが走っている可能性があります。少し待ってください。数分待っても進まない場合は、Blenderを閉じてshader cacheを削除し、再起動します。

### Q. Initializingから進まない

古いshader cache、GPU変更、driver更新後の不整合が考えられます。cacheを削除して再起動します。

### Q. 形状の端が切れる

Domainが足りていない可能性があります。Auto DomainがONか確認し、必要ならDomainを大きくします。DeformやLayoutで外側に広がった場合もDomain不足が起きます。

### Q. Math Fieldが潰れる、穴が消える

Scaleに対してResolutionが足りない可能性があります。Resを上げるか、Scaleを粗くします。Thicknessが薄すぎる場合もメッシュ化で拾えないことがあります。

### Q. Math Fieldが伸びて見える

Object Scaleを非均一にした場合は、Axis X/Y/Zを調整します。まず `Auto Match Scale` を試します。

### Q. Intersectが本体まで切ってしまう

Layer Boundaryを使います。切りたい装飾やMath FieldをLayer Boundary以下に置き、Intersect用Primitiveも同じLayer内に入れます。

### Q. 高Resolutionで結果が空になる

容量制限や生成失敗の可能性があります。Resを下げ、Protect Partial Mesh、Auto Safe Retry、Chunked Fallbackを確認します。

### Q. エッジが少し乱れる

Res、MC/DC、Weld、Live Normals、Post-Processを順に確認します。SDFをポリゴン化する以上、急な交差や細かいFieldでは多少の乱れが出ることがあります。

### Q. Curve Syncがビューポートでは細い線にしか見えない

仕様です。Ghost PreviewはCurve Syncをガイド線として表示します。実際のパイプ形状は `Show Result Mesh` をONにするか、`Force Update` を押すと確認できます。詳細は「13. Curve Sync」を参照してください。

### Q. Curve SyncをSubtractにしたのに何も削れない

SubtractはStack上でそれより上にあるものに対して働きます。削られる側の形状（Union）がCurve Syncより上にあるか確認してください。Stackの一番上にSubtractを置いても、削る対象がないため何も起きません。

### Q. Curve SyncのSubdiv Samplesを変えても何も変わらない

対象カーブがNURBSの可能性があります。NURBSはBlender側の評価を使うため、`Subdiv Samples` は効きません。カーブデータプロパティの `Resolution Preview U` で調整してください。

### Q. Transmissionを上げてもガラスにならない

3点確認してください。`Setup Nodes` でSDFマテリアルを作成済みか、`Apply Material All` を押したか、ビューポートがMaterial PreviewまたはRenderedになっているか。TransmissionはGhost Previewでは再現されません。

### Q. Radialで回転を大きくするとインスタンスが欠ける

Radialは空間を等角度のスライスに折りたたむ方式のため、回転がスライス幅（目安 `180° ÷ Count`）を超えるとはみ出した部分が欠けます。回転量を下げる、Countを増やす、Group Layoutを使う、のいずれかで回避できます。詳細は「15. Layout / Instancing」を参照してください。

### Q. 色変更が重い

個別Colorはブレンド色再評価のためmesh再計算が必要です。全体色の確認なら `Apply Color All` を使うと軽く済みます。

### Q. Finalize後に戻したい

Finalize前にSnapshot Meshを残す運用がおすすめです。履歴に退避される場合もありますが、重要な節目は明示的にSnapshotとして残すと安心です。

---

## 22. 確定前チェックリスト

### 形状

- Stack順は意図通りか。
- Union/Subtract/Intersectは正しいか。
- Layer Boundaryの範囲は分かりやすいか。
- Divider名は意味が分かるか。
- Domainで形が欠けていないか。
- Math FieldのScale/ThicknessはResで拾えているか。

### 品質

- LowだけでなくHighでも確認したか。
- MC/DCを比較したか。
- Weldで潰れすぎていないか。
- Live Normalsあり/なしを確認したか。
- Post-Processの有無を比較したか。

### Material

- Setup Nodes済みか。
- 作業用の個別色を残すか、Apply Color Allで統一するか。
- Metallic/Roughnessは意図通りか。
- SnapshotでMaterial案を残したか。

### 安全

- 重要な節目でSnapshot Meshを残したか。
- Finalizeしてよい状態か。
- All ClearやInclude Baked Resultsの状態を確認したか。

---

## 23. Operator ID一覧

| Operator ID | ラベル | 概要 |
|----|----|----|
| `sdf.add_primitive` | Add SDF Primitive | Primitiveを追加 |
| `sdf.toggle_display` | Toggle Wire/Solid | 表示モード切替 |
| `sdf.move_to_sdf_collection` | Move to SDF Collection | 選択ObjectをSDF Collectionへ移動 |
| `sdf.duplicate_collection` | Duplicate Collection | Collection Dividerグループを複製 |
| `sdf.bake_mesh` | Snapshot Mesh | 静的メッシュコピー作成 |
| `sdf.setup_material` | Setup Color Material | 標準Material nodes作成 |
| `sdf.reset_material` | Reset Shader Nodes | 標準Material nodesへ戻す |
| `sdf.apply_color_all` | Apply Color To All | 全PrimitiveへColor一括適用 |
| `sdf.apply_material_all` | Apply Material To All | Metallic/Roughness一括適用、Transmission/IOR適用 |
| `sdf.update_normals` | Update Normals | 法線更新 |
| `sdf.generate_mesh` | Generate SDF Mesh | 結果メッシュ生成/Force Update |
| `sdf.add_selected` | Add Selected to SDF | 選択ObjectをSDF Stackへ追加 |
| `sdf.make_output` | New SDF Workspace | 新規Workspace作成 |
| `sdf.stack_move` | Move Stack Item | Stack項目移動 |
| `sdf.stack_remove` | Remove Stack Item | Stack項目削除 |
| `sdf.select_stack_obj` | Select SDF Object | Stack対応Object選択 |
| `sdf.use_previous_as_mask` | Use Previous as Mask | Math Fieldを直前PrimitiveでMask |
| `sdf.match_math_field_axis_to_scale` | Auto Match Scale | Math Field AxisをObject Scaleへ合わせる |
| `sdf.setup_post_process` | Setup Post Process (GN) | GeoRemesh_R追加 |
| `sdf.finalize` | Finalize (Bake All) | SDF結果を確定メッシュ化 |
| `sdf.set_resolution_preset` | Set Resolution Preset | Low/High切替 |
| `sdf.all_clear` | All Clear | SDF関連データ削除 |
| `sdf.deform_add` | Add Deform | Deform追加 |
| `sdf.deform_remove` | Remove Deform | Deform削除 |
| `sdf.deform_move` | Move Deform | Deform順序変更 |
| `sdf.switch_algo` | Switch Algorithm | MC/DC切替 |
| `sdf.add_collection_divider` | Add Collection Divider | Collection Divider追加 |
| `sdf.add_curve_sync` | Add Curve Sync Reference | Curve Refプロキシ追加（V16.1.0） |
| `sdf.edit_curve_sync_target` | Edit Target Curve | 参照先カーブを選択して編集モードへ（V16.1.0） |

---

## 24. 用語集

| 用語 | 意味 |
|----|----|
| SDF | Signed Distance Field。表面からの距離で形を表す仕組み |
| Primitive | SDFを構成する基本形状 |
| Stack | Primitiveの評価順序 |
| Union | 形状を足す |
| Subtract | 形状で削る |
| Intersect | 重なった部分だけ残す |
| Smoothness | 接続や境界のなめらかさ |
| Blend Profile | Smoothnessの質感 |
| Edge Profile | Primitive単体の角処理 |
| Domain | SDF計算領域 |
| Resolution | メッシュ生成の解像度 |
| Ghost Preview | メッシュ化前の軽量GPU Preview |
| Marching Cubes | 滑らかで安定したメッシュ生成方式 |
| Dual Contouring | シャープな角を残しやすいメッシュ生成方式 |
| Math Field | Gyroid / Schwarz P/Dなどの周期的数理場 |
| Layer Boundary | Divider以下をローカルLayerとして評価する境界 |
| Collection Divider | Stack内のグループ区切り |
| Layout | Mirror/Radial/Gridなどのインスタンス配置 |
| Deform | Bend/Twist/Taperなどの空間変形 |
| Snapshot Mesh | Live SDFを残したまま作る静的メッシュコピー |
| Finalize | SDF結果を通常メッシュとして確定する操作 |
| Curve Sync | Blender標準のカーブをSDF形状（パイプ）として取り込む機能 |
| Curve Ref | カーブ本体を動かさずに参照するためのプロキシアイテム |
| Guide Line | Curve SyncのGhost Preview表示。実形状ではなく軽量な線表示 |
| Transmission | マテリアル全体にかかるガラス的な透過。Primitive個別指定は不可 |

---

## まとめ

SDF.R V16.1.0の基本は、PrimitiveをStackへ積み、OperationとSmoothnessで形を作ることです。そこにMath Field、Layer Boundary、Layout、Deformを加えることで、単なるブーリアンツールを超えたSDFモデリング環境になります。

V16.1.0では、これに「手で描く」という選択肢が加わりました。数値で組み立てるのが向く形はPrimitiveで、描いたほうが早い形はCurve Syncで、と使い分けられます。

最初は次の順番で覚えるのがおすすめです。

1. New SDF Workspace
2. Sphere / Box / Cylinder
3. Union / Subtract / Intersect
4. Smoothness / Blend Profile
5. Resolution / Domain / MC / DC
6. Snapshot Mesh
7. Curve Sync
8. Math Field
9. Layer Boundary
10. Layout / Deform
11. Material / Finalize

この順番で触ると、SDF.Rの濃い機能群を無理なく自分の制作フローへ取り込めます。
