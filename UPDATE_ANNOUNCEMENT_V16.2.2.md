# SDF.R V16.2.2 — Update Announcement Email

Copy-paste ready. English version first (for Superhive / Blender Market / Gumroad buyers),
Japanese version below.

> **V16.2.1 のときとの違い:** 前回は「できなかったことができるようになった」大きなリリースでした。
> **今回は小さな修正リリースです。** 足した機能はなく、直したのは1件、加えた警告が1件。
> 告知の目的も変わります。前回は使ってもらうため、**今回は誤解を解くため**です。
>
> V16.2.1 で Mirror Blend を試して「上げると細くなる」「上げ切ると消える」を見た人は、
> **機能が壊れていると思ったまま使うのをやめている**可能性が高い。その人に届けるのが主目的です。
> 逆に Mirror Blend を使っていない人には、見える変化がありません。**全員に急かす文面にしない**でください。

---

## Subject line options

1. `SDF.R V16.2.2 — the Mirror Blend preview now matches the mesh`
2. `SDF.R V16.2.2 is out (free update) — Mirror Blend preview fix`
3. `[SDF.R] If Mirror Blend looked broken in V16.2.1, it was the preview`

**Use option 3.** The people who need this mail are the ones who tried Mirror Blend, saw the shape
thin out or vanish, and stopped using it. They are not looking for a version number — they are
carrying a wrong conclusion about the feature. The subject has to name that conclusion for them to
recognise themselves in it.

*Option 1 is the better subject if you would rather keep the tone neutral, or for a later
re-announcement once this has gone out.*

**Japanese subject:** `SDF.R V16.2.2 公開 — Mirror Blend のプレビューが最終メッシュと一致するようになりました`

---

## Body (English)

Hi, and thank you for supporting SDF.R.

**V16.2.2 is now available as a free update for all owners.** It is a small release: one fix, and
one warning added to the panel.

### 🪞 If Mirror Blend looked broken in V16.2.1, it was the preview

V16.2.1 introduced **Mirror Blend**, which rounds off the hard crease down the middle of a mirrored
shape. If you tried it and the shape in the viewport got *thinner* as you raised the value — or
disappeared once you raised it far enough — **that was the ghost preview, not the feature.**

The generated mesh has been correct the whole time. Meshing runs on a completely separate path that
never touched the preview's code, so every mesh you produced and every file you saved on V16.2.1 is
fine. What was wrong was the live overlay.

The reason is worth a sentence, because it explains why the two disagreed rather than one simply
failing. The final mesh evaluates both mirrored halves and joins them with a smooth union, which
pushes the surface *outward* near the seam. The preview evaluates each shape only once per frame and
cannot do that, so V16.2.1 approximated the rounding by softening the mirror fold itself. That
rounds the seam *inward* — the opposite direction — and at larger values it ate the shape entirely.

**V16.2.2 fixes it.** The preview now swells as you raise Blend, in the same direction as the mesh.
It remains an approximation: measured on a mirrored sphere at radius 0.15 and offset 0.25, it sits
within about 0.02–0.12 of the mesh through the range you would normally work in, against 0.11 and
then total disappearance before. It does not round *identically* to the mesh, and it is not meant to.

**If you never used Mirror Blend, nothing you can see has changed.** At 0 the preview takes exactly
the path it always did.

### ⚠️ A warning for a setting that surprises people

**Raising Mirror Blend past twice the Offset thickens the whole shape, not just the seam.**

This is not a defect and it is not new — it is what joining two halves smoothly does. Once the blend
radius reaches across the gap between the halves, no part of the shape is far enough from the seam
to be left alone. It is confusing in practice because the axis *across* the mirror grows too, which
is not a direction the setting looks like it should touch.

The panel now tells you when your settings cross that line. If you want a rounder seam without a
heavier shape, **raise Offset rather than Blend**.

### Upgrading

Install over V16.2.1 as usual. Existing files need no migration.

