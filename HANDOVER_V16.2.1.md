# SDF.R V16.2.1 引継書

最終更新: 2026-09-09（ヘッドレス検証・実機の現状・全ツリープレビューの検討記録を追記）
対象ブランチ: `feature/multitree-phase0`（master からの分岐）
前提バージョン: V16.2.0（リリース済み）

このドキュメントだけで現在地が分かるように書いてあります。
数字の根拠は [MULTITREE_MEASUREMENT_REPORT.md](MULTITREE_MEASUREMENT_REPORT.md)、
着手順の元になった計画は [MULTITREE_IMPLEMENTATION_PLAN.md](MULTITREE_IMPLEMENTATION_PLAN.md) にあります。

---

## 0. 3行で

- V16.2.1 では **複数のSDFツリーを同時に扱えるように**した（Phase 0/1/2）。ここまでは Python のみ。
- さらに **Layout Mirror の継ぎ目（折り目）を丸める `Mirror Blend`** を追加した。ここで初めて Rust / シェーダーを変更している。
- **未リリース**。実機のUI目視確認と Mac/Linux の CI ビルドが残っている。

---

## 1. リポジトリの構造（先に知っておくべきこと）

```
外部テスト/
├── Rust-GPU-SDF-V16.2.1/          ← Windows 作業ツリー。**gitignore されている**（手元のみ）
├── Rust-GPU-SDF-V16.2.1_MAC/      ← Git が追跡するのはこちら
├── Rust-GPU-SDF-V16.2.1_LINUX/    ← 同上（MAC と中身は完全に同一）
└── (各種ドキュメント)
```

`.gitignore` が `Rust-GPU-SDF-V*/` を無視し、`_MAC` / `_LINUX` だけを追跡する運用です。
**コードを直すときは Windows ツリーで作業し、終わったら `_MAC` / `_LINUX` へコピーしてコミット**します。
3ツリーの Python はバイト単位で一致していることが要求されます（`.gitattributes` が eol=lf を固定）。

Mac/Linux のバイナリは GitHub Actions が作ります。手順とハマりどころは
`cross_platform_build_notes.md` のセクション0チェックリストにまとまっています（過去に2回事故あり）。

### ビルドとテストの実際のコマンド

```bash
# Rust (Windows)
cd Rust-GPU-SDF-V16.2.1
P=$(py -3.11 -c "import sys; print(sys.prefix)")
export PYO3_PYTHON="$P/python.exe" PYO3_CROSS_LIB_DIR="$P/libs"
cargo build --release
cp target/release/rust_gpu_sdf.dll rust_gpu_sdf_addon/bin/win/rust_gpu_sdf.pyd
cp target/release/rust_gpu_sdf.dll rust_gpu_sdf_addon/rust_gpu_sdf.pyd
```

`lib.rs` だけの変更なら 3〜5 秒、wgsl を含めても 1 分程度です。
`build_sdf_addon.ps1` はビルド後に zip 化までやるので、検証中は `cargo build` だけ叩く方が速い。

ヘッドレステストは Blender の `--background` で動きます（GPU も Vulkan で動作します）。

```bash
"/c/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --factory-startup \
  --python test_xxx.py -- "E:\blender_addon\外部テスト\Rust-GPU-SDF-V16.2.1"
```

テストスクリプトは `tests_V16.2.1/` にあります。使い方と、それぞれ何を保証するかは
本書の「7. 検証の型」を参照してください。

---

## 2. V16.2.1 で何をしたか

### Phase 0: 非同期メッシュ結果を、要求したツリーへ返す（Python のみ）

Rust 側は `GPU_CONTEXT` が単一 Mutex、`IS_UPDATING` が単一フラグなので、
**同時に走る計算は常に高々1つ**です。だから「いま投げた要求の持ち主」を Python が1つ覚えておけば、
結果を正しい相手に返せます。当初計画にあった「Rust にリクエストIDを持たせる」は**不要でした**。

直した既存バグ:

