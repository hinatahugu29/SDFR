# SDF.R V16.1.1 — Update Announcement Email

Copy-paste ready. English version first (for Blender Market / Gumroad buyers),
Japanese version below.

---

## Subject line options

1. `SDF.R V16.1.1 — smoother viewport, and Blender 5.2 support`
2. `SDF.R V16.1.1 is out (free update) — faster preview, 5.2 compatibility`
3. `[SDF.R] V16.1.1 released — preview performance & Blender 5.2 fixes`

*Recommended: option 1 — it leads with the benefit and flags the compatibility fix, which
is the part 5.2 users need to know about.*

---

## Body (English)

Hi, and thank you for supporting SDF.R.

**V16.1.1 is now available as a free update for all owners.**

This is a maintenance release. Nothing about mesh generation changes — the geometry SDF.R
produces is identical to V16.1.0. What changes is how the preview is drawn while you work,
plus a set of fixes, including one that matters if you have moved to Blender 5.2.

### What's new

**⚡ Smoother viewport while navigating**
The Ghost Preview is raymarched, so its cost scales with the number of pixels on screen.
While the camera is moving, or while you are dragging an object, the preview now renders at
a reduced resolution and is scaled up to fill the viewport — 50% linear resolution during
camera navigation, which is a quarter of the pixels. Shading normals switch to a cheaper
estimate at the same time.

**The moment you stop, it is redrawn at full resolution.** Still frames look exactly as
before. Because this reduces pixel count rather than scene complexity, it helps most in the
heavy scenes that used to suffer worst.

**🧩 Blender 5.2 support for the Post-Process panel**
If you are on Blender 5.2, the Post-Process (Smoothing) section came up empty. Blender 5.2
changed where Geometry Nodes modifier inputs are stored, and SDF.R was still looking in the
old place. It now finds them either way, so one build works on both 5.1 and 5.2.

Worth knowing: this affected **every earlier version of SDF.R** running on Blender 5.2, not
just V16.1.1. If you tried the smoothing controls on 5.2 and found them missing, this is why.

**🖥️ Correct preview with split viewports**
With two or more 3D Viewports open, the Ghost Preview could fail to appear once the camera
came to rest, and stayed stuck in its reduced-quality state. Simply alternating between two
viewports looked like continuous camera movement to the add-on. Motion is now tracked per
viewport.

**🛡️ Mesh data safety check**
Vertex data coming back from the engine is now range-checked before being handed to Blender.
Invalid data is reported in the console instead of being written into the mesh, where it
could corrupt memory and crash Blender later — in a place with no obvious connection to the
real cause. Valid data is unaffected.

### ✅ Updating from V16.1.0 — nothing to do

The GPU shader code is unchanged in this release, so **clearing the shader cache is not
required** this time.

If you are coming from **V16.0.x or earlier**, please still clear it, since V16.1.0 did
change the shader code:

1. Close Blender completely.
2. Delete `%APPDATA%\Blender Foundation\Blender\<your version>\datafiles\rust_gpu_sdf\shader_cache.bin`
3. Restart Blender. The first startup after clearing takes the full warm-up time again.

### Downloads

All three platforms are available at V16.1.1:

- **Windows:** `SDF_R_16_1_1.zip` (standard package)
- **macOS:** `SDF_R_16_1_1_MAC.zip` — experimental test build, Apple Silicon (arm64)
- **Linux:** `SDF_R_16_1_1_LINUX.zip` — experimental test build, x86-64

The macOS build is not code-signed, so if Gatekeeper blocks it, open
**System Settings → Privacy & Security** and click **Open Anyway**.

### 🔍 One open issue on macOS — and a request

I want to be upfront about this rather than let you find it.

One user has reported Blender crashing immediately when adding a primitive, on **macOS 26.6
with Apple Silicon and Blender 5.2**. **I have not been able to reproduce it.** The same
steps work here on Windows under both Blender 5.1 and 5.2, and the crash lands inside
Blender's own scene evaluation rather than anywhere I can point to in the add-on. The cause
is still unknown.

**Workaround:** turning **Show Result Mesh** off lets you add and shape primitives normally.
You keep the live Ghost Preview and the whole modelling workflow — you simply do not get the
final generated mesh until this is solved.

The safety check mentioned above may or may not address it. That is an honest "may": it
closes a real hole, but I have no evidence yet that this particular hole is the one being hit.

**If you are on macOS or Linux, I would genuinely appreciate hearing from you either way:**

- **If it crashes**, the most useful thing is the console output. Launch Blender from
  Terminal with `/Applications/Blender.app/Contents/MacOS/Blender`, reproduce the crash, and
  send me whatever the Terminal printed.
- **If it simply works, please tell me that too.** Knowing which macOS versions, chips and
  Blender versions are *unaffected* narrows this down just as much as a crash report does.
  Right now I have exactly one data point and cannot tell how widespread it is.

The full release notes and updated documentation are on the product page.

Thanks again — and if you work with several viewports open, or you have moved to 5.2, this
one is worth grabbing.

— hinata_hugu

---

## Body (日本語)

いつも SDF.R をご利用いただきありがとうございます。

**V16.1.1 を、すべての購入者様向けの無償アップデートとして公開しました。**

今回はメンテナンスリリースです。メッシュ生成の内容は変わっておらず、出力されるジオメトリは
V16.1.0 と同一です。変わったのは作業中のプレビュー描画と、いくつかの修正です。とくに
Blender 5.2 をお使いの方には関係する修正が含まれています。

### 更新内容

