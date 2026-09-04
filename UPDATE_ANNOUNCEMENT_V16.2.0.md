# SDF.R V16.2.0 — Update Announcement Email

Copy-paste ready. English version first (for Superhive / Blender Market / Gumroad buyers),
Japanese version below.

---

## Subject line options

1. `SDF.R V16.2.0 — Layer Boundary now keeps shapes apart`
2. `SDF.R V16.2.0 is out (free update) — hard boundaries between groups`
3. `[SDF.R] V16.2.0 released — if Layer Boundary never seemed to do anything, this is why`

*Recommended: option 1 — it names the feature and the outcome, which is what anyone who tried Layer
Boundary and gave up will recognise.*

---

## Body (English)

Hi, and thank you for supporting SDF.R.

**V16.2.0 is now available as a free update for all owners.**

This release is about one feature that has never worked the way its name suggests: **Layer
Boundary**.

### 🧱 Layer Boundary now produces a hard boundary

A layer boundary builds its group on its own and then merges the finished shape into the scene
once. That much always worked. The merge itself did not: it was a smooth union, and the blend
radius came from **whichever primitive happened to come first in the group.**

That value was doing two jobs, and hiding one of them. Inside the group, the first primitive's
Smoothness does nothing — there is nothing for it to blend against yet. So the number looked inert
while you shaped the group, and then quietly decided how the whole group met the rest of the model.
With the default of 0.2 sitting on that first shape, switching Layer Boundary on gave you a group
that melted into the scene as one soft lump — the opposite of a boundary.

If you turned Smoothness down trying to fix it, you had the right idea and the wrong control. And
if the shape you turned down was not the first in the group, it did nothing at all.

The divider now carries its own **Layer Blend**, and it defaults to **0.0** — a hard seam. Raise it
if you want the group to settle into the scene instead. **Primitive Smoothness is untouched**,
including the way a new primitive inherits it from the previous one. Shapes inside a group still
blend with each other exactly as before.

### 📐 A layer now covers the group above its divider

Group layout — Radial, Grid, Mirror and the rest — and stack parenting have always acted on the
rows **above** a divider. The layer acted on the rows **below** it. One divider, two different
groups, depending on which feature you were thinking about.

They now agree: a divider closes the group above it.

**This does change existing files that use Layer Boundary**, in both of the ways above. The groups
have shifted, and the seams are now hard. The new behaviour is what the feature was always meant to
do, so the fix is usually to leave it — but Layer Blend is there if you want the old softness back,
and 0.2 reproduces the old default exactly.

### 🐛 And the fixes that came with it

- **Layout on a layer boundary no longer disappears.** A divider carrying Radial or Grid threw its
  layout away entirely the moment Layer Boundary was switched on. The two now work together.
- **The ghost preview and the mesh agree on layers.** The rules live in three places — the CPU
  mesher, the GPU mesher, and the preview shader. All three now match.
- **Move to SDF**, three separate faults: it picked its destination collection from the first output
  object it happened to find, so a scene with more than one SDF output sent objects somewhere
  unpredictable; it could leave the old link behind for an object that belonged to several
  collections; and when an object's name matched none of the shapes it knows, it fell back to a
  sphere without saying so. It now uses the active output, relinks cleanly, and tells you which
  objects it had to guess at.

### The part worth knowing before you try it

Layer Boundary takes **one divider per part**. A single layer on its own does very little, for two
reasons that are the same reason twice: the first layer merges into an empty scene, so its Layer
Blend has nothing to act on — and any shape left outside every layer still blends freely into
whatever the layers merged into.

So for a character whose eyes, eyelids and shell should not melt into the body, every one of those
parts gets its own divider, the body included:

```text
01 Body A
02 Body B
== Layer: Head ==     Layer Boundary on
03 Eye L
04 Eye R
05 Eyelid / Subtract  cuts the eyes only — the body is in another layer
== Layer: Eyes ==     Layer Boundary on, Layer Blend 0.0
06 Shell
== Layer: Shell ==    Layer Boundary on
```

One thing to be clear about: merging a layer is always a Union. Layer Boundary stops shapes from
blending, but overlapping shapes still form one connected solid. If you need the eyes as a separate
mesh object, build them as a second SDF output.

The user guide's chapter on Collection Divider and Layer Boundary has been rewritten around all of
this, and Workflow Examples gains a section on keeping parts apart.

### Upgrading

Install over the previous version as usual. Clearing the shader cache is not required. Windows,
macOS and Linux builds are all available.

This came out of a user writing in to ask whether eyes and eyelids could be kept from smoothing
together. The honest answer at the time was "yes, but only if you also know which primitive's
Smoothness secretly controls the seam" — which is not an answer. Thank you for asking; it is a
better feature now.

— hinata_hugu

---

## Body (Japanese / 日本語版)