| ID | 内容 | 場所 |
|---|---|---|
| B1 | `auto_domain` / `use_live_normals` が状態ハッシュに無く、トグルしても再メッシュされない | `engine.get_sdf_state_fingerprint` |
| B2 | 取得した1件の結果を**全出力オブジェクトに適用**していた（2本目を作ると同じ形になる） | `engine.sdf_mesh_timer` |
| B3 | 予約更新の再試行がループ内 `return` で先頭の出力しか処理しない | 同上 |
| B4 | 仕切りEmpty名のキャッシュが単一集合で、最後に同期したツリーに上書きされる | `engine.sync_sdf_stack` |
| B5 | 要求が拒否されたのに状態ハッシュだけ進む（**稀なレース**。当初「必ず踏む」と書いたのは誤り） | `engine.update_sdf_mesh` |
| — | V16.2.0 のコンソール版数表示が `V16.1.3` のままだった（`bl_info` は正しい） | `__init__.py` |

主な追加物: `_pending_updates` / `_last_mesh_requests` などを出力名キーの dict 化、`_inflight_owner`。

### Phase 1: 複数ツリーの成立（Python のみ）

ツリー解決を `engine.resolve_active_output()` に集約。優先順は
**アクティブが出力 → アクティブが属するツリー → シーンに記録されたツリー → 1本しか無ければそれ**。

> **この関数は絶対にデータを書かないこと。** パネルの `draw()` と オペレーターの `poll()` から
> 呼ばれるため、Blender の制約で描画中の変更は許されません。記録は
> `engine.set_active_output()` を execute から呼ぶ形に分けてあります。

- `"SDF_Collection"` のハードコード10箇所を `target_collection` 経由へ
- **命名は温存**。1本目は `SDF_Collection` / `SDF_Result` のまま、2本目以降が連番
  （`All Clear` が `"SDF_Result_"` などの文字列一致で削除対象を決めているため、リネームは危険）
- 新オペレーター `sdf.add_tree`（退避せずツリー追加） / `sdf.set_active_tree`
- `New SDF Workspace` はアクティブツリーだけを退避するよう変更
- `All Clear` / `Show Primitives` / depsgraph の関連判定が全ツリーを走査
- **プレビューはアクティブツリーのみ描画**（ドメインと対称がツリーごとの uniform なので合成不可。
  かつプレビューは毎フレーム走る唯一のコスト）

### Phase 2: ツリー参照 `TREE_REF`（Python のみ）

Curve Sync プロキシと同じ作りの Empty（`SDF_TreeRef_NNN`）をスタックに置き、別ツリーを取り込みます。
Empty を動かすと参照先がずれ、作成時は参照先の上に置かれるので動かさなければ一致します。

そのために `update_sdf_mesh` に直書きだった走査ループを
**`engine.collect_stack_primitives()` として切り出し**ました（参照先のスタックに同じ走査をかけるため）。
取り込む側の逆行列を渡すので、参照先の形はそのまま取り込む側のローカル空間に入ります。

| モード | 実装 | 正確さ |
|---|---|---|
| Blend | レイヤー機構でひとかたまりの Union | **厳密**（レイヤー合流は元々 union 固定） |
| Subtract | 参照先の各プリミティブを個別に減算 | 参照先が Union だけなら**厳密**。内部で Subtract/Intersect を使っていると近似（UIで注意表示） |

- 状態ハッシュに参照先のハッシュを畳み込み（visited セットで循環防止）。**これが無いと参照先を編集しても更新されません。**
- 参照の入れ子は1段まで（参照先の参照は辿らない）
- `SdfPrimitive` の `operation` / `smoothness` は Python から書き換えられない（pyo3 の get/set が付いているのは `layer_*` だけ）ので、減算の上書きは**生成時**に差し込んでいます

### ウォームアップ中にパネルが開いてしまう問題（Python のみ）

