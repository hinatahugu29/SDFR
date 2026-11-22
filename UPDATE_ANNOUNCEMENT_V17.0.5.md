# SDF.R V17.0.5 — Update Announcement Email

Ready to copy and paste. The English version comes first (for Superhive / Blender Market / Gumroad buyers), and the Japanese version follows.

> **V17.0.4 のときとの違い:** 今回は新しい機能(Apply Edge All)が入るので、修正だけだった V17.0.4 より
> 前向きに告知できます。新機能を先に、四角錐の修正を後に置いています。
>
> - 四角錐(Pyramid)を使っている既存ファイルは、底面のまわりの形が少し変わります。メールでも一言触れています。
> - Windows の更新手順は今回も同じです(無効化 → 再起動 → インストール)。毎回書いておくのが安全です。
> - V17.0.4 をまだ告知していないなら、V17.0.4 と V17.0.5 をまとめて1通にする手もあります。

---

## Subject line options

1. `SDF.R V17.0.5 — Round every edge in one click`
2. `SDF.R V17.0.5 is out (free update) — Apply Edge All, and a fix for the Pyramid base`

**Japanese subject:** `SDF.R V17.0.5 公開 — 全プリミティブのエッジを一度に丸める Apply Edge All`

---

## Body (English)

Hi, and thank you for supporting SDF.R.

**V17.0.5 is now available as a free update for all owners.** It adds a new one-click tool for
edges and fixes the Pyramid base.

### ✨ Apply Edge All — round every edge at once

Perfectly sharp edges can look streaky under smooth shading. The rim of a cylinder's end cap is a
typical example, in MC and DC alike. The shape itself is accurate, and a tiny bit of rounding
gives the shading a real curve to follow, so the rim comes out clean.

The new **Edges (All Primitives)** box, below the stack list, does this for the whole tree in one
click:

1. Pick an edge profile (Round, Sharp, Soft, Tight or Chamfer).
2. Set the size in **Voxels** (default 2, so it follows your resolution) or as a fixed **Distance**.
3. Click **Apply Edge All**.

Every primitive gets the same edge, and you can still change any of them on its own afterwards.
Turn on **Also round Subtract / Intersect seams** to round the rims of holes cut by Subtract as well.

### 🐛 Pyramid base: flat again

The bottom face of a **Pyramid** came out in small stair steps at the wrong height. With
GeoRemesh_R on, it could even render as black patches in Cycles. The base is now exactly flat where
you placed it, in MC, DC and the preview.

If you use pyramids, their base will look slightly different, and cleaner.

### ⚠️ Updating on Windows — same order as before

1. **Edit → Preferences → Add-ons**, and **disable** SDF.R.
2. **Restart Blender.**
3. Install the V17.0.5 zip and enable SDF.R.

If the panel shows **Engine version mismatch**, repeat the three steps. macOS and Linux can install
over the previous version as usual.

Windows, macOS (Apple Silicon) and Linux builds are all available.

---

## Body (日本語)

いつも SDF.R をご利用いただきありがとうございます。

**V17.0.5 を公開しました。既存ユーザーの方は無償アップデートです。** エッジを一度に丸める新しい
機能を追加し、四角錐の底面の不具合を修正しました。

### ✨ Apply Edge All — すべてのエッジを一度に丸める

完全に鋭いエッジは、スムーズシェーディングで縁が筋っぽく汚れて見えることがあります。円柱の端面の
縁がその典型で、MC でも DC でも起きます。形そのものは正確で、ほんの少し丸めるだけで陰影が素直に
つながり、縁がきれいに見えるようになります。

スタックの一覧の下に新しく追加した **Edges (All Primitives)** の欄で、ツリー全体にまとめて設定できます。

1. エッジの形を選ぶ(Round / Sharp / Soft / Tight / Chamfer)
2. 大きさを **Voxels**(初期値 2。解像度に合わせて変わります)か、決まった **Distance** で指定する
3. **Apply Edge All** を押す

すべてのプリミティブに同じエッジが入ります。あとから一つずつ変えることもできます。
**Also round Subtract / Intersect seams** をオンにすると、Subtract で開けた穴の縁なども一緒に丸まります。

### 🐛 四角錐の底面が平らになりました

**Pyramid** の底面が細かい階段状になり、置いた高さからずれていました。GeoRemesh_R を使うと、
Cycles で黒い模様になることもありました。今回から、MC・DC・プレビューのどれでも、底面が置いた
位置にぴったり平らに出ます。

四角錐を使っているファイルでは、底面の見た目が少し変わります(よりきれいになります)。

### ⚠️ Windows では、これまでと同じ順番で更新してください

1. **Edit → Preferences → Add-ons** で SDF.R を**無効**にする
2. **Blender を再起動**する
3. V17.0.5 の zip をインストールして、有効にする

パネルに「**Engine version mismatch**」と出たら、上の3手順をもう一度行ってください。macOS /
Linux はこれまでどおり上書きインストールで問題ありません。

Windows / macOS(Apple Silicon)/ Linux 版すべて公開済みです。
