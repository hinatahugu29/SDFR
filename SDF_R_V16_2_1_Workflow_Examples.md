# SDF.R V16.2.1 Workflow Examples

対象: **Rust-GPU-SDF / SDF.R V16.2.1** \| 作成日: 2026-07-19 \| 更新日: 2026-09-09 \| 用途: 想定ワークフロー例・制作手順集


この資料は「ボタンの意味」ではなく、「どう使うと制作が進みやすいか」をまとめたものです。SDF.Rは、プリミティブを積むだけでなく、Stack順序、Smoothness、Layer Boundary、Math Field、Material一括適用、Snapshot Meshを組み合わせることで、作品として仕上げやすくなります。



**基本思想:** 形を作る段階では `Live Update` と `Ghost Preview` を活用し、重くなったら結果メッシュを隠して軽く動かします。見た目をまとめる段階では `Apply Color All` / `Apply Material All` / `Snapshot Mesh` を使い、確定が必要になったら `Finalize (Bake)` へ進みます。


## 0. 全体の制作フェーズ

| フェーズ | 主な操作 | 見るべきポイント | おすすめ設定 |
|----|----|----|----|
| ラフ造形 | `Sphere`, `Box`, `Cylinder`, `Union/Subtract` | 大きなシルエット、比率、塊感 | `Res` 低め、`Preview Quality` Low/Mid |
| 接続調整 | `Smoothness`, `Blend Profile`, `Edge` | 繋がりの自然さ、角の残り方、面の張り | Smoothnessを前の値から継承しつつ微調整 |
| 装飾/パターン | `Math Field`, `Use Previous as Mask`, `Layer Boundary` | 穴、繰り返し、模様、切り抜き範囲 | 分けたい部品ごとにDividerを立てて影響範囲を限定 |
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

通常のIntersectは過去プリミティブ全体へ効きますが、Layer Boundaryを使うと「このレイヤー内だけでIntersectして、最後に全体へ合算」できます。

**Dividerはグループの下端に置きます。そのDividerより上に積んだものが、そのグループです。** そして**本体側にもDividerが要ります**。本体をレイヤーにしないと、装飾を乗せた後のシーンへ本体が混ざりにいくためです。

1.  まず `Sphere` や `Box` でベース形状を作ります。ここは通常の `Union/Subtract` で構いません。
2.  `Add Collection Divider` を押し、`Layer Boundary` をONにします。ここで**本体のグループが閉じます**。
3.  その下に `Math Field` を追加します。
4.  さらに下に `Cylinder` や `Box` を追加し、`Intersect` にします。
5.  もう一度 `Add Collection Divider` を押し、`Layer Boundary` をONにします。ここで**装飾のグループが閉じます**。
6.  結果は `ベース形状 ∪ (Math Field ∩ Cylinder)` のように考えます。
7.  Cylinderを動かすと、ベース形状を問答無用で切らず、Math Fieldレイヤーの見える範囲だけを調整できます。

| Stack例                              | 意味                              |
|--------------------------------------|-----------------------------------|
| 01 Box / Union                       | ベース形状                        |
| 02 Sphere / Subtract                 | ベースへの通常カット              |
| == Layer: Body == / Layer Boundary ON| ここまでが本体グループ            |
| 03 Math Field / Union                | 装飾パターン                      |
| 04 Cylinder / Intersect              | 装飾パターンだけの表示範囲        |
| == Layer: Pattern == / Layer Boundary ON | ここまでが装飾グループ        |

装飾Divider側の `Layer Blend` で、装飾と本体の境目の硬さを決めます。既定の `0.00` なら硬い境界、`0.10` 程度なら少し馴染みます。

**使いどころ:** 「本体には穴を開けたくないが、模様だけを丸く切り抜きたい」「表面装飾をレイヤー的に重ねたい」という場面で強いです。



## 6. Collection Dividerをグループ配置として使う


### Grouping 複数プリミティブをひとまとまりでRadial/Grid展開する