`is_gpu_ready` は **シーンのプロパティなので .blend に保存されます**。
エンジン初期化済みの状態で保存したファイルを開くと、次回起動時、
まだパイプラインをコンパイルしている最中でもパネルのガードが外れていました
（コンソールに `Compiling MC Pipeline...` が流れているのに操作できる）。

対策:
- ウォームアップ完了までは `init_checker` が毎チェックでフラグを False に落とす
- `load_post` ハンドラを追加し、ファイルを開いたときにモジュール側の実状態へ揃える

> **`is_gpu_available()` をパネルから呼んではいけません。** この関数は `GPU_CONTEXT` を
> ロックしますが、初期化スレッドはコンパイル中ずっとそのロックを保持します。
> `draw()` から呼ぶと、まさに守りたい期間ちょうどUIが固まります。

なお、ウォームアップ中に操作しても壊れはしません。メッシュ要求は別スレッドで走り、
同じ Mutex を待ってからコンパイル完了後に実行されます（遅れて完了する）。
それでも「準備できているように見える」のは直すべき、という判断です。

### Mirror Blend（Rust + WGSL + GLSL + Python）

**ここだけ Rust/シェーダー変更を含みます。** 詳細は次章。

---

## 3. ミラーの継ぎ目の問題（今回の主題）

### 何が起きていたか

プリミティブ側の Layout Mirror は**空間の折り返し**です:

```wgsl
if ((mask & 4u) != 0u) { lp.z = abs(lp.z) - m_offset; }   // common.wgsl
```

`abs()` で折り返すと、2つのコピーは必ず**ハードな min（通常の Union）**で合わさります。
そして **プリミティブの Smoothness はこの継ぎ目に効きません**。
折り畳まれた空間の中に形は1つしか無く、ブレンドすべき相手が存在しないためです。

実測（球 r=0.6 / offset 0.4 / res 128、隣接面の角度が30度を超える辺を数える）:

| | 折れ目の辺 | 最大角 |
|---|---|---|
| プリミティブの Mirror（折り返し） | 44本 | **84.1°** |
| 実体2つ + Smooth Union | 0本 | 8.5° |
| Collection Divider の Mirror | 0本 | 8.5° |

メッシュ全体で鋭い辺はこの44本だけ、つまり**陰影の問題ではなく形そのものの折れ目**でした。

### 入れた対策（A案: 両側評価 + 結合）

新プロパティ **`mirror_blend`（Mirror Blend、既定 0.0）**。

- `0` のときは**従来と完全に同じ経路**を通ります（既存ファイルの見た目は変わりません）
- `> 0` のとき、折り返さずに**有効な軸ぶん側を分けて評価**し、
  プリミティブのブレンド形状（`blend_profile` / `chamfer_smooth`）で結合します

結果（同条件）:

| | 頂点数 | 折れ目 | 最大角 |
|---|---|---|---|
| Mirror Blend = 0.0 | 1846 | 44本 | 84.1° |
| Mirror Blend = 0.3 | 1782 | **0本** | **8.5°** |
| 実体2つ + Smooth Union（正解） | 1782 | 0本 | 8.5° |

**頂点数も最大角も「実体2つの Smooth Union」と完全に一致**しました。近似ではなく厳密です。
2軸（X+Z）同時でも折れ目ゼロを確認しています。

コスト: res192・1軸で **31.5ms → 53.9ms（1.71倍）**。理屈どおり評価が2倍になるぶんです。
軸を増やすと 2^軸数 倍になります。

### 変更したファイル

