# SDF.R V16.0.7 Workflow Examples

対象: **Rust-GPU-SDF / SDF.R V16.0.7** \| 作成日: 2026-07-19 \| 用途: 想定ワークフロー例・制作手順集


この資料は「ボタンの意味」ではなく、「どう使うと制作が進みやすいか」をまとめたものです。SDF.Rは、プリミティブを積むだけでなく、Stack順序、Smoothness、Layer Boundary、Math Field、Material一括適用、Snapshot Meshを組み合わせることで、作品として仕上げやすくなります。



**基本思想:** 形を作る段階では `Live Update` と `Ghost Preview` を活用し、重くなったら結果メッシュを隠して軽く動かします。見た目をまとめる段階では `Apply Color All` / `Apply Material All` / `Snapshot Mesh` を使い、確定が必要になったら `Finalize (Bake)` へ進みます。


## 0. 全体の制作フェーズ

| フェーズ | 主な操作 | 見るべきポイント | おすすめ設定 |
|----|----|----|----|
| ラフ造形 | `Sphere`, `Box`, `Cylinder`, `Union/Subtract` | 大きなシルエット、比率、塊感 | `Res` 低め、`Preview Quality` Low/Mid |
| 接続調整 | `Smoothness`, `Blend Profile`, `Edge` | 繋がりの自然さ、角の残り方、面の張り | Smoothnessを前の値から継承しつつ微調整 |
| 装飾/パターン | `Math Field`, `Use Previous as Mask`, `Layer Boundary` | 穴、繰り返し、模様、切り抜き範囲 | Layer BoundaryでIntersectionsの影響範囲を限定 |
| 仕上げ | `Apply Color All`, `Apply Material All`, `Live Normals` | 作品としての統一感、質感、見え方 | High preset + Live Normals |
| 比較/保存 | `Snapshot Mesh`, `Finalize (Bake)` | 案の保存、メッシュとしての扱いやすさ | 試作はSnapshot、確定はFinalize |

## 1. 最短の基本ワークフロー: まず形を出す


### Basic Sphere + BoxでSDFの感覚を掴む

最初に覚えるべき最小構成です。SDF.Rの強みは「置く、重ねる、削る、滑らかにつなぐ」がすぐ見えることです。

1.  `New SDF Workspace` を押して作業空間を作ります。
2.  `Sphere` を追加します。ViewportにGhost PreviewとSDFソースが出ます。
3.  `Box` を追加し、Sphereに重なる位置へ移動します。
4.  Boxの `Op` を `Subtract` に変えます。
5.  `Smoothness` を0.1から0.4程度で動かし、切り口の柔らかさを確認します。
6.  `Force Update` で結果メッシュを明示更新し、必要なら `Fix Normals` を押します。


**狙い:** SDFは順番と演算で結果が変わります。まず「Unionで足す」「Subtractで削る」「Smoothnessで繋げる」を身体に入れると、以後のワークフローがかなり楽になります。



## 2. 有機的な塊を作るワークフロー


### Organic 複数Sphereを滑らかに融合してベース形状を作る

キャラクターのラフ、液体、骨格、丸いプロダクト形状などに向く流れです。

1.  `Sphere` を1つ追加し、中心の塊にします。
2.  追加で `Sphere` や `Capsule` を置き、すべて `Union` にします。
3.  `Smoothness` を0.25から0.8程度に上げ、接続部をなじませます。
4.  形状ごとの色を一旦変えておくと、どの塊がどこに効いているか把握しやすくなります。
5.  全体のシルエットが見えたら `Apply Color All` で一色化し、作品としてのまとまりを確認します。
6.  `High` に切り替え、`Live Normals` を使って面の流れを確認します。


**色の使い分け:** 制作途中は個別色で構造理解、仕上げでは `Apply Color All` で統一、という切り替えが使いやすいです。個別色変更はブレンド色再評価のためMesh再計算が走ります。



## 3. ハードサーフェス寄りのワークフロー


