# SDF.R V17.0.0 ギズモ実装 引継書

最終更新: 2026-10-14
対象ブランチ: `feature/multitree-phase0`
対象バージョン: V17.0.0(V16.2.2からのメジャー区分。ギズモ実装に伴い版を切った)
思想・設計判断の全履歴は [GIZMO_ROADMAP.md](GIZMO_ROADMAP.md) にある。このドキュメントは
**「次回どこから再開するか」だけ**を素早く拾えるようにした要約。

---

## 0. 3行で

- Blenderのビューポートから、SDFプリミティブのパラメータをドラッグ/クリックで直接編集できる「ギズモ」を追加した。
- 共通パラメータ(`edge_profile_size`/`shell_thickness`/`smoothness`/`operation`/`edge_profile`)と、
  Torus/Cylinder/Capped Cone/Ellipsoid/Rounded Cylinder/Pyramid/Hex Prism/Rounded Box/Octahedron/Cut Sphere
  の固有パラメータは**実装・実機検証とも完了**。
- 残っているのは「難度が上がる2シェイプ(Capped Torus/N-gon Prism)」「ドラッグ中の負荷対策(Phase G1)」
  「ブール操作/モディファイアへの拡張(Phase G3/G4)」。**コードはすべてCIツリー側にあり、pushも済んでいる。**

---

## 1. いま何が終わっていて、何が残っているか

| | 状態 |
|---|---|
| Phase G0(試作: `edge_profile_size`) | 完了・実機検証済み |
| Phase G2(Boxの共通パラメータ: `shell_thickness`/`smoothness`/`operation`/`edge_profile`) | 完了・実機検証済み |
| Phase G2.5(シェイプ固有 `p1`〜`p4`): Torus/Cylinder/Capped Cone/Ellipsoid | 完了・実機検証済み |
| 同上: Rounded Cylinder/Pyramid/Hex Prism/Rounded Box/Octahedron/Cut Sphere | 完了・実機検証済み |
| 同上: **Capped Torus**(`p3` Angle) | **未着手**。ダイヤル(回転)型の新ギズモ形状が要る |
| 同上: **N-gon Prism**(`ngon_sides`) | **未着手**。整数ステッパー型の新ギズモ形状が要る |
| Phase G1(ドラッグ中のスロットリング/軽量プレビュー) | **未着手**。現状1プリミティブに最大5〜6本のギズモが同時に出るため、重いツリーでの負荷未検証 |
| Phase G3(ブール操作へのギズモ適用) | **構想のみ**。着手判断は未定(やらない判断も可) |
| Phase G4(Deform Stackへのギズモ適用) | **構想のみ**。リスト構造・move_3d型ギズモ・モード依存スロットなど新規の論点あり |
| git コミット/push | 完了。`origin/feature/multitree-phase0` と同期済み |

### 再開したらまずこれ

直近のユーザー判断は「低コストなものを先に埋める」方針だった。その方針のままなら、
次の2つのうちどちらからでも着手できる(どちらも新しいギズモ形状が要る分、ここまでより1段コストが上がる):

- **Capped Torus**: `p1` Main Radius / `p2` Pipe Radius はTorusと同じ矢印パターンで即着手可能。
  `p3` Angle (rad) だけダイヤル型ギズモ(`GIZMO_GT_dial_3d`)の検討が要る。
  Radius 2つだけ先に矢印で実装し、Angleを後回しにする、という分割も可。
- **N-gon Prism**: `p1` Radius / `p3` Height は同じく矢印パターンで即着手可能。
  `ngon_sides`(整数・辺数)だけ新しい操作感(増減ボタン2個のステッパー、または
  `GIZMO_GT_button_2d`を流用した+/-ボタン)の検討が要る。

方針を変えて「負荷対策を先に」にするなら、Phase G1(スロットリング)から。
重めのツリーでドラッグ中のフレームレートを実機確認してから設計するのが前提になる
([GIZMO_ROADMAP.md](GIZMO_ROADMAP.md) Phase G1節)。

---

## 2. 何を作ったか(コードの場所)

- 全コードは `rust_gpu_sdf_addon/gizmos.py`(新規ファイル)に集約。`__init__.py` から
  `gizmos.register()`/`gizmos.unregister()` を呼ぶ形で既存の登録フローに組み込んである。
- Rust側(`src/`)は無改修。Python/UI層のみで完結している。
- 追跡対象は **`Rust-GPU-SDF-V17.0.0_CI/`**(gitで管理。`.gitignore`の`!Rust-GPU-SDF-V*_CI/`参照)。
  ローカルの `Rust-GPU-SDF-V17.0.0/`(コンパイル済み.pyd込み、無印)は実機検証用の作業コピーで、
  **CIツリーに加えた変更は都度こちらにもコピーして同期している**(gitには入らない)。
- シェイプ固有ギズモの大半(Rounded Cylinder/Pyramid/Hex Prism/Rounded Box/Octahedron/Cut Sphere)は
  `_make_single_prop_drag_gizmo()`ファクトリ(`gizmos.py`内)から生成している。Capped Torus/N-gon Prismの
  残り2値(Radius/Height)もこのファクトリにそのまま乗せられる。新形状(ダイヤル/ステッパー)が要るのは
  Angle/ngon_sidesの1プロパティずつだけ。

## 3. 検証の仕方(次回も使えるやり方)

- **ヘッドレス一次検証**: `--background`モードのBlenderでは`GizmoGroup`が`bpy.types`に実体化されない
  (Blender自体の既知の制約。本アドオン固有のバグではない、素のテスト用クラスでも同様に確認済み)。
  そのため`poll()`をクラスから直接呼ぶ形で、対象シェイプの受理/除外とプロパティの書き込みラウンドトリップを
  スクリプトで検証している(このセッションで使ったスクリプト例は `C:\Users\hinat\AppData\Local\Temp\claude\...\scratchpad\verify_*.py` 群、使い捨てなので再利用時は都度書き直し)。
  起動例:
  `"/c/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --python <script.py>`
- **実機最終確認**: 上記はpoll()とプロパティ書き込みの機械的確認のみ。実際のドラッグ操作・見た目の
  矢印位置・2つのギズモの干渉有無は毎回ユーザーによるBlender実機確認で締めている。新しいギズモを
  追加したら、このサイクル(ヘッドレス→実機確認→ロードマップに日付入りで記録)を踏襲する。

---

## 4. 軸・色の割り当て一覧(新しいシェイプを足すときの参照表)

共通ギズモが既に `+Z`(edge_profile_size)/`-Z`(shell_thickness)/`+X`(smoothness)/`+X`付近(operationボタン)/
`-X`付近(edge_profileボタン)を使っているため、シェイプ固有の値は原則 **`p1`→+Y, `p2`→-Y, `p3`→-X** に揃えている
(shape_typeが排他なのでシェイプ間の使い回しは衝突しない。例外はEllipsoidで、Blenderの軸配色(赤/緑/青)を
優先したため `p1`(Radius X)だけ`-X`、`p2`→+Y、`p3`→+Zという special case)。新しいシェイプを足すときもこの
規則に従えば、軸の取り合いを都度考え直さずに済む。

---

次回はこのファイルと [GIZMO_ROADMAP.md](GIZMO_ROADMAP.md) を読めば再開できる。