| ファイル | 内容 |
|---|---|
| `src/common.wgsl` | `evaluate_layout_side(..., msign)` を追加し、`evaluate_layout` は薄いラッパに。`evaluate_shape_mirrored()` が両側評価と結合を行う。呼び出し2箇所を差し替え |
| `src/lib.rs` | CPU 経路も同様に。`get_scene_sdf_with_color` の中に直書きだったプリミティブ1個ぶんの評価を `eval_primitive_from_local()` に切り出し、`eval_primitive_mirrored()` から側ごとに呼ぶ。`SdfPrimitive` に `mirror_blend` を追加し、GPU 側は `layer_params` の**空いていた第4成分**に載せた（構造体サイズは不変） |
| `rust_gpu_sdf_addon/shader.py` | プレビュー用 GLSL。**近似実装**（後述） |
| `rust_gpu_sdf_addon/handlers.py` | プレビューのプリミティブテクスチャ 17行目の第4成分に `mirror_blend` を載せる |
| `rust_gpu_sdf_addon/properties.py` | `mirror_blend` プロパティ |
| `rust_gpu_sdf_addon/engine.py` | `SdfPrimitive` 生成時に渡す + 状態ハッシュへ追加 |
| `rust_gpu_sdf_addon/ui.py` | Mirror Settings に Mirror Blend を表示。0 のときは注意書き |

### 既知の割り切り

1. **プレビューは近似**です。プレビューの GLSL は「1形状につき1評価」の構造で、
   最終メッシュと同じ両側評価をするにはループ全体の作り替えが要ります。
   いまは `sqrt(z*z + e)` で折り返しを丸める近似を入れており、
   **継ぎ目が丸まった見た目にはなりますが、丸まり方は最終メッシュと厳密には一致しません。**
2. **Radial と Grid は未対応**です。これらも領域繰り返しなので同じ折れ目が出ます
   （実測: Radial 338本/77.2°、Grid 99本/69.9°）。
   セル境界をまたいでブレンドするには隣のセルも評価する必要があり、
   ミラーの「2つの側」より一般化が必要です。
3. **仕切り（Collection Divider）側の Mirror/Radial/Grid は元から継ぎ目が出ません。**
   こちらは Python でコピーを実体化する経路なので、普通の Smooth Union で繋がります。
   代償は評価コストが個数に比例すること（領域繰り返しは個数に依らず一定）。

---

## 4. コミット一覧（このブランチ）

```
7de57ef  Name the tree behind each mesh request, and let ...  ← ログ強化 + B-1 修正
dd43842  Finalize one tree without shutting down the others
8873a9d  Make the tree dropdown actually change the tree
70fdd22  Switch the ghost preview as soon as the active tree does
0b7559e  Record the warm-up guard finding in the handover
8a78412  Stop a saved file from unlocking the panel before the engine is up
e0c22f1  Keep the V16.2.1 verification scripts in the repo
b0d0426  Write the V16.2.1 handover
d189f06  Give the mirror seam a way to round itself off      ← Mirror Blend
0f5832d  Note what actually shipped against the plan
be73456  Let one SDF tree reference another                  ← Phase 2
9da1afe  Let several SDF trees live in one scene             ← Phase 1
25464f9  Route each async mesh result back to the tree...    ← Phase 0
72c1eb8  Write down the multi-tree plan and the measurements
```

`d189f06` より前は Rust 無変更（`src/` は V16.2.0 と同一）でした。
**戻したいときの単位としてはここが切れ目**です。Mirror Blend だけ落として複数ツリーを先に出す、
という判断ができます。`d189f06` 以降は Python のみなので、この性質は今も保たれています。

`dd43842` / `8873a9d` / `70fdd22` の3件は、いずれも**複数ツリーにして初めて壊れた**箇所です
（Finalize が他ツリーを巻き添えにする / ドロップダウンが実際には切り替わらない /
ゴーストが前のツリーのまま残る）。後ろ2件はUI経路なので、同種の残りがまだある前提でいてください。

`7de57ef` は2つの変更を1コミットに含んでいます（分けるべきでしたが、コミット後に気付きました）。
ログ強化は診断のみで挙動を変えません。同居している B-1 修正だけを戻したい場合は、
`engine.py` の早期リターン内にある `clear_geometry()` の塊を消せば元の挙動に戻ります。

---

## 5. 性能について分かっていること

RTX 3060 / Blender 5.1.1 background / MC / weld なし での実測。