**⚡ 視点操作中のビューポートが軽くなりました**
ゴーストプレビューはレイマーチングで描いているため、コストは画面のピクセル数に比例します。
カメラを動かしている間、およびオブジェクトをドラッグしている間は、**解像度を落として描画し、
拡大してビューポートに表示する**ようになりました。カメラ操作中は縦横 50%、つまりピクセル数
としては 1/4 です。同時に、陰影の法線計算も軽い方式へ切り替わります。

**操作を止めた瞬間にフル解像度で描き直されます。** 静止画の見た目は従来どおりです。
シーンの複雑さではなくピクセル数を減らす方式なので、これまで最も重かった大規模なシーンほど
効果が出ます。

**🧩 Blender 5.2 での Post-Process パネル対応**
Blender 5.2 をお使いの場合、Post-Process（Smoothing）の項目が空欄になっていました。
5.2 で Geometry Nodes モディファイアの入力値の格納場所が変更されたにもかかわらず、SDF.R が
従来の場所を参照し続けていたためです。どちらの形式でも値を見つけられるようにしたので、
5.1 と 5.2 のどちらでも同じビルドが動作します。

補足として、これは V16.1.1 で発生した不具合ではなく、**Blender 5.2 上では過去のすべての
バージョンで起きていた**ものです。5.2 でスムージングの項目が見当たらなかった方は、これが原因です。

**🖥️ 3Dビュー分割時のプレビュー表示を修正**
3Dビューを2つ以上開いていると、カメラを止めてもゴーストプレビューが表示されず、低品質の
状態のままになることがありました。2つのビューポートを交互に描画するだけで、アドオン側からは
カメラが動き続けているように見えていたためです。移動判定をビューポートごとに行うようにしました。

**🛡️ メッシュデータの安全チェック**
エンジンから返る頂点データを、Blender へ渡す前に範囲チェックするようにしました。不正な値は
メッシュに書き込まず、コンソールへ報告します。従来はそのまま書き込まれてメモリを破壊し、
**まったく無関係に見える場所で後からクラッシュする**可能性がありました。正常なデータには影響ありません。

### ✅ V16.1.0 からの更新は、事前作業なしで大丈夫です

今回のリリースでは GPU シェーダーのコードを変更していないため、**シェーダーキャッシュの削除は
不要**です。

**V16.0.x 以前**からの更新の場合は、V16.1.0 でシェーダーコードが変わっているため、従来どおり
削除をお願いします。

1. Blender を完全に終了する
2. `%APPDATA%\Blender Foundation\Blender\<バージョン>\datafiles\rust_gpu_sdf\shader_cache.bin` を削除
3. Blender を再起動する（初回起動はウォームアップに 15〜45 秒ほどかかります）

### ダウンロード

3プラットフォームすべて V16.1.1 で揃っています。

- **Windows:** `SDF_R_16_1_1.zip`（標準パッケージ）
- **macOS:** `SDF_R_16_1_1_MAC.zip` — 実験的テストビルド、Apple Silicon (arm64) 用
- **Linux:** `SDF_R_16_1_1_LINUX.zip` — 実験的テストビルド、x86-64 用

macOS 版は署名されていないため、Gatekeeper にブロックされた場合は「システム設定 →
プライバシーとセキュリティ」から**「このまま開く」**をクリックしてください。

### 🔍 macOS で未解決の問題があります（あわせてお願い）

後から気づかれるより先にお伝えしておきます。

**macOS 26.6 / Apple Silicon / Blender 5.2** の環境で、プリミティブを追加した瞬間に Blender が
クラッシュするという報告を1件いただいています。**こちらでは再現できていません。** 同じ手順を
Windows の Blender 5.1 / 5.2 で試しても問題なく、クラッシュしている場所も Blender 内部の
シーン評価処理で、アドオン側の特定の箇所を指し示せていません。原因は未特定です。

**回避策:** **Show Result Mesh** を OFF にすれば、プリミティブの追加も形状の調整も通常どおり
行えます。ゴーストプレビューもモデリングの流れもそのまま使え、最終的な生成メッシュだけが
出ない状態になります。

上に書いた安全チェックが効く可能性はありますが、断定はできません。実在する穴を塞いだのは
確かですが、その穴が今回の症状の原因だという証拠はまだありません。

**macOS / Linux をお使いの方は、どちらの結果でもお知らせいただけると大変助かります。**

- **クラッシュする場合** — 最も有用なのはコンソール出力です。ターミナルから
  `/Applications/Blender.app/Contents/MacOS/Blender` で Blender を起動し、クラッシュを
  再現させたうえで、ターミナルに出力された内容をお送りください。
- **問題なく動く場合も、ぜひお知らせください。** どの macOS バージョン・チップ・Blender
  バージョンで**問題が起きないか**が分かることは、クラッシュ報告と同じくらい切り分けに
  役立ちます。現時点でデータが1件しかなく、どの範囲の問題なのか判断できていません。

詳細なリリースノートと更新済みドキュメントは製品ページに掲載しています。

複数のビューポートを開いて作業される方、および Blender 5.2 へ移行された方には、
とくにおすすめのアップデートです。

— hinata_hugu

---

## Short version (for social / changelog blurb)

> **SDF.R V16.1.1 — Preview performance & Blender 5.2 support**
> The Ghost Preview now drops to a reduced resolution while you navigate and snaps back to
> full quality the instant you stop, so heavy scenes stay responsive. Also fixes the
> Post-Process panel on Blender 5.2 (which affected earlier versions too), the preview
> failing to appear with split viewports, and adds a safety check on mesh data.
> Mesh output is unchanged. Free update for all owners — Windows, macOS, and Linux.
> ✅ No shader cache clearing needed when coming from V16.1.0.
