# SDF.R V17.0.2 — Update Announcement Email

Copy-paste ready. English version first (for Superhive / Blender Market / Gumroad buyers),
Japanese version below.

> **V17.0.1 のときとの違い:** 前回と同じく**小さな修正リリース**です。新機能はありません。
> Edge を Round(既定値)にしたまま Size を上げても角が丸くならなかった不具合の修正です。
>
> **対象は Box / Cylinder / Hex Prism / Ngon Prism の角を丸めたい人**です。Edge Size の既定値が
> 0.1 から 0 に変わった点と、「Round のまま Size を触っていたプリミティブは更新後に丸くなる」点
> だけは全員に伝えておく必要があります。

---

## Subject line options

1. `SDF.R V17.0.2 — Round edges now follow Edge Size`
2. `SDF.R V17.0.2 is out (free update) — the Round edge profile finally rounds`

**Japanese subject:** `SDF.R V17.0.2 公開 — Edge「Round」で Size が効かなかった不具合を修正しました`

---

## Body (English)

Hi, and thank you for supporting SDF.R.

**V17.0.2 is now available as a free update for all owners.** It's a small fix release: one bug,
fixed.

### 🐛 Round ignored Edge Size

If you added a Box, left **Edge** on **Round** and raised **Size** — and the corners stayed
sharp — that was a real bug, and it's fixed. It affected both the viewport preview and the
generated mesh, and the Fillet gizmo too.

**Round is now a true circular round, with Size as its radius.** Size 0.5 on a default cube gives
a 0.5 radius on every edge, with clean spherical corners. Size 0 means sharp edges for every
profile. Sharp, Soft, Tight and Chamfer look exactly as before.

**Edge Size now starts at 0** on new primitives — pick a profile, then raise Size.

**About your existing files:** primitives whose Edge Size you never touched keep their sharp
look. If a primitive on Round already had an Edge Size set (for example from dragging the Fillet
gizmo when it seemed to do nothing), it will now be rounded by that amount. Set Edge Size back to
0 if that's not what you want.

Thanks to the user who reported this with a precise diagnosis.

### Upgrading

Install over V17.0.1 as usual. No migration needed.

Windows, macOS (Apple Silicon) and Linux builds are all available.

---

## Body (日本語)

いつも SDF.R をご利用いただきありがとうございます。

**V17.0.2 を公開しました。既存ユーザーの方は無償アップデートです。** 修正1件のみの小さな
リリースです。

### 🐛 Edge「Round」で Size が効いていませんでした

Box を追加して **Edge** を **Round** のまま **Size** を上げても角が丸くならなかった方、それは
実在する不具合でした。ビューポートのプレビューと生成メッシュの両方、そして Fillet ギズモにも
影響していました。今回修正しています。

**Round は Size をそのまま半径とする、本物の円形の丸めになりました。** デフォルトのキューブで
Size 0.5 にすると、すべての辺が半径 0.5 で丸まり、角はきれいな球面になります。Size 0 は、
どのプロファイルでも角なしです。Sharp・Soft・Tight・Chamfer の見た目は以前と変わりません。

**Edge Size の初期値は 0 になりました。** プロファイルを選んでから Size を上げてください。

**既存のファイルについて:** Edge Size を一度も触っていないプリミティブは、これまでどおり角の
ある形のままです。Round のまま Edge Size を設定していたプリミティブ(効いていないように見えた
Fillet ギズモをドラッグした場合など)は、更新後はその値で丸くなります。意図しない場合は
Edge Size を 0 に戻してください。

的確な原因の分析とともにご報告くださったユーザー様に感謝いたします。

### アップデート方法

V17.0.1 に上書きインストールしてください。移行作業は不要です。

Windows / macOS(Apple Silicon)/ Linux 版すべて公開済みです。