- 評価コストの支配項は**解像度ではなくプリミティブ数**。表面積を固定した対照実験で、
  res 128 なら 1プリミティブあたり約 4.2ms のほぼ線形。res を 32→256 に上げても 14.6ms→101.7ms
- **同じモデルを N 本のツリーに分割すると、合計コストはむしろ下がる**
  （216球、res128: 1本 5053ms → 4本 1904ms → 8本 1215ms）。
  1リクエストあたりのプリミティブ数が減ることと、疎ブロック検出が効くため
- ツリーが増えるだけのアイドルコストは小さい（16本で depsgraph イベントあたり 0.74ms）
- リクエスト1回の下限は約 3ms

つまり**ツリー数の上限を設ける性能的な理由はありません**。

---

## 6. 残作業（優先度順）

### A. リリース前に必須

1. **実機での目視確認**。2026-09-09 に実機で一通り触り、**現時点で問題は出ていません**。
   ただし**確認できたのは通常の操作範囲までで、エッジケースには手が回っていません**。
   「問題なし」ではなく「見た範囲では問題が出ていない」が正確なところです。
   手順と合格基準は「8. 実機確認の手順」にまとめてあります。
   **ロジック側は同日にヘッドレス9本すべてグリーン**を確認済みです。
2. ~~**Mac / Linux の CI ビルド**~~ → **完了（2026-09-09）**。
   ワークフロー `build-sdf-r-v16-2-1-cross-platform.yml` を追加し、両ジョブとも成功（1分26秒）。
   セクション6の事前検証・セクション6-Bの配布物検証ともに ALL OK。
   成果物は `Other_OS/V16.2.1/` に配置済み（gitignore配下）。
   `macos-14` / `ubuntu-22.04`、3ツリーの Python はバイト単位で一致、版数 print の残骸なし。
   **なお、セクション6の検証スクリプトはファイル数の期待値が `34` 固定ですが、V16.2.0 の時点で
   既に 35 です。**前バージョンの実数と比較する形に直して流しました。次回も同様に。
3. ~~**ドキュメント更新**~~ → **完了（2026-09-09）**。作成物は以下。

   | 種別 | ファイル |
   |---|---|
   | リリースノート | `RELEASE_NOTES_V16.2.1.md` / `.html` |
   | 告知メール（英/和） | `UPDATE_ANNOUNCEMENT_V16.2.1.md` |
   | SNS文面（和） | `SNS_POSTS_V16.2.1.md` |
   | Superhive 掲載 | `BlenderMarket_Documentation_V16.2.1.html` / `BlenderMarket_Product_Description_V16.2.1.html` |
   | ユーザーガイド | `SDF_R_V16_2_1_Comprehensive_User_Guide_JP.md`（第4-B章を新設、第15章に Mirror Blend） |
   | コマンド棚卸し | `SDF_R_V16_2_1_UI_Command_Inventory.md` / `.html`（第0章 Tree、第8-B章 Tree Reference） |
   | ワークフロー例 | `SDF_R_V16_2_1_Workflow_Examples.md` / `.html`（12c を新設） |

   看板は**「ツリー分割 = 1つのアドオンから別々のオブジェクトを作れる」**に統一しました。
   同じ報告者に V16.1.3 / V16.1.4 / V16.2.0 の3回「SDF出力を分けるしかない」と回答してきた、
   その要望への回答にあたるためです（`REPLY_TO_REPORTER_*.md` 参照）。

   iGPU の warm-up（194秒）も各ドキュメントに反映済みです。
   なお無印の `BlenderMarket_Documentation.md` / `_Product_Description.md` は5〜6月時点の
   旧ファイルで、V16.2.0 でも同期していない運用のため触っていません。

### B. 分かっている不具合・割り切り