個別プリミティブにLayoutをかけるだけでなく、Dividerを選択してGroup Layoutを使うと、複数形状をセットとして展開できます。

1.  複数プリミティブで小さな部品を作ります。例: Capsule + Sphere + Cylinder。
2.  そのまとまりの**すぐ下**に `Add Collection Divider` を追加します。Dividerより上に積んだものがグループになります。
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
2.  `Add Collection Divider` を追加し、`Layer Boundary` をONにします。ここで本体のグループが閉じます。
3.  その下に小さな `Box` や `Capsule` を追加します。
4.  さらに `Add Collection Divider` を追加し、`Layer Boundary` と `Group Layout` の `Radial` をONにします。上に積んだ装飾がこのDividerのグループなので、Layoutもレイヤー分割も同じDividerで効きます。
5.  必要なら装飾側に `Subtract` や `Intersect` を入れて、装飾レイヤー内だけで形を整えます。
6.  本体とは別レイヤーとして合算されるので、装飾帯の調整がしやすくなります。

> **V16.1.3以前からの変更**: 以前はGroup LayoutとLayer Boundaryを同じDividerでONにすると
> Layoutが無視されるバグがありました。V16.2.0で修正されているので、この構成が使えます。


**向いている用途:** SFパーツ、アクセサリー、器、ケース、パネルライン、リブ、放射状の穴パターン。



## 12b. 部品を融合させたくないとき（目・まぶた・殻）


### Separation 隣り合う部品を、溶けずに並べる

キャラクターの目とまぶた、貝殻と身体のように、**接しているが混ざってほしくない**部品を並べるワークフローです。

コツは1つだけです。

> **混ざらせたくない部品は、全部それぞれグループにする。**
> レイヤーに入れなかった形は、全体に対する「共通の接着剤」として働いてしまう。

1.  頭部などの本体を積みます。
2.  `Add Collection Divider` → `Layer Boundary` ON。ここで本体グループが閉じます。
3.  目とまぶたを積みます。まぶたを `Subtract` にすると、**まぶたは目だけを削り、本体には届きません**。
4.  `Add Collection Divider` → `Layer Boundary` ON、`Layer Blend` は `0.00`。目が本体にくっきり乗ります。
5.  殻を積み、同じように `Add Collection Divider` → `Layer Boundary` ON で閉じます。

| Stack例                             | 意味                              |
|-------------------------------------|-----------------------------------|
| 01 頭 A / Union                     | 本体                              |
| 02 頭 B / Union                     | 本体（互いにブレンドする）        |
| == Layer: Head == / Layer Boundary ON | ここまでが本体                  |
| 03 目 L / Union                     | 目                                |
| 04 目 R / Union                     | 目                                |
| 05 まぶた / Subtract                | 目だけを削る。本体には届かない    |
| == Layer: Eyes == / Layer Boundary ON | ここまでが目のグループ          |
| 06 殻 / Union                       | 殻                                |
| == Layer: Shell == / Layer Boundary ON | ここまでが殻のグループ         |

**つまずきやすい点:**

- **最初のレイヤーの `Layer Blend` は効きません。** 注ぎ込む先のシーンが空で、混ぜる相手がいないためです。効くのは2番目以降です。
- **本体をグループにし忘れると効きません。** 目だけをグループにしても、本体が自分のSmoothnessで後から混ざりにいきます。
- **Layer Boundaryは「くっつかなくなる」機能ではありません。** 合流は必ずUnionなので、重なっていれば繋がった1つの立体になります。止まるのは境目が溶けることだけです。目を独立したオブジェクトにしたい場合は、**ツリーを分けてください（12c を参照）**。V16.2.1 からパネルの `Tree` 行の `+` で追加できます。

**確認のしかた:** `Layer: Eyes` の `Layer Blend` を `0.00` と `0.50` で往復させます。目と本体の境目だけが変わり、目とまぶたの関係も殻も動かなければ、正しく組めています。



## 12c. 部品を別オブジェクトとして出す（V16.2.1）