### Hard Surface Box / Cylinder / DCで角を残す

機械部品、ケース、ジョイント、ブロック形状などに向く流れです。

1.  `Box` を追加し、Object Scaleで大きさを決めます。
2.  `Cylinder` を追加して `Subtract` にし、穴やスロットを作ります。
3.  `Edge` を `Chamfer` や `Tight` にして角の表情を調整します。
4.  `Smoothness` は低めにし、角が溶けすぎないようにします。
5.  `Dual Contouring` に切り替えて、角や平面の残り方を確認します。
6.  必要に応じて `Weld (Merge)` と `Scale` を調整します。


**注意:** DCは硬いエッジに向きますが、複雑な交差や高密度パターンではMCのほうが安定して見えることもあります。最終的な見た目でMC/DCを選ぶのが実用的です。



## 4. Math Fieldを使ったパターン入り形状


### Math Field BoxやSphereの中にGyroid/Schwarzを詰める

V16系の中心機能です。ラティス、穴あき構造、TPMS系の装飾、内部構造の試作に向きます。

1.  `Box` または `Sphere` を追加し、外形マスクにしたい大きさへ調整します。
2.  `Math Field` を追加します。
3.  Math Fieldを選択した状態で `Use Previous as Mask` を押します。
4.  `Formula` で `Gyroid`, `Schwarz P`, `Schwarz D` を切り替え、セル構造を比較します。
5.  `Scale` でセル密度、`Thickness` で壁厚、`Bias` で面の出方を調整します。
6.  `Phase` を動かし、穴やリッジが見せたい場所へ来るように調整します。
7.  非均一スケールした場合は `Auto Match Scale` を押して、Axis X/Y/ZをObject Scaleに合わせます。


**おすすめ:** Formulaは作品の印象が大きく変わります。Gyroidは流れがあり、Schwarz Pは規則的で構造的、Schwarz Dは斜め方向のリズムが強めです。



## 5. Layer Boundaryで「切り抜き範囲」を限定する


### Layer Boundary 既存の形を壊さず、装飾レイヤーだけIntersectする

V16.0.7らしいワークフローです。通常のIntersectは過去プリミティブ全体へ効きますが、Layer Boundaryを使うと「このレイヤー内だけでIntersectして、最後に全体へ合算」できます。

1.  まず `Sphere` や `Box` でベース形状を作ります。ここは通常の `Union/Subtract` で構いません。
2.  `Add Collection Divider` を押してDividerを追加します。
3.  追加したDividerを選択し、`Layer Boundary` をONにします。
4.  Dividerより下に `Math Field` を追加します。
5.  さらに下に `Cylinder` や `Box` を追加し、`Intersect` にします。
6.  結果は `ベース形状 ∪ (Math Field ∩ Cylinder)` のように考えます。
7.  Cylinderを動かすと、ベース形状を問答無用で切らず、Math Fieldレイヤーの見える範囲だけを調整できます。

| Stack例                                | 意味                        |
|----------------------------------------|-----------------------------|
| 01 Box / Union                         | ベース形状                  |
| 02 Sphere / Subtract                   | ベースへの通常カット        |
| == Collection 1 == / Layer Boundary ON | ここから下をローカルLayer化 |
| 03 Math Field / Union                  | 装飾パターン                |
| 04 Cylinder / Intersect                | 装飾パターンだけの表示範囲  |


**使いどころ:** 「本体には穴を開けたくないが、模様だけを丸く切り抜きたい」「表面装飾をレイヤー的に重ねたい」という場面で強いです。



## 6. Collection Dividerをグループ配置として使う


### Grouping 複数プリミティブをひとまとまりでRadial/Grid展開する

個別プリミティブにLayoutをかけるだけでなく、Dividerを選択してGroup Layoutを使うと、複数形状をセットとして展開できます。