1. ~~`sdf_show_result` を OFF にしてもメッシュがクリアされない~~ → **`7de57ef` で修正済み**。
   V15.9.9.4 で入った早期リターンが `clear_geometry()` の分岐より先に効き、あの分岐が
   到達不能になっていました（V16.2.0 も同じ）。クリアは早期リターンより前にしか置けないので
   そちらへ移しています。**あわせて状態ハッシュを捨てる必要があります** —
   捨てないと ON に戻したとき「変化なし」と判定されてメッシュが空のまま残ります。
2. プレビューのミラー近似（3章）。
3. Radial / Grid の折れ目（3章）。

### C. 作業候補（やるとしたら）

| 候補 | 内容 | 規模の見立て |
|---|---|---|
| Radial / Grid のブレンド | 隣接セルも評価して結合。ミラーと同じ考え方の一般化 | シェーダー中。評価コストは 2〜4倍 |
| プレビューの厳密化 | GLSL のループを「1プリミティブ = 1関数」に作り替え、`evaluate_shape_mirrored` 相当を入れる | 中。プレビュー全体の回帰確認が要る |
| ツリー参照の Intersect | いまは Blend / Subtract のみ。グループ単位の演算には `union_layer_accum` に演算子を持たせる必要がある | シェーダー変更。CPU/GPU/プレビューの3箇所 |
| ツリー参照の Clearance | 印刷公差ぶん相手を膨らませて引く。距離場の一律膨張（`d - eps`）の口が `SdfPrimitive` に無い | 小〜中（フィールド追加。空きスロットは `layer_params.w` を使い切ったので次は要検討） |
| 参照ツリーの表示 | Phase 2 で参照した相手が見えないと、はめ合いを作りにくい。参照先だけ半透明で重ねる案 | 中。プレビューの複数パス化と関係する |
| **全ツリープレビューのトグル** | 常時はアクティブ1本、必要なときだけ全ツリーのゴーストを出す。**やるかもしれない程度の候補**（下の補足を参照） | 中。Python のみで可能 |
| ツリー単位の Finalize | いまの Finalize はアクティブツリーに対して動くが、複数ツリーを一括で焼く導線は無い | 小 |
| 元の要望（bake時のパーツ分離） | Phase 2 まで入ったので、**ツリーを分ければ結果メッシュが最初から別オブジェクト**になり、上位互換で満たされている。1本のツリー内をさらに分割したい場合のみ別途検討 | — |

#### 補足: 全ツリープレビューのトグル（2026-09-09 に可否だけ検討した記録）

**結論: 実装可能。シェーダー変更なし、Python のみ。ただし V16.2.1 には入れない。**

2章で「プレビューはアクティブツリーのみ」とした理由は、ドメインと対称マスクがツリーごとの
uniform なので**1パスでは**混ぜられない、というものだった。**パスをツリーごとに分ければ**
各パスが自分の uniform を持てるので、この制約は消える。

障害は2つ:

1. **キャッシュが1本ぶんしかない。** `handlers.py` の `_cached_prim_tex` / `_cached_prim_count` /
   `_cached_domain_size` / `_cached_sym_mask` / `_cached_base_steps` / `_cached_output_name` /
   `_cached_curve_guides` が、いずれも「いま描いている1本」を持つモジュール変数。
   出力名キーの dict にする必要がある。**Phase 0 で `_pending_updates` などにやったのと同じ形**。
   ここが単一ツリー経路（既存の全ユーザーが通る道）に触る唯一の危険なので、
   `test_preview_switch` と `test_tree_switch_ui` が変更前後で緑のままであることを合格条件にする。
2. **重なったときの前後関係。** レイマーチの GLSL は `gl_FragDepth` を書いておらず、
   描画は `depth_test_set('ALWAYS')` + アルファブレンド。つまり**合成順 = 描画順**で、
   複数を重ねると「後に描いた方が手前」になる。離れて並ぶツリー（想定される主用途）では
   問題にならないが、重なるツリー（Tree Reference のはめ合い）では前後が嘘になる。
   アクティブツリーを最後に描けば、少なくともアクティブが手前に来る。

