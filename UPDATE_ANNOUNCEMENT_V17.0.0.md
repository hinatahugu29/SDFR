# SDF.R V17.0.0 — Update Announcement Email

Copy-paste ready. English version first (for Superhive / Blender Market / Gumroad buyers),
Japanese version below.

> **V16.2.2 のときとの違い:** 前回は小さな修正リリースでした。**今回はメジャーアップデートです。**
> ビューポートに「ギズモ」(ドラッグ/クリックで値を変えられるハンドル)を追加しました。
> ただし**Rustエンジンは無改修**で、パネルの数値欄も全部そのまま残っています。
> 告知の目的は「新しい触り方ができるようになった」ことを伝えることで、
> 既存ファイルへの影響や移行作業が無い点も明記してください。

---

## Subject line options

1. `SDF.R V17.0.0 — drag it in the viewport now (Edge Size, Shell, Smoothness, and more)`
2. `SDF.R V17.0.0 is out (free update) — viewport gizmos for every primitive`
3. `[SDF.R] You can now drag primitive values directly in the viewport`

**Use option 1 or 2** — this is a positive feature announcement, not a bug-fix notice, so the
subject should lead with what's new rather than reference a prior problem.

**Japanese subject:** `SDF.R V17.0.0 公開 — ビューポート上のギズモでプリミティブを直接編集できるようになりました`

---

## Body (English)

Hi, and thank you for supporting SDF.R.

**V17.0.0 is now available as a free update for all owners.** This is a major update: SDF.R now
has viewport gizmos.

### 🧰 Drag it, don't just type it

Select an SDF primitive and colored arrows and buttons now appear around it in the viewport.
Drag an arrow to change a value — Fillet size, Shell thickness, Smoothness, a shape's own
Radius or Height — and click a button to switch a choice — Union/Subtract/Intersect, or the
Edge Profile style. The side panel still has every field it always had; the gizmos are a
second way to reach the same values, not a replacement for the panel.

Every shape gets what makes sense for it. A Sphere has no edges, so it skips the fillet gizmo
instead of showing one that would do nothing. A Torus gets its own Main Radius and Pipe Radius
arrows. An Ellipsoid's three radius arrows are colored red/green/blue to match the X/Y/Z axes
they move along. The full list of what's covered is in this version's release notes.

### Nothing about your files changes

Every gizmo writes to the exact same property the panel field already used. There is no new
data saved on your objects, no file format change, and no change to how any shape is meshed.
**If you never touch a gizmo, nothing about how SDF.R behaves has changed.**

The Rust engine itself is untouched in this release, so there's no shader cache rebuild —
**the first start after upgrading is as fast as always.**

### What's not here yet

Two areas are still panel-only in this release: the relationship between two primitives in a
boolean operation (blend radius at a specific boundary), and the Deform Stack (Elongate / Bend
/ Twist / Taper). Both need a different kind of gizmo than the ones added here and are planned
for a future update.

### Upgrading

Install over V16.2.2 as usual. Existing files need no migration and open exactly as they did
before.

Windows, macOS and Linux builds are all available.

---

## Body (日本語)

いつも SDF.R をご利用いただきありがとうございます。

**V17.0.0 を公開しました。既存ユーザーの方は無償アップデートです。** 今回はメジャーアップデートで、
SDF.R にビューポートギズモが加わりました。

### 🧰 数値欄に入力するだけでなく、ビューポートでドラッグできます

SDFプリミティブを選択すると、周囲に色付きの矢印やボタンが表示されるようになりました。矢印を
ドラッグすれば値が変わります — フィレットのサイズ、シェル(中空)の厚み、滑らかさ、各形状固有の
半径や高さなど。ボタンをクリックすれば選択肢を切り替えられます — Union/Subtract/Intersect や
エッジプロファイルのスタイルなど。サイドパネルの項目は今までどおりすべて残っており、ギズモは
同じ値への**もう一つの入口**です。パネルを置き換えるものではありません。

それぞれの形状に意味のあるものだけを出しています。Sphereには角が無いため、フィレット用の
ギズモは最初から出ません(出しても何も変わらないため)。Torusには専用のMain Radius / Pipe Radius
矢印が付きます。Ellipsoidの3本の半径矢印は、動かす軸に合わせて赤/緑/青に色分けしています。
対応している項目の一覧は、このバージョンのリリースノートに記載しています。

### ファイルへの影響はありません

どのギズモも、パネルの項目が使っていたのと**全く同じプロパティ**に書き込みます。オブジェクトに
新しいデータが増えることも、ファイル形式が変わることも、メッシュの生成方法が変わることもありません。
**ギズモを一度も触らなければ、SDF.Rの動作は何も変わりません。**

今回のリリースではRustエンジン自体には一切手を入れていないため、**シェーダーキャッシュの
再構築は走らず、アップデート後の初回起動もこれまでどおりすぐ立ち上がります。**

### まだ対応していないもの

2つの領域は、今回まだパネル操作のみです。2つのプリミティブ間のブーリアン関係(特定の境界での
ブレンド半径)と、Deform Stack(Elongate / Bend / Twist / Taper)です。どちらも今回追加した
ギズモとは異なる形式が必要で、今後のアップデートで対応予定です。

### アップデート方法

V16.2.2 に上書きインストールしてください。既存ファイルの移行作業は不要で、今までどおり開けます。

Windows / macOS / Linux 版すべて公開済みです。
