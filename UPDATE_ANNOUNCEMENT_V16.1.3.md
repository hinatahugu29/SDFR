# SDF.R V16.1.3 — Update Announcement Email

Copy-paste ready. English version first (for Blender Market / Gumroad buyers),
Japanese version below.

---

## Subject line options

1. `SDF.R V16.1.3 — Global Symmetry now generates a mesh`
2. `SDF.R V16.1.3 is out (free update) — Symmetry X/Y/Z mesh fix`
3. `[SDF.R] V16.1.3 released — if Symmetry gave you an empty mesh, this is the fix`

*Recommended: option 1 — it names the feature and the outcome, which is exactly what anyone who
hit this was searching for.*

---

## Body (English)

Hi, and thank you for supporting SDF.R.

**V16.1.3 is now available as a free update for all owners.**

This release fixes one thing, and it is a significant one: **Global Symmetry did not produce a
mesh.**

### 🐛 Symmetry X / Y / Z — negative-side shapes are back

With **X**, **Y** or **Z** enabled in the Mesh Settings panel, the Ghost Preview showed the
mirrored result exactly as expected — and then generating a mesh dropped any primitive sitting on
the negative side of that plane, or quietly shrank one that straddled it. Marching Cubes and Dual
Contouring both.

**If you hit this with Booleans, that was the same bug.** It is worth calling out, because it looks
nothing like the single-shape case. With one shape on the negative side you get an empty mesh, and
something is obviously wrong. With a Boolean, the base shape still meshes perfectly and **only the
cut disappears** — a Subtract placed on the negative side was dropped entirely, so what came out
was the uncut solid, while the preview kept showing the cut you expected. Intersect collapsed to
almost nothing. Both are fixed: a cut at X = −2 and one at X = +2 now produce identical meshes.

**Were you affected?** Only if a primitive's centre sat on the negative side of an enabled symmetry
plane. Shapes on the positive side, or exactly on the plane, meshed correctly. And if you had a
matching shape on the positive side, the result could look completely right — so the problem could
stay hidden in exactly the symmetric scenes Symmetry is for.

The preview being correct is what made this so confusing. It looked like the meshing step was
refusing to run. It was running — it was simply looking in the wrong place.

The preview and the mesh generator are two separate implementations of the same scene. The
preview raymarches the SDF directly; the generator first works out where in space it needs to
look, then samples only that volume. Global Symmetry was handled correctly in the first path and
incorrectly in the second, in two ways at once:

- **The search volume covered only one side of the symmetry plane.** The bounding box was being
  clamped to run from 0 to +max instead of −max to +max. Anything on the negative side — including
  the mirrored half of your own model — was discarded before meshing even began.
- **Primitive centres were not folded onto the mirrored side.** Symmetry works by folding the
  sampled point onto one side of the plane, and the preview shader folds each primitive's centre
  to match. The two meshing shaders did not, so a primitive placed at X = −2 with Symmetry X on
  was evaluated as if it sat somewhere else entirely.

As soon as a primitive was on the negative side, both faults lined up: the volume being searched
was empty, and so was the mesh.

Both are fixed, in the Windows, macOS and Linux builds alike. Verified on Blender 5.1 by running
the old and new engines side by side: a primitive at X = −2 with Symmetry X produced an empty mesh
before and a correct −3.0 → +3.0 mesh now, under Marching Cubes and Dual Contouring alike.

Per-primitive **Mirror** in the Layout section was never affected. Meshes generated with Symmetry
off are identical to V16.1.2 — nothing else about the output changes in this release.

If you tried Global Symmetry, got an empty mesh and assumed you had set something up wrong: you
had not.

### 🖱️ Clicking a layer in The Stack now selects it

Also from the same feedback: selecting a layer only worked by clicking its **name**. Clicking
anywhere else in the row moved the highlight but left the viewport selection alone, so the panel
and the scene disagreed about what you had selected. The whole row now works.

Selecting objects in the viewport still drives the panel the other way, and multi-selection is
preserved — selecting several objects no longer gets collapsed down to one.

### 🔧 One internal change

All three platform builds now load their native engine through the same code path. Until now the
Windows build loaded it one way and the macOS and Linux builds another, so the three packages
carried slightly different Python that had to be reconciled by hand every release. They are now
byte-for-byte identical — which means the macOS and Linux builds run exactly the code I can test on
Windows, rather than a hand-adjusted variant of it. No visible change for you.

