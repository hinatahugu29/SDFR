# SDF.R V16.1.0 — Update Announcement Email

Copy-paste ready. English version first (for Blender Market / Gumroad buyers),
Japanese version below.

---

## Subject line options

1. `SDF.R V16.1.0 is out — draw your shapes with Blender Curves`
2. `SDF.R V16.1.0: Curve Workflow (free update for all owners)`
3. `[SDF.R] V16.1.0 released — Curve Sync, Bezier primitive, Transmission`

*Recommended: option 1 — it names the concrete benefit rather than the version number.*

---

## Body (English)

Hi, and thank you for supporting SDF.R.

**V16.1.0 is now available as a free update for all owners.**

Until now, every shape in SDF.R had to be described numerically. This release adds a
different way to work: **draw a path with Blender's own Curve tools, and SDF.R turns it into
a solid SDF shape** that blends, cuts, and intersects with the rest of your model exactly
like any other primitive.

### What's new

**🌀 Curve Sync — native Blender Curves as SDF geometry**
Add as many curves as you like. Each one gets its own Pipe Radius, boolean Operation
(Union / Subtract / Intersect), Smoothness, and material values. Bezier, Poly, NURBS, and
closed curves are all supported.

There are two ways to attach a curve:

- **Move it in** — drop the curve into the SDF Collection and it is registered directly.
- **Curve Ref** — point a lightweight proxy at a curve living anywhere else in your scene.
  The original object never moves and is never modified, so it stays available for animation
  or Geometry Nodes. You can even aim several proxies at the same curve and give each a
  different radius, colour, or boolean operation.

A one-click **Edit** button jumps straight into the target curve's Edit Mode, so reshaping
the path never means hunting through the Outliner.

**📐 Bezier Curve primitive**
A self-contained 3D quadratic Bezier with independent Start and End radius — for tapered
horns, claws, tentacles, and swept accents defined entirely by numeric control points.

**💎 Transmission & IOR**
Glass-like transmission for the generated SDF material, with a paired IOR control.

**🔧 Instancing accuracy fix**
Fixed geometry that could go missing when Radial or Spiral layouts were combined with
Individual/Step Rotation, and when the Radial Axis was set to X or Y. This affects any
elongated or asymmetric primitive, so it is worth re-checking older arrays too.

### ⚠️ One thing to do before you update

This release changes the GPU shader code, so please **clear the shader cache** before
launching Blender with V16.1.0 installed:

1. Close Blender completely.
2. Delete `%APPDATA%\Blender Foundation\Blender\<your version>\datafiles\rust_gpu_sdf\shader_cache.bin`
3. Restart Blender.

The first startup after clearing will take the full warm-up time again (about 15–45 seconds).
Skipping this step can leave the panel stuck on "Initializing...".

### Downloads

All three platforms are available at V16.1.0:

- **Windows:** `SDF_R_16_1_0.zip` (standard package)
- **macOS:** `SDF_R_16_1_0_MAC.zip` — experimental test build, Apple Silicon (arm64)
- **Linux:** `SDF_R_16_1_0_LINUX.zip` — experimental test build, x86-64

macOS and Linux builds remain experimental while we keep gathering environment reports —
feedback is very welcome. The macOS build is not code-signed, so if Gatekeeper blocks it,
open **System Settings → Privacy & Security** and click **Open Anyway**.

The full release notes and the updated documentation are on the product page.

Thanks again, and I hope the new curve workflow opens up some shapes that were awkward to
build before.

— hinata_hugu

---

## Body (日本語)

いつも SDF.R をご利用いただきありがとうございます。

**V16.1.0 を、すべての購入者様向けの無償アップデートとして公開しました。**

これまで SDF.R の形状はすべて数値で指定する必要がありましたが、今回のアップデートで
**Blender 標準のカーブツールでパスを描くと、それがそのまま SDF 形状になる**という
新しい作り方が加わりました。生成された形状は他のプリミティブとまったく同じように
ブレンド・減算・交差できます。

### 新機能

**🌀 Curve Sync — Blender ネイティブカーブを SDF 形状として使う**
カーブは何本でも追加でき、それぞれに Pipe Radius・ブーリアン演算（Union / Subtract /
Intersect）・Smoothness・マテリアル値を個別に設定できます。Bezier / Poly / NURBS、
閉じたカーブにも対応しています。

カーブの登録方法は2通りです。

- **コレクションに入れる** — カーブを SDF コレクションに移動すれば、そのまま登録されます。
- **Curve Ref** — シーン内の任意の場所にあるカーブを、軽量なプロキシから参照します。
  元のオブジェクトは移動も変更もされないので、アニメーションや Geometry Nodes と併用できます。
  同じカーブを複数のプロキシから参照し、それぞれ別の太さ・色・演算を割り当てることも可能です。

**Edit** ボタンひとつで対象カーブの編集モードに入れるので、アウトライナーを探す必要はありません。

**📐 Bezier Curve プリミティブ**
始点・終点の半径を個別に指定できる3次元の2次ベジェプリミティブです。テーパーのついた角・爪・
触手のような形状を、数値の制御点だけで作れます。

**💎 Transmission と IOR**
生成される SDF マテリアルにガラスのような透過を設定できるようになりました。IOR も併せて調整できます。

**🔧 配列の欠損バグ修正**
Radial / Spiral 配列と Individual/Step Rotation を組み合わせた際、および Radial Axis を
X または Y にした際にジオメトリが欠けることがある問題を修正しました。細長い形状・非対称な形状
すべてに影響するため、以前作った配列も併せてご確認いただくとよいかもしれません。

### ⚠️ アップデート前に1点お願いします

今回のリリースでは GPU シェーダーのコードが変更されています。V16.1.0 をインストールして
Blender を起動する前に、**シェーダーキャッシュを削除**してください。

1. Blender を完全に終了する
2. `%APPDATA%\Blender Foundation\Blender\<バージョン>\datafiles\rust_gpu_sdf\shader_cache.bin` を削除
3. Blender を再起動する

削除後の初回起動は、ウォームアップに再び 15〜45 秒ほどかかります。この手順を飛ばすと、
パネルが「Initializing...」のまま止まってしまう場合があります。

### ダウンロード

3プラットフォームすべて V16.1.0 で揃っています。

- **Windows:** `SDF_R_16_1_0.zip`（標準パッケージ）
- **macOS:** `SDF_R_16_1_0_MAC.zip` — 実験的テストビルド、Apple Silicon (arm64) 用
- **Linux:** `SDF_R_16_1_0_LINUX.zip` — 実験的テストビルド、x86-64 用

macOS / Linux 版は引き続き実験的な位置づけで、環境ごとの動作報告を集めている段階です。
フィードバックをいただけると大変助かります。なお macOS 版は署名されていないため、
Gatekeeper にブロックされた場合は「システム設定 → プライバシーとセキュリティ」から
**「このまま開く」**をクリックしてください。

詳細なリリースノートと更新済みドキュメントは製品ページに掲載しています。

新しいカーブワークフローが、これまで作りにくかった形状のお役に立てば幸いです。

— hinata_hugu

---

## Short version (for social / changelog blurb)

> **SDF.R V16.1.0 — Curve Workflow**
> Draw a path with Blender's Curve tools and SDF.R turns it into a solid SDF shape that
> blends, cuts, and intersects like any other primitive. Multiple curves, per-curve radius
> and boolean operation, plus a new numeric Bezier primitive and Transmission support.
> Free update for all owners — Windows, macOS, and Linux.
> ⚠️ Please clear the shader cache before updating.
