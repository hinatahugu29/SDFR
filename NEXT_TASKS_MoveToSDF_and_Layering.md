# 次回着手案 — Move to SDF の不具合修正と Layer Boundary の発見性

起票: 2026-09-04 / 契機: V16.1.3 利用者からの報告（[REPLY_TO_REPORTER_V16.1.4_MoveToSDF_Smoothing.md](REPLY_TO_REPORTER_V16.1.4_MoveToSDF_Smoothing.md)）

対象コードは `Rust-GPU-SDF-V16.1.3/rust_gpu_sdf_addon/`。着手時は最新版へ読み替えること。

---

## A. Move to SDF: 出力オブジェクトの選択が不定（バグ）

`SDF_OT_move_to_sdf_collection.execute`（operators.py:269）は行き先コレクションを

```python
for o in context.scene.objects:
    if p and p.is_output and p.target_collection:
        target_col = p.target_collection
        break
```

で決めている。`scene.objects` の**先頭ヒット**なので、シーンに SDF 出力オブジェクトが複数あると
意図しない側へ入る。順序は Blender 内部の都合で決まるため再現性もない。

**方針**: 他オペレーターと同じく `get_sdf_output_obj(context)`（operators.py:52 付近、アクティブ
オブジェクト優先）を使う。解決できないときは現行のフォールバック（`SDF_Collection` 名引き）を残す。

## B. Move to SDF: users_collection のイテレート中変更（バグ）

```python
for col in obj.users_collection:
    col.objects.unlink(obj)
```

`users_collection` は評価のたびに再構築されるタプルだが、unlink しながら回すと取りこぼす場合がある。
複数コレクションに属するオブジェクトで元のリンクが残り、SDF コレクションと二重所属になる。

**方針**: `for col in list(obj.users_collection):` としてスナップショットを取ってから unlink。

## C. Move to SDF: shape_type 推定が名前依存（設計上の限界）

現状は `obj.name.lower()` に box/cube/torus/cylinder を含むかだけで判定し、残りは全部 `sphere`。
`shape_type` enum（properties.py:260）にメッシュ系の項目が無いため、任意メッシュは原理的に取り込めない。

**短期案（次回スコープ）**:
- 判定できなかった場合に `self.report({'WARNING'}, ...)` を出し、球にフォールバックしたことを明示する。
  現状は無言で球になるため「ボタンが壊れている」と受け取られる。
- 名前ではなく、可能な範囲でメッシュ形状から推定する（頂点数・バウンディングボックス比など）。
  ただし誤判定のほうが害が大きいので、優先度は警告表示より下。

**長期案（別タスク）**: mesh SDF シェイプの導入。Rust 側の `SdfPrimitive` は既に
`vertices` / `indices` を受け取れる（src/lib.rs:65 のシグネチャ）ので、BVH 経路の実態調査から入る。
これは規模が大きいので本タスクには含めない。

## D. Layer Boundary の発見性（UX）

機能自体は実装済みで正しく動く。divider 行の `is_layer_boundary`（ui.py:411、Rust 側は
src/lib.rs:929 付近の `union_layer_into_scene`）。だが

- 名前から効果が読み取れない（「グループ内だけで評価してから一度だけ Union する」＝**外側とブレンドしない**）
- スタック行のアイコン（ui.py:64）だけでは ON/OFF の意味が伝わらない
- 合流時のブレンド強度が**そのレイヤー先頭プリミティブの Smoothness** から来る、という規則がどこにも書かれていない

利用者が「Smoothness を下げる」で解こうとして行き詰まる典型パターンになっている。

**方針**:
1. `is_layer_boundary` の description を、効果が伝わる文面に書き換える
   （例: "Keep this group from blending with anything outside it. The group is evaluated on its
   own and unioned into the scene once."）
2. Layer Boundary が ON のとき、合流に使われる Smoothness がどのプリミティブ由来かをパネルに表示する。
   できれば divider 自身に合流用の Smoothness を持たせ、先頭プリミティブ依存をやめるのが本筋
   （※挙動変更になるため既存ファイルへの影響を要検討）
3. ドキュメントに「目・まぶた・殻を混ざらせない」ワークフローを図付きで追加する。
   `SDF_R_V16_1_1_Comprehensive_User_Guide_JP.md` 系と Workflow Examples の両方。

---

## 着手順の推奨

B → A（どちらも数行、リグレッションリスクが低い）→ C の警告表示 → D-1/D-3 → D-2（挙動変更を伴うので単独で）

