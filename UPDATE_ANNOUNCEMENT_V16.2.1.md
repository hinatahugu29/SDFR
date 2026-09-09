# SDF.R V16.2.1 — Update Announcement Email

Copy-paste ready. English version first (for Superhive / Blender Market / Gumroad buyers),
Japanese version below.

---

## Subject line options

1. `SDF.R V16.2.1 — one add-on, separate objects`
2. `SDF.R V16.2.1 is out (free update) — a scene can now hold several SDF trees`
3. `[SDF.R] V16.2.1 released — the parts of your model can be separate meshes now`

*Recommended: option 1 — short, and it names the outcome rather than the mechanism. Anyone who has
asked "how do I get the eyes out as their own object?" will recognise it immediately.*

---

## Body (English)

Hi, and thank you for supporting SDF.R.

**V16.2.1 is now available as a free update for all owners.**

Until now, an SDF.R scene held exactly one SDF tree, and that tree produced exactly one mesh. If you
wanted a model's parts as separate objects, the answer was always "build a second SDF output" — and
there was no way to actually do that from inside the add-on.

That is what this release is.

### 🌳 A scene can hold as many SDF trees as you like

Each tree has its own parts collection, its own settings, and its own result mesh. They are separate
objects from the moment they are built, so there is nothing to split afterwards.

The panel opens with a **Tree** row. The dropdown picks which tree you are editing, **+** adds a new
one, and everything below that row follows your selection. You can also just click a part in the
viewport — the panel jumps to whichever tree that part belongs to.

**Finalize applies to the active tree only.** Baking one leaves the others live and editable.

This matters because shapes in the same tree always form one connected solid where they overlap.
Layer Boundary (V16.2.0) stops them blending, but the merge is still a Union. Shapes in different
trees never meet at all.

It is also **faster**, not slower. Splitting a model means each request carries fewer primitives, and
sparse block detection has less to search. A 216-sphere model at resolution 128 took 5053 ms as one
tree, 1904 ms across four, and 1215 ms across eight. There is no cap on the number of trees.

### 🔗 Tree Reference — for parts that have to fit

One tree can read another tree's shape. Select a part, press **Add Tree Reference**, point it at
another tree, and choose **Blend** or **Subtract**.

Subtract is the one for a fit: carve the lid's cavity out of the jar and the two meet exactly. Edit
the lid, and the cavity follows.

Blend is exact. Subtract is exact as long as the referenced tree is built from Union alone — if it
uses Subtract or Intersect internally, the carve is approximate there, and the panel tells you so.

### 🪞 Mirror Blend — the mirror seam can finally be rounded

Per-primitive **Mirror** repeats a shape by folding space, so the two halves have always met at a
hard minimum. **Smoothness could never touch that seam** — inside folded space there is only one
shape, and nothing to blend it against.

That crease was real geometry, not shading. On a mirrored sphere it measured 44 creased edges at up
to 84°.

**Mirror Blend** evaluates the two sides separately and joins them with the primitive's own blend
shape: 0 creased edges at 8.5°, vertex for vertex identical to building two spheres and joining them
with a smooth union. It works on two axes at once.

It **defaults to 0**, which takes exactly the path it always did, so your existing files are
unchanged until you decide otherwise.

Two honest limits: the ghost preview shows this as an approximation, and **Radial and Grid still
crease** — blending across cell boundaries needs the neighbouring cells, which is a bigger change.

### 🐛 Also fixed

- **Show Result Mesh** now clears the mesh when switched off, instead of only hiding the result.
- **Auto Domain** and **Use Live Normals** re-mesh when toggled.
- The panel no longer unlocks while shaders are still compiling. The GPU-ready flag was being saved
  into your .blend, so a file saved after start-up looked ready on the next launch before the engine
  actually was.

### Upgrading

Install over your current version as usual. Existing files need no migration.

One thing to expect: **the first start after updating takes longer than usual.** The GPU shader code
changed, so the cached pipeline no longer matches and is rebuilt once. On a discrete GPU that is the
usual 15–45 seconds. **On integrated graphics it can take several minutes** — an Intel Iris Xe
measured 194 seconds. The console prints `Compiling MC Pipeline...` while it works and
`GPU Engine Ready!` when it is done. Later starts take a second or two.

Windows, macOS and Linux builds are all available.

Thanks as always for the reports and suggestions — the tree work in this release came directly from
people asking for their parts as separate objects.

---

## Body (日本語)

いつも SDF.R をご利用いただきありがとうございます。

