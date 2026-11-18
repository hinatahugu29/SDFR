# 複数SDFツリー対応 実装計画

> **実装状況（2026-09-09 時点）: Phase 0 / 1 / 2 すべて V16.2.1 として実装済み。**
> ブランチ `feature/multitree-phase0`。
>
> 計画からの主な変更点:
>
> - **Rust は一切変更していない**（`src/` は V16.2.0 とバイト単位で同一）。
>   GPU コンテキストが単一 Mutex で、同時に飛ぶ要求が常に高々1つであるため、
>   リクエストIDを Rust に持たせる必要が無かった。Python 側で「いま投げた要求の
>   持ち主」を1つ覚えるだけで足りる。
> - **B5 は稀なレースだった**（当初「複数ツリーでは必ず踏む」と書いたのは誤り）。
>   実際に systematic なのは B3（予約再試行が先頭の出力で打ち切られる）のほう。
> - Phase 2 の **Intersect と Clearance は見送り**。レイヤー合流が union 固定
>   （`union_layer_accum`）で、距離場を一律に膨らませる口も `SdfPrimitive` に無いため、
>   どちらもシェーダー変更が要る。Blend（厳密）と Subtract（参照先が Union なら厳密）
>   の2モードで出す。
> - 追加で見つけて直したもの: V16.2.0 のコンソール版数表示が V16.1.3 のままだった。
>
> 実測の根拠は [MULTITREE_MEASUREMENT_REPORT.md](MULTITREE_MEASUREMENT_REPORT.md)。

対象バージョン: V16.2.0 時点のコードベース
目的: (1) 非同期メッシュ要求の持ち主識別、(2) 複数ワークスペース(ツリー)の同時運用、(3) ツリー間の干渉(参照)設定
方針: 実装は行わず、着手順・変更箇所・リスク・検証項目を確定させる

---

## 0. 現状調査で判明した既存バグ

複数ツリー対応の前提として、先に潰すべき欠陥がコードから確認できた。
B2/B5/B4 は「2本目のツリーを作った瞬間に必ず踏む」ため、Phase 1 の前提条件になる。

### B1. `auto_domain` が状態フィンガープリントに入っていない
- 場所: `engine.get_sdf_state_fingerprint()` (engine.py:86-104)
- 内容: `resolution` / `domain_size` / `algo_type` などは `state` に積まれているが `auto_domain` が無い。
- 影響: `auto_domain` は `update=update_sdf_callback` 付き (properties.py:437) なのでトグルすると
  `update_sdf_mesh` は呼ばれるが、ハッシュが不変のため「変更がないので何もしない」で早期リターンする。
  **Auto Expand Domain の ON/OFF が、他の変更を加えるまで反映されない。**
- 修正: `state` に `props.auto_domain` を追加するだけ。単独で現行版にも適用できる。
- 同様に未収録: `use_live_normals`（法線適用経路が別なので実害は小さい。要確認）

### B2. 取得したメッシュ結果を全出力オブジェクトに適用している
- 場所: `engine.sdf_mesh_timer()` (engine.py:1455-1462)
- 内容: `fetch_mesh_if_ready()` で取り出した 1 件を `for obj in scene.objects: if is_output:` の全件に `apply_mesh_data` している。
- 影響: 出力が 1 本のうちは無害。**2 本目を作ると両方が同じ形になる。**
- 修正: Phase 0 のリクエストID化とセットで、持ち主 1 体にだけ適用する。

### B3. ペンディング再試行が先頭の出力で打ち切られる
- 場所: engine.py:1474-1480 および engine.py:1500-1506
- 内容: `for obj in ...: if is_output: ... return 0.05` と、ループ内で無条件 `return` している。
- 影響: 2 本目以降の出力の予約更新が永久に処理されない。

### B4. `_cached_divider_names` がモジュールグローバルで、最後に同期したツリーに上書きされる
- 場所: `engine.sync_sdf_stack()` 末尾 (engine.py:317)、参照側は handlers.py:901
- 内容: 仕切り Empty 名の集合を 1 つのグローバル集合に持っている。
- 影響: 複数ツリーでは、片方のツリーの仕切り Empty を動かしても depsgraph ハンドラが
  「関係あり」と判定できず、**メッシュが更新されない**。
- 修正: `{output_name: set()}` の dict 化、または全ツリー分の和集合を保持。

### B5. 要求が拒否されたときに状態ハッシュだけ進んでしまう
- 場所: engine.py:928-930（ハッシュ更新）と engine.py:1240-1250（`requested` の判定）
- 内容: `_last_state_hashes[name] = current_hash` を **リクエスト送出前** に行っている。
  Rust 側は `IS_UPDATING` が立っていると `request_*_update` が `false` を返して要求を捨てる (lib.rs:1288)。
  この場合 Python 側はタイマー登録も `_pending_update` の設定もしないため、
  **更新が失われたまま、ハッシュは「最新」になる。**
