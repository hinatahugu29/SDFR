# SDF.R V16.2.1 引継書

最終更新: 2026-09-09
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
d189f06  Give the mirror seam a way to round itself off      ← Mirror Blend
0f5832d  Note what actually shipped against the plan
be73456  Let one SDF tree reference another                  ← Phase 2
9da1afe  Let several SDF trees live in one scene             ← Phase 1
25464f9  Route each async mesh result back to the tree...    ← Phase 0
72c1eb8  Write down the multi-tree plan and the measurements
```

`d189f06` より前は Rust 無変更（`src/` は V16.2.0 と同一）でした。
**戻したいときの単位としてはここが切れ目**です。Mirror Blend だけ落として複数ツリーを先に出す、
という判断ができます。

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

1. **実機での目視確認**。`--background` ではパネルの `draw()` を通していないので、
   ツリー選択UI・Tree Reference のUI・Mirror Blend のスライダーは**まだ一度も描画されていません**。
2. **Mac / Linux の CI ビルド**。`d189f06` で Rust が変わったので、3プラットフォームとも必要です。
   `cross_platform_build_notes.md` のチェックリストを上から潰してください。
   特に「`register()` の版数 print を更新したか」は**過去2回落としている**項目です（今回は修正済み）。
3. **ドキュメント更新**。ユーザーガイド / UI Command Inventory に
   Add SDF Tree / Tree Reference / Mirror Blend が未記載です。

### B. 分かっている不具合・割り切り

1. **`sdf_show_result` を OFF にしてもメッシュがクリアされない**。
   `update_sdf_mesh` 冒頭の早期リターンが `clear_geometry()` の分岐より先に効くため、あの分岐は
   事実上デッドコードです。**V16.2.0 でも同じ**なので今回は触っていません
   （結果メッシュは `hide_viewport` で隠れるので実害は小さい）。
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
| ツリー単位の Finalize | いまの Finalize はアクティブツリーに対して動くが、複数ツリーを一括で焼く導線は無い | 小 |
| 元の要望（bake時のパーツ分離） | Phase 2 まで入ったので、**ツリーを分ければ結果メッシュが最初から別オブジェクト**になり、上位互換で満たされている。1本のツリー内をさらに分割したい場合のみ別途検討 | — |

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

## 8. 判断の記録（なぜそうしたか）

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