深度を正しくするなら GLSL でヒット距離を `gl_FragDepth` に書く必要があり、それは
**シェーダー変更＝3プラットフォームのビルドやり直し**を意味する。実物のメッシュとの前後関係も
正しくなるという副産物はあるので、やるなら「プレビューの厳密化」と合流させるのが自然。

コストはフレームあたり**ツリー数に比例**する（5章のとおりプレビューは毎フレーム走る唯一のコスト。
メッシュ生成が分割で安くなるのとは逆に、素直に N 倍）。既定 OFF の一時トグルという形は、
この N 倍を任意かつ一時的にするので、設計としてはこの弱点への答えになっている。

**V16.2.1 に入れなかった理由:**

- **製品として欠けていない。** 各ツリーの結果メッシュは実体のあるオブジェクトなので常に全部見える。
  1本に絞られているのはゴーストプレビュー（編集中のライブ表示）だけで、欠落ではなく利便性の問題。
- **要望はまだ予測。** マルチツリー自体が未出荷なので誰も使っていない。使われていない機能から
  派生した要望を先回りすると外しうる。実際、はめ合いを作りたい人が本当に欲しいのは
  上の「参照ツリーの表示」の方かもしれず、要件が違う。
- **先送りしても安いまま。** Python のみなので、要望が来てから出しても CI ビルドは要らない。
  この安さは先送りで失われない。

**着手を判断する条件**: 実際に要望が来たとき、または自分で使っていて不便を感じたとき。
どちらも予測ではなく実データなので、それなら十分な根拠になる。

---

## 7. 検証の型（テストを作り直すとき）

ヘッドレスで addon を読み込み、タイマーを手で回す形です。`--background` では
`bpy.app.timers` が回らないので、`engine.sdf_mesh_timer()` を自分で呼びます。

```python
import bpy, sys, os, time
sys.path.insert(0, r"E:\blender_addon\外部テスト\Rust-GPU-SDF-V16.2.1")
import rust_gpu_sdf_addon as A
A.register()
from rust_gpu_sdf_addon import engine
from rust_gpu_sdf_addon._native import rust_gpu_sdf as R
R.init_gpu(os.path.join(os.path.expanduser("~"), "sdf_cache.bin"), False)   # 初回は数十秒

def pump(n=800):
    for _ in range(n):
        if engine.sdf_mesh_timer() is None:
            return
        time.sleep(0.005)

# ツリーを作る: コレクション + is_output なオブジェクト + target_collection
# プリミティブは空メッシュの Object に sdf_props.is_primitive / shape_type を立てるだけでよい
# 変更後は engine._last_state_hashes.pop(out.name, None) してから update_sdf_mesh(out); pump()
```

判定に使った指標:

- **折れ目**: `bmesh` で `edge.calc_face_angle()` が 30度を超える辺を数える。
  ミラー面付近だけ数えると原因の切り分けになる
- **体積**: `bmesh.calc_volume(signed=False)`。ツリー参照の Blend / Subtract が
  和集合・差集合として正しいかは、頂点数ではなく体積で見る
  （実測値: 半径1.5の球単体 14.05 / 半径1.0を Blend 15.14 / Subtract 10.95）
- **状態ハッシュ**: `engine.get_sdf_state_fingerprint(out, depsgraph)` の変化。
  「プロパティを変えたのに再メッシュされない」系のバグはこれで直接確認できる

---

## 7.5 ログからどこまで分かるか

`Rust Debug: Starting SDF generation` は Rust 側の出力で、**どのツリーの要求か書いていません**。
つまり Phase 0 の核心（結果を要求した本人に返す）は、既定のログでは検証できません。
同じ内容のメッシュ生成が何度も並ぶログを見たとき、それが「2本が別々に更新されている」のか
「1本が空回りしている」のかは区別がつきません。

`7de57ef` で、要求側と受け取り側の両方に持ち主を出すようにしました。
**Nパネルの診断トグル "Mesh" を ON** にすると出ます（既定は OFF）。