- 影響: 現状は関数冒頭の `is_updating()` チェックで大半が救われており、稀なレースに留まる。
  **複数ツリーでは日常的に発生する**（depsgraph ハンドラが 1 回のループで A と B を続けて要求するため、
  B の要求は必ず拒否される）。
- 修正: 要求が成功したときにだけハッシュを確定する、または拒否時にハッシュを巻き戻す。

### B6. 「シーン内で最初に見つかった出力」への暗黙フォールバックが各所にある
- `operators.get_sdf_output_obj()` (operators.py:49-58): アクティブが出力でなければ先頭ヒットを返す
- `SDF_OT_stack_move` ほかの `master` 探索 (operators.py:812-818)
- `SDF_PT_main.draw` の `output_obj` 決定 (ui.py:155-160)
- プレビュー描画の出力決定 (handlers.py:657-666)
- 影響: 複数ツリーでは操作対象が Blender 内部の列挙順で決まり、再現性が無い。
- 備考: `SDF_OT_move_to_sdf_collection` (operators.py:266-280) だけは既にこの問題を認識したコメントと
  対策が入っている。この考え方を全体へ広げる。

### B7. プレビューのキャッシュが単一スロット
- 場所: handlers.py:20-28 (`_preview_dirty`, `_cached_prim_tex`, `_cached_curve_guides` ほか)
- 影響: レイマーチプレビューは 1 ツリーぶんしか保持できない。
- 方針: v1 では「アクティブツリーのみプレビュー」と割り切る（全ツリー合成は負荷が高い）。

---

## Phase 0: リクエストID化（複数ツリーの土台 + 既存バグ修正）

単一ツリー環境では挙動が変わらないため、回帰リスクが小さい。先行して単独リリース可能。

### Rust 側 (`src/lib.rs`)

現状、4 つの要求関数が完全に同型で並んでいる:
- `request_mesh_update` (lib.rs:1287)
- `request_chunked_mesh_update` (lib.rs:1332)
- `request_gpu_chunked_mesh_update` (lib.rs:1356)
- `request_gpu_chunked_dc_update` (lib.rs:1380)

いずれも `IS_UPDATING` を見て `false` を返し、成功時は `MESH_RESULT`(単一 `Option`) に書く。

変更内容:
1. `static MESH_RESULT: Mutex<Option<(Vec<f32>, Vec<u32>)>>` を
   `Mutex<VecDeque<(u64, Option<(Vec<f32>, Vec<u32>)>, String)>>` 相当へ（id・データ・診断/エラー）。
   キュー長には上限を設けて古いものから捨てる。
2. 4 関数すべてに `request_id: u64` 引数を追加（末尾・デフォルト値付きにすれば旧呼び出しとも両立可能）。
3. **失敗時にも id 付きで結果を積む**。現状は `if let Ok(data)` で失敗を握り潰しており
   (lib.rs:1300)、要求元は「結果が来ない」以外の手掛かりを持てない。
4. `fetch_mesh_if_ready()` の戻り値を `Option<(u64, Vec<f32>, Vec<u32>)>` に変更。
5. `IS_UPDATING` は据え置きでよい。`GPU_CONTEXT` が単一 Mutex (lib.rs:18) である以上、
   GPU 計算は元々並列化できない。**逐次実行のまま、結果の持ち主を正しく返せれば足りる。**
   ただし「拒否された要求」を Python が確実に再試行できるよう、拒否は `false` のまま返す。

規模: 約 50-80 行。シェーダー(`*.wgsl`)は無変更。`SdfPrimitive` 構造体も無変更。

### Python 側 (`rust_gpu_sdf_addon/engine.py`)

1. 単一グローバルを出力オブジェクト名キーの dict へ:
   `_pending_update` / `_pending_retry_count` / `_last_mesh_request` / `_safe_retry_active` /
   `_gpu_chunked_mc_active` / `_gpu_chunked_dc_active` / `_cpu_chunked_fallback_active`
   (engine.py:14-24)
2. 要求送出時に `request_id` を採番し `{id: output_name}` を記録。
3. `sdf_mesh_timer()` を書き換え、`fetch_mesh_if_ready()` が返した id から持ち主を引いて
   **その 1 体にだけ** `apply_mesh_data` する（B2 の修正）。再試行ループの早期 `return` も除去（B3）。
4. 要求が受理された場合のみ `_last_state_hashes` を確定（B5 の修正）。
5. `_cached_divider_names` を dict 化（B4 の修正）。
6. B1 の `auto_domain` をフィンガープリントへ追加。