### 🔄 Updating — nothing you must do

SDF.R now clears its own shader cache and retries if it ever fails to start after an update, so the
manual cleanup older announcements asked for is no longer required. If you would rather clear it by
hand anyway, it is harmless and costs one slower startup:

1. Close Blender completely.
2. Delete the shader cache file:
   - Windows: `%APPDATA%\Blender Foundation\Blender\<your version>\datafiles\rust_gpu_sdf\shader_cache.bin`
   - macOS: `~/Library/Application Support/Blender/<your version>/datafiles/rust_gpu_sdf/shader_cache.bin`
   - Linux: `~/.config/blender/<your version>/datafiles/rust_gpu_sdf/shader_cache.bin`
3. Restart Blender. The first startup after clearing takes the full warm-up time again.

### Downloads

- **Windows:** `SDF_R_16_1_3.zip` (standard package)
- **macOS:** `SDF_R_16_1_3_MAC.zip` — Apple Silicon (arm64)
- **Linux:** `SDF_R_16_1_3_LINUX.zip` — x86-64

The macOS build is not notarized, so if Gatekeeper blocks it, open
**System Settings → Privacy & Security** and click **Open Anyway**.

Full release notes and updated documentation are on the product page.

As always: I develop on Windows and do not own a Mac or a Linux machine, so those builds improve
exactly as fast as people tell me things — including telling me when things work. One sentence
genuinely helps.

Thank you,

— hinata_hugu

---

## Body (日本語)

いつも SDF.R をご利用いただきありがとうございます。

**V16.1.3 を、すべての購入者様向けの無償アップデートとして公開しました。**

今回は修正が1点のみですが、重要なものです。**全体対称化（Global Symmetry）でメッシュが
生成されない不具合**を修正しました。

### 🐛 Symmetry X / Y / Z で負側の形状が出るようになりました

Mesh Settings パネルの **X / Y / Z** をオンにすると、ゴーストプレビューでは期待どおり対称化
された形状が表示されるにもかかわらず、メッシュを生成すると**対称面の負側に置いたプリミティブ
が消える**、あるいは**面をまたいでいる場合は黙って形が縮む**、という不具合がありました。
Marching Cubes / Dual Contouring のどちらでも発生していました。

**ブーリアン（Subtract / Intersect）でこの症状に当たられた方へ。同じ不具合です。** 単体の
プリミティブとは現れ方がまったく違うため、個別に説明させてください。単体形状が負側にある場合は
メッシュが空になり、異常だとすぐ分かります。しかしブーリアンの場合、**土台の形状は正常に
メッシュ化され、切り欠きだけが消えます。** 負側に置いた Subtract が丸ごと無視されるため、
出力されるのは「切り欠きのない元の形状」です。エラーも出ず、プレビューには切り欠きが
表示され続けます。Intersect の場合はほぼ何も残りませんでした。いずれも修正済みで、切り欠きを
X = −2 に置いても X = +2 に置いても同一のメッシュが生成されるようになりました。

**自分は影響を受けていたのか？** プリミティブの**中心が対称軸の負側にあった場合のみ**です。
正側や対称面上にあるものは正しくメッシュ化されていました。さらに、正側に対になる形状があると
結果が正しく見えてしまうため、**対称化を使う典型的なシーンほど不具合が隠れやすい**状態でした。

**プレビューが正しく見えていたことが、この問題を分かりにくくしていました。** メッシュ生成が
動いていないように見えますが、実際には動いており、単に「見る場所」が間違っていました。

プレビューとメッシュ生成は、同じシーンに対する別々の実装です。プレビューは SDF を直接
レイマーチングします。一方メッシュ生成は、まず**空間のどこを見るべきかを決めてから**、その
範囲だけを GPU でサンプリングします。全体対称化は前者では正しく、後者では誤って扱われて
いました。しかも2箇所同時に、です。

- **探索範囲が対称面の片側しか覆っていませんでした。** バウンディングボックスが
  「−max 〜 +max」ではなく「0 〜 +max」に切り詰められていました。負側にあるもの
  （ミラーされた反対側の形状も含みます）は、メッシュ生成が始まる前に捨てられていました。