1.  複数プリミティブで小さな部品を作ります。例: Capsule + Sphere + Cylinder。
2.  Stack上でそのまとまりの位置に `Add Collection Divider` を追加します。
3.  Dividerを選択し、`Group Layout` の `Radial` をONにします。
4.  `Count` と `Radius` を調整して円周配置します。
5.  `Rotation (Indiv & Accum)` で向きや回転の蓄積を調整します。
6.  さらに `Jitter` を少し足すと、均一すぎない配置になります。


**ポイント:** Group Layoutは「装飾パーツを一個ずつ作る」よりも速く、後からCountやRadiusを変えられるため、パターンデザインの試行錯誤に向きます。



## 7. Snapshot Meshで案を残しながら進める


### Iteration この状態どうかな、を残す

FinalizeはライブSDFワークスペースを確定方向へ進める操作ですが、Snapshot Meshはライブ編集を残したまま結果だけをメッシュコピーできます。

1.  ある程度形がまとまったら `Snapshot Mesh` を押します。
2.  `SDF_Snapshots` に静的メッシュが作られ、そのSnapshotだけが選択状態になります。
3.  Snapshotへ別マテリアルを当てたり、横に移動して比較します。
4.  元のSDFワークスペースはそのままなので、さらにStackやパラメータを変えて別案を作れます。
5.  複数案を並べて比較し、最後に採用案を `Finalize (Bake)` します。


**おすすめ場面:** 色やMaterialをいじり始めた時、Math Fieldの密度違いを比べたい時、Layer Boundaryの範囲違いを比較したい時に有効です。



## 8. Materialをまとめて仕上げる


### Finishing 色・Metallic・Roughnessで作品感を整える

V16.0.6以降の仕上げ系機能を使う流れです。形が見えてきたら、全体のMaterial感を早めに確認すると判断しやすくなります。

1.  `Setup Nodes` を押して、Color/Metallic/Roughness属性を読む標準マテリアルを作ります。
2.  制作中はプリミティブごとの色で構造を見分けます。
3.  仕上げ確認に入ったら、Material欄のBase Colorを選び `Apply Color All` を押します。
4.  `Metallic` と `Roughness` を調整し、`Apply Material All` を押します。
5.  `High` と `Live Normals` で見え方を確認します。
6.  迷ったら `Snapshot Mesh` でMaterial案を残します。

| 操作 | 再計算 | 理由 |
|----|----|----|
| `Apply Color All` | 軽量更新 | 全体を一色にするだけなので既存Color属性更新で足りる。 |
| 個別 `Color` | Mesh再計算 | ブレンド境界の色をSDF距離評価から再計算する必要がある。 |
| `Apply Material All` | 軽量更新 | Metallic/Roughnessを全体属性として置き換えられる。 |
| 個別Metallic/Roughness | Mesh再計算 | 個別属性としてSDF評価結果へ反映する。 |


## 9. Ghost Preview中心の軽量編集


### Performance 重いシーンを軽く動かす

プリミティブ数が増えたり、Math Fieldが重くなった時の逃げ方です。

1.  `Mesh icon` をOFFにして、結果メッシュ表示を隠します。
2.  `Ghost icon` はONにして、Previewだけで形を確認します。
3.  `Preview Quality` をLowまたはMidにします。
4.  移動・回転・Scale・Stack調整を行います。
5.  形が決まったら `Mesh icon` をONに戻し、`Force Update` を押します。
6.  最終確認で `High` と `Live Normals` を使います。


**考え方:** 編集中は軽く、確認時だけ重く、が基本です。毎回高品質メッシュを待つより、Ghost Previewで構図を決めてからMesh生成するほうが制作テンポを保ちやすいです。



## 10. 高解像度・大規模メッシュの安定化


### Large Scene Chunked / Protect系を使う

高Res、広Domain、多数プリミティブ、Math Fieldを組み合わせると、GPU容量や生成上限に当たることがあります。その場合の見方です。