### Separation 最初から別メッシュにする

12b は「溶けないように並べる」方法でした。こちらは**そもそも別のオブジェクトとして出す**方法です。
重なっていても繋がりません。合流自体が起きないためです。

> **1つのツリー = 1つの結果メッシュ。** 別オブジェクトにしたい単位でツリーを分けます。

1. 本体をいつもどおり積みます。
2. パネル最上段の `Tree` 行で **`+`** を押します。新しいツリーが増え、編集対象がそちらへ移ります。
3. 目をそのツリーに積みます。**本体には一切影響しません。**
4. `Tree` のドロップダウン、またはビューポートでパーツをクリックすれば、行き来できます。

| | 12b（Layer Boundary） | 12c（ツリー分割） |
|---|---|---|
| 結果メッシュ | 1つ | **部品ごとに1つ** |
| 重なった部分 | 繋がった1つの立体になる | **繋がらない** |
| 別マテリアルを割り当てる | メッシュ1つなので面倒 | オブジェクトが別なので普通に割り当てられる |
| 溶けない | ○ | ○ |

**速度について:** 分けると重くなりそうですが、逆です。1リクエストあたりのプリミティブ数が減り、
疎ブロック検出も効きやすくなります（216球・res128 で 1本 5053ms → 8本 1215ms）。本数の上限もありません。

### はめ合いを作る（Tree Reference）

蓋と瓶のように、**片方の形を相手に反映させたい**ときに使います。

1. 瓶のツリーを作ります。
2. `Tree` 行の `+` で蓋のツリーを作り、蓋を積みます。
3. 瓶のツリーに戻り、パーツを選んで **`Add Tree Reference`** を押します。
4. 出てきたEmptyの `Tree` に蓋のツリーを指定し、`Mode` を **`Subtract`** にします。

瓶に蓋の形のくぼみが空きます。**蓋を編集すると、くぼみも追従します。**

**つまずきやすい点:**

- **Emptyは動かさないでください。** 作成時は参照先の真上に置かれます。動かすとその分ずれます（意図的にずらしたいときには使えます）。
- **`Subtract` が厳密なのは、参照先が Union だけで組まれているときです。** 参照先が内部で Subtract や Intersect を使っていると、その箇所は近似になります。パネルに注意が出ます。`Blend` は常に厳密です。
- **参照の入れ子は1段まで。** 参照先がさらに別のツリーを参照していても、そこは辿りません。
- **ゴーストプレビューはアクティブなツリー1本だけです。** ただし**結果メッシュは全ツリーぶん常に見えています**ので、はめ合いの確認は結果メッシュで行ってください。

**確認のしかた:** 蓋のツリーで蓋のサイズを変え、瓶側のくぼみが追従するかを見ます。追従すれば正しく参照できています。


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
- 混ざらせたくない部品が、すべて自分のグループに入っているか
- Finalize後に戻りたい場合の履歴があるか




## 14. よくある判断の分岐

| 状況 | まず試すこと | 次に試すこと |
|----|----|----|
| 形が重い | Mesh icon OFF、Preview Quality Low | Resを下げる、Chunked Fallbackを使う |
| エッジが少し乱れる | Resを上げる、Live Normals | Post-Process GNでスムーズ調整 |
| Intersectが過去形状まで切る | 装飾のすぐ下にLayer Boundary付きDividerを置く | 本体側にもDividerを置いてレイヤーにする |
| Math Fieldが伸びて見える | Auto Match Scale | Axis X/Y/Zを手動微調整 |
| 色変更が重い | Apply Color Allで全体色を試す | 個別色はブレンド維持のため再計算を許容する |
| 案を残したい | Snapshot Mesh | 確定時のみFinalize |

Source basis: SDF.R V16.2.1 UI behavior and current implementation notes. Companion document: `SDF_R_V16_2_1_Comprehensive_User_Guide_JP.md` (第10章にLayer Boundaryの詳細、第0章にSDFツリーの詳細).