```
[SDF-Debug/Mesh] request  <- owner=SDF_Result algo=MC res=48 prims=5
[SDF-Debug/Mesh] result   -> owner=SDF_Result
```

`request` と `result` の owner が食い違っていたら Phase 0 が壊れています。
もう1つ注意して見るべきは次の行で、**持ち主が見つからず出力が1本しか無いときに
黙って拾い上げる経路**です。ここが出るときは何かがおかしいと思ってください。

```
[SDF-Debug/Mesh] result   -> adopted by the only output 'SDF_Result' (owner=... not found)
[SDF-Debug/Mesh] result   -> DISCARDED (owner=... not found, 2 outputs in scene)
```

---

## 8. 実機確認の手順（残作業A-1）

> **現状（2026-09-09）**: 実機で一通り操作し、**問題は出ていません**。
> **A-2（CIビルド）と A-3（ドキュメント）は完了済みで、残っているのはこの章だけです。**
> ただし見たのは**通常の操作範囲まで**で、エッジケース（多数ツリー、参照の入れ子、
> 極端な解像度、操作中の連打、undo/redo をまたぐ切り替えなど）には**まだ手が回っていません**。
> 「検証済み」ではなく「見た範囲では問題なし」として扱ってください。

ロジックはヘッドレスで押さえてあるので、ここでは**描画とUI操作にだけ**集中します。

> **必ずコンソールを開いたまま操作してください。** パネルの `draw()` で出た例外は
> 画面上ほとんど無症状で、コンソールにしか出ません。したがって下の1・2・3・5は
> 実質「**トレースバックが出ないこと**」が合格基準です。

| # | 何を | どうやって | 合格基準 |
|---|---|---|---|
| 1 | ツリー選択ドロップダウン | ツリーを2本作り、往復で切り替える | 選んだ側が Parts / The Stack に反映される。トレースバックが出ない |
| 2 | プレビュー追従 | 切り替えるたびにゴーストを見る | アクティブツリー側のゴーストだけが出る |
| 3 | Tree Reference のUI | `Add Tree Reference` で参照を作り、Blend / Subtract を切り替える | 両モードのUIが出る。Subtract のとき近似の注意書きが出る |
| 4 | Mirror Blend スライダー | Layout Mirror を有効にし、0 → 0.3 へ動かす | 0で継ぎ目が角張り、上げると丸くなるのが**見て分かる**。0のとき注意書きが出る |
| 5 | `draw()` がデータを書いていないこと | 上を一通り操作する | `Writing to ID classes in this context is not allowed` が**一度も出ない** |

5が最重要です。`resolve_active_output()` は `draw()` と `poll()` から呼ばれるため
**データを書いてはいけない**（1章の注記）という制約があり、これを破ったときのエラーは
ヘッドレスでは絶対に出ません。実機確認の主目的はここだと思ってください。

4だけは目視が本質です。他は数値でヘッドレスに押さえてあります。

---

## 9. 判断の記録（なぜそうしたか）

- **命名を変えなかった**: All Clear が名前の文字列一致で削除対象を決めており、
  リネームは「消してはいけないものを消す」方向に壊れうるため。得られるのは見た目の統一だけ。
- **プレビューを1本に絞った**: ドメインと対称がツリーごとの uniform で合成できないうえ、
  プレビューだけが毎フレーム走るコスト。評価が分割で 0.24〜0.59倍に下がるのとは逆に、
  プレビューの複数パス化は素直に N 倍になる。
- **ツリー数に上限を設けなかった**: 常時コストが本数に比例しないことを実測で確認したため。
- **Mirror Blend の既定を 0 にした**: 既存ファイルの形が勝手に変わらないようにするため。
  ミラーを使っている既存ユーザーは、開いた瞬間に形が変わると困る。
- **Intersect と Clearance を見送った**: 知っていて間違っているものを出すより外した。
  どちらもシェーダー変更が必要で、Mirror Blend とは別の作業単位。
