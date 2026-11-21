# SDF.R V17.0.3 — Update Announcement Email

Copy-paste ready. English version first (for Superhive / Blender Market / Gumroad buyers),
Japanese version below.

> **V17.0.2 のときとの違い:** 今回も**修正リリース**ですが、全員に伝えるべき点が2つあります。
>
> 1. **Windows の更新手順が変わります。** 有効なまま上書きインストールすると、エンジン(pyd)
>    だけ旧版のまま残ります。「無効化 → Blender 再起動 → インストール」の順を必ず書いてください。
> 2. **Live Normals が効くようになり、High プリセットの見た目が変わります。** 既定で
>    「High で Live Normals を自動 ON」なので、High を押すとカスタム法線が付き、Finalize 後も残ります。
>
> 黒点の修正は、Weld ON(既定)で Marching Cubes を使っている人全員が対象です。

---

## Subject line options

1. `SDF.R V17.0.3 — No more black spots with Weld on`
2. `SDF.R V17.0.3 is out (free update) — welded meshes shade cleanly, and Live Normals works`

**Japanese subject:** `SDF.R V17.0.3 公開 — Weld ON 時の黒点を修正しました(Windows は更新手順にご注意ください)`

---

## Body (English)

Hi, and thank you for supporting SDF.R.

**V17.0.3 is now available as a free update for all owners.** It's a fix release, with one
change to how you update on Windows — please read that part before installing.

### 🐛 No more black spots with Weld on

With **Weld (Merge)** on — the default — Marching Cubes meshes could show small black dots and
dark wedges on smooth areas. They came from tiny "needle" triangles that Weld joined into the
mesh while they faced the wrong way. Weld now repairs them, closes the tiny seam holes left by
rounding noise, and no longer leaves stray loose vertices in Snapshot and Finalize results.
Same shape, same face count.

### ✨ Live Normals now actually works

**Live Normals** was supposed to give the mesh smooth shading taken straight from the SDF, but
Blender 4.1 and newer were silently ignoring it. It now writes real custom normals.

Heads-up: **Auto-enable Live Normals on High** is on by default, so pressing **High** now gives
the mesh custom normals, and Finalize keeps them. If you plan to keep editing a finalized mesh by
hand, turn Live Normals off before finalizing.

### ⚠️ Updating on Windows — please do it in this order

1. **Edit → Preferences → Add-ons**, and **disable** SDF.R.
2. **Restart Blender.**
3. Install the V17.0.3 zip and enable SDF.R.

If you install over an enabled add-on, Windows keeps the old engine file in place and you get a
mix of old and new. SDF.R now detects this and shows **Engine version mismatch** in the panel —
if you see it, just repeat the three steps.

macOS and Linux can install over the previous version as usual. Existing files open unchanged.

Windows, macOS (Apple Silicon) and Linux builds are all available.

---

## Body (日本語)

いつも SDF.R をご利用いただきありがとうございます。

**V17.0.3 を公開しました。既存ユーザーの方は無償アップデートです。** 修正リリースですが、
Windows での更新手順に1点変更があります。インストール前にその部分だけお読みください。

### 🐛 Weld ON 時の黒点を修正しました

**Weld (Merge)** が ON(既定)のとき、Marching Cubes のメッシュの滑らかな部分に、小さな黒い点や
くさび状の暗い影が出ることがありました。原因は、向きが裏返った極細の三角形が Weld によって
周りとつながっていたことです。今回の更新で Weld がこれを修正するようになりました。あわせて、
丸め誤差でできていた小さな継ぎ目の穴を閉じ、Snapshot や Finalize の結果に余分な孤立頂点が
残らないようにしました。形と面数は変わりません。

### ✨ Live Normals が効くようになりました

**Live Normals** は SDF から求めた滑らかな法線でメッシュを表示するための機能ですが、
Blender 4.1 以降では反映されていませんでした。今回から本当のカスタム法線を書き込みます。

ご注意: 「**Auto-enable Live Normals on High**」が既定で ON のため、**High** を押すとメッシュに
カスタム法線が付き、Finalize 後もそのまま残ります。Finalize 後にメッシュを手作業で編集する
予定がある場合は、Finalize の前に Live Normals を OFF にしてください。

### ⚠️ Windows では、この順番で更新してください

1. **Edit → Preferences → Add-ons** で SDF.R を**無効**にする
2. **Blender を再起動**する
3. V17.0.3 の zip をインストールして、有効にする

有効なまま上書きインストールすると、Windows がエンジンのファイルを置き換えられず、新旧が
混ざった状態になります。今回から SDF.R がこれを検出し、パネルに「**Engine version mismatch**」と
表示します。表示されたら、上の3手順をもう一度行ってください。

macOS / Linux はこれまでどおり上書きインストールで問題ありません。既存のファイルはそのまま
開けます。

Windows / macOS(Apple Silicon)/ Linux 版すべて公開済みです。