### 配布上の注意
Rust の関数シグネチャが変わるため、**Windows / Mac / Linux の 3 バイナリすべての再ビルドと再配布が必要**
(`_native.py` はプラットフォーム別 `bin/{win,mac,linux}` を読む)。
`cross_platform_build_notes.md` の手順を通す前提でスケジュールを見る。
なお engine.py は既に `hasattr(rust_gpu_sdf, "request_gpu_chunked_mesh_update")` 形式の
機能検出を行っているので、同じ流儀で新旧バイナリを両対応させることも可能。

### 検証項目
- 単一ツリーで、従来通りの更新・chunked フォールバック・safe retry・protect partial が動く
- Auto Expand Domain のトグルが即座に反映される（B1）
- 高解像度で連続編集し、要求の取りこぼしが無い（B5）
- DC コンパイル失敗時に、エラーが従来通り UI に出る

**見積: 3-5 日**（うち 3 プラットフォームのビルド確認に 1 日）

---

## Phase 1: 複数ツリーの成立

### 1-1. `"SDF_Collection"` ハードコードの除去

`target_collection` 経由に置換する。該当箇所:

| ファイル:行 | 用途 | 対応 |
|---|---|---|
| operators.py:190 | `add_primitive` の置き場 | アクティブツリーの `target_collection` |
| operators.py:285 | `move_to_sdf_collection` のフォールバック | 既に主経路は対応済み。フォールバックを削るか警告に |
| operators.py:739 | `add_selected` の置き場 | アクティブツリー |
| operators.py:761 | `make_output` の既存作業検出 | 全ツリー走査へ |
| operators.py:793 | `make_output` の新規作成 | ツリーごとに一意名 (`SDF_Collection_002` 等) |
| operators.py:1405 | `add_collection_divider` のフォールバック | 主経路は `props.target_collection` で対応済み |
| operators.py:1516 | `add_curve_sync` のフォールバック | 同上 |
| operators.py:1236,1241 | All Clear | 全ツリーのコレクションを列挙 |
| handlers.py:874 | SDF 関連オブジェクト判定 | 全ツリーの `target_collection` の和 |
| __init__.py:166 | 起動時処理 | 要確認 |

命名規約の決定が必要:
- 出力: `SDF_Result` → `SDF_Result_A` / `SDF_Tree_001` など
- 置き場: `SDF_Collection` → `SDF_Collection_001`
- 既存シーンとの互換のため、**既存の `SDF_Collection` / `SDF_Result` はそのまま 1 本目として扱う**。
  リネームは行わない（過去の .blend が壊れる）。

### 1-2. アクティブツリーの概念を導入

- `SDF_SceneProperties` に `active_output: PointerProperty(type=bpy.types.Object)` を追加（properties.py:160-）。
- `get_sdf_output_obj()` の解決順を明文化 (operators.py:49):
  1. アクティブオブジェクトが出力ならそれ
  2. アクティブオブジェクトが**いずれかのツリーの `target_collection` に属するプリミティブ**なら、そのツリーの出力
  3. `scene.sdf_scene_props.active_output`
  4. （フォールバック廃止、または「最初の 1 つ」ではなく明示的な警告）
  現状の 2 が欠けているため、プリミティブ選択中の操作が別ツリーへ流れる。
- `stack_move` ほかの独自 `master` 探索 (operators.py:812-818) を `get_sdf_output_obj()` に統一。

### 1-3. ツリー追加オペレーター

`SDF_OT_make_output` (operators.py:753) は既存作業を `SDF_History/Iteration_NNN` へ退避してから
新規作成する「作り直し」オペレーターなので、これは温存する。
別途 `sdf.add_tree`（仮）を新設し、退避せずに新しい出力オブジェクト + 専用コレクションを追加する。

### 1-4. プレビューとキャッシュ

- `_draw_callback_3d_impl` (handlers.py:638) の出力決定を `get_sdf_output_obj()` 基準に変更。
- v1 では**アクティブツリーのみ描画**とし、UI に明記する。
- `mark_preview_dirty()` はツリー切替時にも呼ぶ。

### 1-5. UI

- パネル冒頭にツリー選択行（アクティブツリー名 + 切替 + 追加）。
- Stack / Group Settings / Finalize は「アクティブツリーに対する操作」であることを明示。

### 検証項目
- ツリー 2 本を作り、片方の編集がもう片方に影響しない
- 片方の仕切り Empty を動かして、そのツリーだけが更新される（B4）
- ツリーごとに resolution / domain / algo を変えられる
- V16.2.0 以前の .blend を開いて、1 本目として正しく認識される
- Finalize / All Clear がツリー単位で正しく動く