---

# 追記（2026-09-04）: Layer Boundary の実装調査結果

報告者スクリーンショット（Collection 1 / Collection 2 で分けても球同士が干渉して見える）を受けて
実装を追った結果、**Layer Boundary は「ブレンドを止める機能」ではない**ことが確定した。
以下4件はいずれも実装事実。GPU 側（src/common.wgsl:724 以降 / 783 以降）と CPU 側
（src/lib.rs:702 以降）のロジックは一致しているので、プレビューと確定メッシュの乖離ではない。

## L-1. レイヤー合流は smooth union（＝干渉は止まらない）【最重要】

`union_layer_into_scene`（src/lib.rs:681）は

```rust
let k = k_in.max(0.0001);
scene.d = apply_profile_union_cpu(scene.d, layer.d, profile, k, cs);
```

で、**k は素通しの smooth union**。この `k` は呼び出し側（src/lib.rs:929-936）で

```rust
current_layer_id = prim.layer_id;
layer_k = prim.smoothness.max(0.0001);
```

＝**そのレイヤーで最初に現れたプリミティブの Smoothness** から取られる。既定値は 0.2 なので、
Layer Boundary を ON にしただけでは「グループがひと塊になって、その塊が外側と 0.2 でブレンドする」
という結果にしかならない。利用者から見た干渉は残る。

なお `apply_primitive_to_accum`（src/lib.rs:630）は accum 未初期化時に smoothness を使わないため、
先頭プリミティブの Smoothness はグループ内部のブレンドには影響しない。実質「レイヤー合流専用の値」に
なっている。**この二重用途が最大の分かりにくさの原因。**

**方針**: divider（`SDF_StackItem`）に合流専用の `layer_smoothness` / `layer_blend_profile` を追加し、
`layer_k` をそこから取る。既定値は 0.0（＝硬い境界）が要望に素直。既存ファイルは先頭プリミティブ由来の
値で初期化して挙動を保つか、破壊的変更として明示するかを要判断。

## L-2. Layer Boundary が効く範囲が divider の「下」で、他の divider 機能と逆

engine.py:1005-1019:

```python
if item.is_layer_boundary:
    _finalize_group_elements(working_group, ...)   # divider より上の要素をここで確定
    working_group = []
    active_layer_id = next_layer_id                # 以降（＝下）の要素が新レイヤー
    next_layer_id += 1
```

`working_group` は divider より**上**（低インデックス）に溜まった要素で、divider のレイアウト展開・
親子付け（engine.py:1531 以降の `sync_...` も同様）はこの「上のグループ」を対象にする。
ところが `active_layer_id` は divider より**下**の要素に付く。**同じ divider の設定が、機能ごとに
別のグループへ効いている。**

UI 上は divider 行がフォルダ見出しとして上に出る（ui.py:64）ため、利用者の直感は「下」寄り。
どちらへ揃えるかは要設計判断だが、**現状の食い違いは必ず解消する**こと。

## L-3. レイアウト付き divider で Layer Boundary を ON にするとレイアウトが消える【バグ】

engine.py:1005-1014、`is_layer_boundary` 分岐は `working_group`（**未展開**）を確定するのに対し、
`start_new_group` 分岐は `expanded_group`（レイアウト展開済み）を確定する。
`is_layer_boundary` が先に評価されるため、Radial / Grid 等のレイアウトを持つ divider で
Layer Boundary を ON にすると**レイアウト展開が丸ごと捨てられる**。

**方針**: `_finalize_group_elements(expanded_group, ...)` に修正。単純な取り違えに見えるが、
既存ファイルの見た目が変わる可能性があるためリリースノートに明記すること。

## L-4. レイヤーは次の divider で暗黙に終わる

engine.py:1012 / 1018 のとおり、`start_new_group` でも入れ子でも `active_layer_id = 0` に戻る。
つまりレイヤーは「次の divider まで」しか続かず、UI にその手掛かりが無い。
利用者が入れ子構造とレイヤーを併用すると、意図せずレイヤーが切れる。

**方針**: 少なくともスタック行にレイヤー範囲を示すインジケータを出す。L-2 の設計判断とセットで検討。

---

## 優先度の見直し

L-1 と L-3 は**機能が要望どおりに働かない直接原因**なので、当初 D 節に書いた「発見性の改善」より上。
推奨順:

1. **L-3**（レイアウト消失。数行の取り違え修正、影響も限定的）
2. **L-1**（divider に合流用 Smoothness を持たせる。既定 0.0。要リリースノート）
3. B → A（Move to SDF の小バグ2件）
4. **L-2**（効く範囲の統一。設計判断を伴うので単独リリース推奨）
5. L-4 / C の警告表示 / D-1・D-3 のドキュメント整備

---

# 決定（2026-09-04）: `layer_smoothness` の既定値は 0.0

L-1 で divider に追加する `layer_smoothness` の既定値を **0.0（硬い境界）** とする。
意図的にレイヤーを外側と馴染ませたいときだけ 0.2 等へ上げる運用。

**混同しやすい点（レビュー中に実際に起きたので明記）**: これは**プリミティブの
`smoothness`（properties.py:352, default=0.2）の既定値を変える話ではない**。プリミティブ側の
既定値も、`_find_smoothness_source`（operators.py:154）による次プリミティブへの継承も一切変更しない。
新設するのは divider（`SDF_StackItem`）が持つ「レイヤーをシーンへ1回だけ合流させるときの k」専用の
別プロパティで、Layer Boundary が ON の divider でのみ使われる（既定 OFF なので通常操作への影響なし）。

**継承機構では代替できない理由**: 現状 `layer_k` は「そのレイヤーで最初に現れたプリミティブの
`smoothness`」（src/lib.rs:935）＝継承で自動伝播してきた 0.2 が入る。一方
`apply_primitive_to_accum`（src/lib.rs:630）は accum 未初期化時に smoothness を使わないため、
**先頭プリミティブの Smoothness はグループ内部の見た目には効かない**。数値を動かしても内部は変わらず
外との合流だけが変わる、という一人二役が報告者の行き詰まりの原因。分離すれば継承機構は本来の
役割に専念できる。

既定 0.0 により既存ファイルの見た目が変わりうる（Layer Boundary を ON にしていたファイルのみ）。
バージョンアップ用の移行処理は入れず、リリースノートに明記する方針。

---

# 実装状況（2026-09-04）

- **L-3 済** — `_finalize_group_elements(expanded_group, ...)`。commit `6c31f03`
- **A / B / C 済** — Move to SDF。`get_sdf_output_obj` 経由 / `list(users_collection)` /
  球フォールバック時の WARNING。commit `6c31f03`
- **L-1 済** — divider に `layer_smoothness` / `layer_blend_profile` / `layer_chamfer_smooth` を追加
  （既定 0.0）。CPU（lib.rs:954）と GPU 両パス（common.wgsl の fast / slow）を書き換え。
  GpuPrimitive / struct Primitive に `layer_params` を追加。commit `2d09aa1`
- **L-2 済** — レイヤーを仕切りより「上」のグループに掛けるよう統一（レイアウト展開・親子付けと同じ向き）
- **L-4 解消** — 上のグループに閉じるようになったため、レイヤーが下へ伝播して次の仕切りで暗黙に切れる
  現象自体が無くなった。インジケータは不要と判断
- **D-1 済** — `is_layer_boundary` の description を書き換え。パネルに Layer Merge 欄を追加

## 検証済み

- `cargo build --release` 通過。`test_wgsl_all`（今回追加。gpu.rs が実行時に連結するのと同じ
  4ファイルを naga で検証する。既存の test_wgsl2 / test_wgsl_spv は common.wgsl 単体しか見ていない）通過
- `GpuPrimitive` のサイズを `18 * 16` で静的アサート（gpu.rs）。WGSL 側とフィールド数が食い違うと
  シェーダは通るのに読み位置がずれるため
- CPU パスの実測: 重なった球2個で `layer_smoothness` 0.0 と 0.5 が別メッシュになること、
  面数が 0.0 > 0.2（素の union）> 0.5 の順で減ることを確認。**修正前バイナリでは
  `layer_smoothness` 引数自体が TypeError になる**ことも確認済み

## 残作業

- **Blender 実機での GPU パス確認**（CPU と GPU で結果が一致するか。特にプレビューとベイクの乖離）
- **detect.wgsl のバウンド確認**: `layer_params.x` を bound_radius に加算済みだが、
  大きい値（1.0 以上）で穴が出ないかは実測が必要
- Mac / Linux バイナリを GitHub Actions で再ビルド
- バージョン番号（bl_info / build_sdf_addon.ps1 の ZIP 名）の更新とリリースノート。
  L-1 と L-2 は既存ファイルの見た目が変わりうる破壊的変更として明記すること
- D-3 のドキュメント整備（Comprehensive User Guide / Workflow Examples）