One thing to expect: **the first start after updating takes longer than usual.** The GPU shader code
changed, so the cached pipeline no longer matches and is rebuilt once. On a discrete GPU that is the
usual 15–45 seconds. **On integrated graphics it can take several minutes** — an Intel Iris Xe
measured 194 seconds. The console prints `Compiling MC Pipeline...` while it works and
`GPU Engine Ready!` when it is done. Later starts take a second or two.

Windows, macOS and Linux builds are all available.

Thank you to the owner who asked whether Mirror Blend and the mesh were really connected. That
report turned out to be about something else, but measuring it is what turned this up.

---

## Body (日本語)

いつも SDF.R をご利用いただきありがとうございます。

**V16.2.2 を公開しました。既存ユーザーの方は無償アップデートです。** 修正1件と、パネルへの警告追加
1件だけの小さなリリースです。

### 🪞 V16.2.1 で Mirror Blend が壊れて見えた方へ — 原因はプレビューでした

V16.2.1 で追加した **Mirror Blend** は、ミラーした形の中央に残るハードな折れ目を丸める機能です。
これを試したときに、**値を上げるとビューポートの形が細くなる**、あるいは**上げ切ると形が消える**という
挙動をご覧になった方がいらっしゃると思います。**それはゴーストプレビュー側の不具合で、機能自体は
正しく動いていました。**

生成されるメッシュは最初から正しい状態でした。メッシュ生成はプレビューとは完全に別の経路で動いて
おり、プレビュー用のコードに一切触れていません。**V16.2.1 で作成したメッシュも、保存されたファイルも
すべて正常です。** 誤っていたのはリアルタイム表示だけです。

理由を一文だけ。最終メッシュはミラーした両側を別々に評価して Smooth Union で結合するため、継ぎ目の
付近で表面が**外側へ**膨らみます。プレビューは1フレームにつき1形状を1回しか評価できず同じことが
できないため、V16.2.1 では**折り返しそのものを鈍らせる**近似を使っていました。これは継ぎ目を
**内側へ**丸めます。向きが逆だったわけです。値が大きいと、内側への食い込みが形を完全に飲み込みます。

**V16.2.2 で修正しました。** プレビューはメッシュと同じ向きに膨らみます。ただし近似である点は
変わりません。半径0.15・オフセット0.25 のミラーした球で実測して、通常使う範囲でメッシュとの差は
0.02〜0.12 程度です（従来は 0.11、そこから先は消滅）。**完全に一致するわけではなく、一致させることを
目指してもいません。**

**Mirror Blend を使っていない場合、見える変化はありません。** 値が 0 のときは従来とまったく同じ
経路を通ります。

### ⚠️ 誤解されやすい挙動に警告を追加しました

**Mirror Blend を Offset の2倍より大きくすると、継ぎ目だけでなく形全体が太ります。**

これは不具合ではなく、また今回始まったことでもありません。両側を滑らかに繋ぐ以上、避けられない
挙動です。ブレンドの半径が両側の隙間を超えて届くと、継ぎ目から十分に離れた場所が形の中に無くなる
ためです。実際に紛らわしいのは、**ミラー軸と直交する方向まで太る**点で、この設定が触るように
見えない方向が動きます。

その範囲に入るとパネルが警告を表示するようにしました。形を太らせずに継ぎ目だけ丸めたい場合は、
**Blend ではなく Offset を上げてください。**

### アップデート方法

V16.2.1 に上書きインストールしてください。既存ファイルの移行作業は不要です。

1点だけご承知おきください。**更新後の初回起動は通常より時間がかかります。** GPU シェーダーのコードが
変わったため、キャッシュ済みのパイプラインが一致せず、1度だけ再構築が走ります。ディスクリート GPU で
通常どおり15〜45秒、**内蔵GPUでは数分かかることがあります**（Intel Iris Xe で194秒を実測）。処理中は
コンソールに `Compiling MC Pipeline...`、完了時に `GPU Engine Ready!` と表示されます。2回目以降は
1〜2秒です。

Windows / macOS / Linux 版すべて公開済みです。

Mirror Blend と最終メッシュが本当に連動しているのか、とご質問をくださった方にお礼を申し上げます。
ご指摘そのものは別の箇所についてのものでしたが、確認のために計測したことで今回の不具合が見つかりました。