- **プリミティブ中心が対称側に折り返されていませんでした。** 対称化はサンプリング点を対称面の
  片側へ折り返すことで実現しており、プレビュー用シェーダーはプリミティブ中心も同様に折り
  返しています。メッシュ生成側の2つのシェーダーはこれを行っていなかったため、Symmetry X
  有効時に X = −2 に置いたプリミティブが、まったく別の位置にあるものとして評価されて
  いました。

プリミティブが負側にあると、この2つが噛み合って探索範囲の中身が空になり、結果として空の
メッシュが出力されていました。

いずれも修正済みで、Windows / macOS / Linux のすべてのビルドに入っています。Blender 5.1 上で
**修正前と修正後のエンジンを並べて実行し**、X = −2 に置いた場合に修正前は空のメッシュ、修正後は
−3.0 〜 +3.0 の正しいメッシュが生成されることを、Marching Cubes / Dual Contouring の両方で
確認しています。

Layout セクションのプリミティブ単位の **Mirror** は元から影響を受けていません。Symmetry を
オフにして生成したメッシュは V16.1.2 と同一で、それ以外の出力は今回変わりません。

全体対称化を試してメッシュが出ず、設定の誤りだと思われた方がいらしたら、**それは違います。**

### 🖱️ The Stack のレイヤーが、行のどこをクリックしても選択できるようになりました

同じくいただいたご意見です。これまではレイヤーの**名前**をクリックしたときだけ選択が連動し、
行の他の場所を押すとハイライトだけが動いて、ビューポートの選択は変わりませんでした。パネルと
シーンで「今どれを選んでいるか」が食い違う状態です。行全体が反応するようになりました。

ビューポート側で選んだときにパネルが追従する動きはこれまでどおりで、**複数選択も維持されます**
（ビューポートで複数選んだものが1つに減ることはありません）。

### 🔧 内部的な変更が1点あります

Windows / macOS / Linux の3ビルドが、**同じ経路でネイティブエンジンを読み込むようになりました。**
これまでは Windows だけ読み込み方が異なっており、3つのパッケージがわずかに違う Python を
持っていて、リリースのたびに手作業で揃える必要がありました。今回からバイト単位で同一です。

皆さんにとっての意味は間接的なものですが、**macOS / Linux 版が「Windows で私がテストできる
コードそのもの」を動かすようになった**、ということです。表示や操作に変化はありません。

### 🔄 アップデート前の作業は不要です

SDF.R は、更新後に起動できなかった場合に**自身でシェーダーキャッシュを削除して再試行します。**
そのため、以前の告知でお願いしていた手動削除はもう必要ありません。念のため手動で削除したい
場合も、実害はありません（初回起動が1回遅くなるだけです）。

1. Blender を完全に終了します。
2. シェーダーキャッシュファイルを削除します。
   - Windows: `%APPDATA%\Blender Foundation\Blender\<お使いのバージョン>\datafiles\rust_gpu_sdf\shader_cache.bin`
   - macOS: `~/Library/Application Support/Blender/<お使いのバージョン>/datafiles/rust_gpu_sdf/shader_cache.bin`
   - Linux: `~/.config/blender/<お使いのバージョン>/datafiles/rust_gpu_sdf/shader_cache.bin`
3. Blender を再起動します。削除後の初回起動のみ、ウォームアップに通常の時間がかかります。

### ダウンロード

- **Windows:** `SDF_R_16_1_3.zip`（通常パッケージ）
- **macOS:** `SDF_R_16_1_3_MAC.zip` — Apple Silicon (arm64)
- **Linux:** `SDF_R_16_1_3_LINUX.zip` — x86-64

macOS 版は公証（notarization）を受けていないため、Gatekeeper にブロックされた場合は
**システム設定 → プライバシーとセキュリティ** を開き、**「このまま開く」** をクリックして
ください。

詳細なリリースノートと更新済みドキュメントは製品ページに掲載しています。

いつものお願いですが、私は Windows で開発しており Mac も Linux の実機も持っていないため、
これらのビルドは皆さんが教えてくださる分だけ良くなります。**「問題なく動いています」という
一言も含めて**、ご連絡いただけると本当に助かります。

引き続きよろしくお願いいたします。

— hinata_hugu