1.  `Engine Diagnostics` を開き、`Last Mesh` のHealthを確認します。
2.  `EMPTY_RESULT` や `CAPACITY_LIMITED` が出る場合、まずResを下げます。
3.  `Protect Partial Mesh` をONにし、破損結果が適用されないようにします。
4.  `Auto Safe Retry` をONにして、低解像度再試行を有効にします。
5.  必要に応じて `Chunked GPU Fallback` または `Chunked CPU Fallback` をONにします。
6.  `Chunk Cells` と `Seam` を調整し、継ぎ目と安定性のバランスを取ります。


**注意:** 高解像度は品質だけでなく、処理時間・VRAM・ドライバ安定性に効きます。最初から最大品質で詰めず、Lowで形を決め、最後にHighへ上げる流れが安全です。



## 11. Post-Processで尖りや乱れを整える


### Post Process 後段GNで美観を整える

MC/DCのどちらでも、急な曲率やIntersect境界では少しエッジが乱れることがあります。これはSDFをポリゴン化する以上、完全には避けにくい部分です。後段で整える発想が有効です。

1.  通常通りSDF形状を作ります。
2.  `Setup Post Process` を押して `GeoRemesh_R` を追加します。
3.  Post-Process欄に展開されるGNパラメータを調整します。
4.  尖りすぎた箇所、段差、細かな乱れを見ながらスムージング量を決めます。
5.  `Snapshot Mesh` で後段あり/なしを比較します。
6.  採用する見た目が決まったら `Finalize (Bake)` で確定します。


**方針:** Weldを美観万能ツールにするより、Weldは頂点整理、GNは見た目調整、と役割を分けたほうが制御しやすいです。



## 12. Layer Boundary + Group Layoutで装飾帯を作る


### Pattern Band 本体に装飾帯を巻く

リング状の装飾、プロダクト外装のライン、穴あき帯などを作るイメージです。

1.  `Cylinder` や `Rounded Box` で本体を作ります。
2.  `Add Collection Divider` を追加し、`Layer Boundary` をONにします。
3.  Divider以下に小さな `Box` や `Capsule` を追加します。
4.  それらを `Radial` やGroup Layoutで円周上に複製します。
5.  必要なら装飾側に `Subtract` や `Intersect` を入れて、装飾レイヤー内だけで形を整えます。
6.  本体とは別レイヤーとして合算されるので、装飾帯の調整がしやすくなります。


**向いている用途:** SFパーツ、アクセサリー、器、ケース、パネルライン、リブ、放射状の穴パターン。



## 13. Finalizeする前のチェックリスト


### Checklist 確定前に見るところ



**形状**

- Resは十分か
- Domainで欠けていないか
- MC/DCのどちらが作品に合うか
- Weldで潰れすぎていないか



**表面**

- Live Normalsあり/なしを比較したか
- Post-Processの有無を比較したか
- 尖りや面の乱れが許容範囲か



**色・質感**

- Setup Nodes済みか
- Color属性が意図通りか
- Metallic/Roughnessを全体で揃えるか個別にするか



**保険**

- Snapshot Meshを残したか
- Layer Boundaryの意図がStack上で分かる名前か
- Finalize後に戻りたい場合の履歴があるか




## 14. よくある判断の分岐

| 状況 | まず試すこと | 次に試すこと |
|----|----|----|
| 形が重い | Mesh icon OFF、Preview Quality Low | Resを下げる、Chunked Fallbackを使う |
| エッジが少し乱れる | Resを上げる、Live Normals | Post-Process GNでスムーズ調整 |
| Intersectが過去形状まで切る | Layer Boundaryを追加 | 切りたい装飾だけDivider以下へ置く |
| Math Fieldが伸びて見える | Auto Match Scale | Axis X/Y/Zを手動微調整 |
| 色変更が重い | Apply Color Allで全体色を試す | 個別色はブレンド維持のため再計算を許容する |
| 案を残したい | Snapshot Mesh | 確定時のみFinalize |

Source basis: SDF.R V16.0.7 UI behavior and current implementation notes. Companion document: `SDF_R_V16_0_7_UI_Command_Inventory.html`.