いつもSDF.Rをご利用いただきありがとうございます。

**V16.2.0を、すべての購入者向けの無償アップデートとして公開しました。**

今回は、名前どおりに動いていなかった機能 **Layer Boundary** の作り直しが中心です。

### 🧱 Layer Boundaryが、本当に「境界」になりました

Layer Boundaryは、グループを別建てで評価してから、出来上がった塊を一度だけシーンへ合流させる機能です。
ここまでは以前から正しく動いていました。問題は合流のしかたで、これがスムーズUnionであり、
そのブレンド半径が**そのグループで最初に現れたプリミティブのSmoothness**から取られていました。

この値は二役を演じたうえ、片方を隠していました。グループの内部では、先頭プリミティブのSmoothnessは
何も変えません（まだ混ぜる相手がいないため）。つまり形を整えている間はまったく効かないように見えて、
その裏でグループ全体と本体の接続だけを決めていたわけです。既定値0.2のままLayer Boundaryを
ONにすると、グループはひと塊になって本体にぬるっと溶ける——境界とは逆の結果になっていました。

Smoothnessを下げて直そうとされた方は、考え方は正しく、触る場所だけが違っていました。しかも
下げた形がグループの先頭でなければ、何も起きませんでした。

Dividerが専用の **Layer Blend** を持つようになり、既定値は **0.0**（＝硬い境界）です。馴染ませたい
ときだけ上げてください。**プリミティブ側のSmoothnessと、新規追加時に前の値を引き継ぐ挙動は
変更していません。** グループ内部のブレンドもこれまでどおりです。

### 📐 レイヤーの範囲がDividerの「上」になりました

Group Layout（Radial / Grid / Mirrorなど）とスタックの親子付けは、以前からDividerの**上**の行を
対象にしていました。一方でレイヤーだけがDividerの**下**に効いていました。ひとつのDividerの設定が、
機能ごとに別のグループへ効いていたことになります。

これを「Dividerは上のグループを締めくくる」に統一しました。

**Layer Boundaryを使っている既存ファイルは、上記2点の影響で見た目が変わる場合があります。**
グループの範囲がずれ、境目が硬くなります。新しい挙動が本来意図していたものなので基本はそのままで
問題ありませんが、以前の柔らかさに戻したい場合はLayer Blendを0.2にしてください。

### 🐛 同時に直した不具合

- **レイアウト付きDividerでLayer BoundaryをONにするとレイアウトが消える問題**を修正しました。両方を
  同じDividerで使えます。
- **ゴーストプレビューと確定メッシュのレイヤー挙動を一致させました。** レイヤーの処理はCPU側、GPU側、
  プレビュー用シェーダーの3箇所にあり、3つとも揃えています。
- **Move to SDF** の3件: 出力オブジェクトが複数あるシーンで行き先が不定になる問題、複数コレクションに
  所属するオブジェクトで元のリンクが残る問題、そして名前から形状を判定できないときに無言で球になる
  問題（対象を警告で知らせるようになりました）。

### 使う前に知っておくと早い点

Layer Boundaryは **分けたい部品の数だけDividerを立てて** 初めて効きます。単独ではほとんど効果が
ありません。理由は2つですが、同じことの裏表です。最初のレイヤーは空のシーンに注がれるので
Layer Blendが効く相手がいないこと、そして**レイヤーに入れなかった形は、合流後の塊に普通に
ブレンドしてしまう**ことです。

目・まぶた・殻を本体と融合させたくない場合は、本体も含めて全部にDividerを立てます。

```text
01 頭 A
02 頭 B
== Layer: Head ==     Layer Boundary ON
03 目 L
04 目 R
05 まぶた / Subtract   目だけを削る。本体は別レイヤーなので無傷
== Layer: Eyes ==     Layer Boundary ON, Layer Blend 0.0
06 殻
== Layer: Shell ==    Layer Boundary ON
```

ひとつ明確にしておくと、レイヤーの合流は必ずUnionです。Layer Boundaryが止めるのは「境目が溶ける
こと」であって、「くっつくこと」ではありません。目を独立したメッシュにしたい場合は、SDF出力
オブジェクト自体を2つに分けてください。

ユーザーガイドの「Collection Divider / Layer Boundary」の章はこの内容で全面的に書き直し、
Workflow Examplesにも部品を分けるための章を追加しています。

### アップデート方法

これまでどおり上書きインストールしてください。シェーダーキャッシュの削除は不要です。
Windows / macOS / Linux 版すべて用意しています。

今回の改修は、「目とまぶたを融合させずに配置できないか」というお問い合わせがきっかけでした。
当時の正直な答えは「できます。ただし、どのプリミティブのSmoothnessが裏で境目を決めているかを
知っていれば」というもので、それは答えになっていませんでした。ご指摘ありがとうございました。

— hinata_hugu