**V16.2.1 を公開しました。既存ユーザーの方は無償アップデートです。**

これまで SDF.R のシーンが持てる SDF ツリーは1本だけで、出力されるメッシュも1つでした。モデルの
パーツを別オブジェクトにしたい場合、答えはいつも「SDF 出力をもう1つ作ってください」でしたが、
**アドオンの中からそれを行う手段がありませんでした**。

今回のアップデートは、その手段そのものです。

### 🌳 1つのシーンに複数の SDF ツリー

各ツリーが自分のパーツ用コレクション、自分の設定、自分の結果メッシュを持ちます。**作った時点で
別オブジェクト**なので、後から分割する作業は要りません。

パネルの一番上に **Tree** 行が出ます。ドロップダウンで編集するツリーを選び、**+** で追加します。
ビューポートでパーツをクリックするだけでも、そのパーツが属するツリーに切り替わります。

**Finalize は選択中のツリーだけに効きます。** 1本を確定しても、残りは編集可能なままです。

同じツリーの中では、重なった形は必ず1つの繋がったソリッドになります。Layer Boundary（V16.2.0）は
ブレンドを止めますが、合流自体は Union のままです。**別のツリー同士は、そもそも一切干渉しません。**

しかも**遅くなるどころか速くなります**。1リクエストあたりのプリミティブ数が減り、疎ブロック検出も
効きやすくなるためです。216個の球・解像度128のモデルで、1本 5053ms → 4本 1904ms → 8本 1215ms。
ツリー数に上限はありません。

### 🔗 Tree Reference — はめ合いを作る

あるツリーが別のツリーの形を読み取れます。パーツを選んで **Add Tree Reference** を押し、参照先の
ツリーと **Blend** / **Subtract** を選びます。

はめ合いに使うのは Subtract です。瓶から蓋のくぼみを削り出せば、両者はぴったり合います。蓋を編集
すれば、くぼみも追従します。

Blend は厳密です。Subtract は、**参照先が Union だけで構成されていれば厳密**です。内部で Subtract
や Intersect を使っている場合はその箇所が近似になり、パネルにその旨が表示されます。

### 🪞 Mirror Blend — ミラーの継ぎ目を丸められるようになりました

プリミティブの **Mirror** は空間を折り返して複製するため、2つの半分は常にハードな最小値で接合されて
いました。**Smoothness はこの継ぎ目に一切効きません** — 折り畳まれた空間の中には形が1つしかなく、
ブレンドする相手が存在しないためです。

これは陰影の問題ではなく、**形そのものの折れ目**でした。ミラーした球で、44本の辺が最大84°。

**Mirror Blend** は両側を別々に評価し、プリミティブ自身のブレンド形状で結合します。結果は折れ目
0本・8.5°で、**実体の球を2つ作って Smooth Union で繋いだ場合と頂点単位で一致**します。2軸同時にも
対応しています。

**既定値は 0** で、その場合は従来とまったく同じ経路を通ります。既存ファイルの見た目は変わりません。

正直に2点。ゴーストプレビューでは近似表示になります。また **Radial と Grid には引き続き折れ目が
出ます** — セル境界をまたぐブレンドには隣のセルの評価が必要で、ミラーより大きな変更になるためです。

### 🐛 その他の修正

- **Show Result Mesh** を OFF にしたとき、結果を隠すだけでなくメッシュを空にするようになりました
- **Auto Domain** と **Use Live Normals** の切り替えで再メッシュされるようになりました
- シェーダーのコンパイル中にパネルが操作可能になる問題を修正しました。GPU準備完了フラグが .blend に
  保存されていたため、初期化後に保存したファイルを開くと、次回起動時に準備完了に見えていました

### アップデート方法

通常どおり上書きインストールしてください。既存ファイルの移行作業は不要です。

1点だけご承知おきください。**更新後の初回起動は通常より時間がかかります。** GPU シェーダーのコードが
変わったため、キャッシュ済みのパイプラインが一致せず、1度だけ再構築が走ります。ディスクリート GPU で
通常どおり15〜45秒、**内蔵GPUでは数分かかることがあります**（Intel Iris Xe で194秒を実測）。処理中は
コンソールに `Compiling MC Pipeline...`、完了時に `GPU Engine Ready!` と表示されます。2回目以降は
1〜2秒です。

Windows / macOS / Linux 版すべて公開済みです。

ご報告・ご要望をいつもありがとうございます。今回のツリー機能は、パーツを別オブジェクトにしたいという
お声から直接生まれたものです。