**見積: 5-8 日**

---

## Phase 2: ツリー間干渉（`TREE_REF`）

### 設計

`update_sdf_mesh` は最終的に、ワールド空間の形状を `inv_world_output` で自ツリーのローカルへ
引き込んだ**フラットなプリミティブ配列**を Rust へ渡すだけ (engine.py:1160-1250)。
したがって、他ツリーのプリミティブ群を自分の配列へ連結し、末尾に op を掛ければ干渉が表現できる。
**Rust / WGSL は無変更。**

既に `CURVE_SYNC` が「外部データを `prebuilt_prims` として working_group に差し込む」前例なので
(engine.py:1055-1105)、同じ枠組みに乗る。

### データモデル

`SDF_StackItem.item_type` に `'TREE_REF'` を追加 (properties.py:245)。追加プロパティ:
- `ref_output_obj: PointerProperty(type=bpy.types.Object)` — 参照先ツリーの出力オブジェクト
- 既存の `operation` / `smoothness` / `blend_profile` / `chamfer_smooth` を流用

干渉モード（`operation` の既存 enum をそのまま使える）:

| モード | 意味 | 用途 |
|---|---|---|
| Union / Smooth Union | 相手と融合 | 別ツリーだが接合部だけ繋ぐ |
| Subtract | 相手の形を引く | **食い込み防止**、はめ込み構造 |
| Intersect | 共通部分 | 型取り、キャップ生成 |

将来拡張: Clearance（相手を半径オフセットで膨らませてから引く。印刷公差用）。
半径の一律加算で近似できるが、smooth union で融合した形状に対しては厳密でない点を仕様として明記する。

### 実装上の必須項目

1. **循環参照の防止**: A→B→A を DAG チェックで拒否。UI 側でも参照先候補から自分と
   自分を参照しているツリーを除外する。`sync_sdf_parents` に同種の循環チェックの前例あり
   (engine.py:1567-1578)。
2. **評価順序**: 参照グラフのトポロジカル順で `update_sdf_mesh` を回す。
   現状の depsgraph ハンドラは `scene.objects` 順に回している (handlers.py:947-951)。
3. **フィンガープリントの伝播**: `get_sdf_state_fingerprint()` (engine.py:84) は自分のスタックしか
   見ていない。**参照先ツリーのハッシュを合成しないと、A を編集しても B が再計算されない。**
   ここが最も踏みやすい落とし穴。循環はここでも防ぐ必要がある（深さ制限つき再帰）。
4. **ドメイン**: 取り込んだプリミティブも `max_extent` に算入する。
   既存の `build_element_primitive` を通せば自動的に満たされる (engine.py:447)。
5. **参照の深さ**: v1 は直接参照 1 段のみに制限する。多段にすると評価プリミティブ数が
   指数的に膨らむため。
6. **Solo との相互作用**: `props.use_solo` は `i > sdf_stack_index` で `break` する実装
   (engine.py:1108) なので、`TREE_REF` アイテムも同じ規則に従わせる。

### 検証項目
- A を Subtract 参照した B が、A の編集に追従して更新される（伝播ハッシュ）
- 循環参照を作ろうとすると拒否される
- 参照先ツリーを削除しても落ちない（`ref_output_obj` が None のときの経路）
- 参照先が `is_output` でなくなった（Finalize された）場合の扱い

**見積: 4-6 日**

---

## 全体の順序と合計

| Phase | 内容 | Rust変更 | 見積 |
|---|---|---|---|
| 0 | リクエストID化 + 既存バグ B1-B5 修正 | 小（50-80行） | 3-5 日 |
| 1 | 複数ツリー成立 | 無し | 5-8 日 |
| 2 | ツリー間干渉 `TREE_REF` | 無し | 4-6 日 |

合計 **12-19 日**。Phase 0 は単独でリリースする価値があり（現行版のバグ修正を含む）、
Phase 1 の前提でもあるため、必ず先行させる。

Phase 2 まで完了すると、発端であった「bake 時に同じコレクションのパーツを分離したい」という要望は、
ツリー分割によって上位互換で満たされる（結果メッシュが最初から別オブジェクトになる）。

## 先に確定させたい仕様判断

1. 既存 `SDF_Collection` / `SDF_Result` の扱い（リネームせず 1 本目として温存する想定でよいか）
2. プレビューはアクティブツリーのみで割り切るか
3. ツリー数の上限を設けるか（GPU 逐次実行なので、編集の応答性は本数に比例して悪化する）
4. Phase 0 を単独のパッチリリース（V16.2.1 相当）として出すか、Phase 1 とまとめるか
