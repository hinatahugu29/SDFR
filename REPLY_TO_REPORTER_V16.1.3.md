# 個別返信案 — V16.1.3 の報告者へ

報告原文（2026-08）の4点すべてに触れる構成。**英語版が送付用、日本語は確認用の参考訳です。**

送る前に確認していただきたい点は末尾にまとめています。

---

## 送付用（English）

Hi,

Thank you for this — it was one of the most useful messages I have had about SDF.R, and two of
the four things you raised are fixed in **V16.1.3**, which is out now as a free update.

### The Symmetry / Boolean problem — found, and it was my bug

You were right, and you described it precisely: the cut showed in the preview and not in the
final mesh.

The cause was in mesh generation, not in Booleans as such. Before sampling the scene, SDF.R works
out the region of space it needs to look at. With a symmetry axis enabled it was clamping that
region to the positive half of the axis, and the meshing shaders were not folding primitive
positions onto the mirrored side the way the preview shader does. Between the two, **any shape
whose centre sat on the negative side of the symmetry plane was dropped before meshing began.**

That is why it looked like a Boolean problem. With a single shape on the negative side you get an
empty mesh and something is obviously wrong. With a Boolean, the base solid still meshes
perfectly and only the cut vanishes — no error, nothing to go on, and the preview still showing
you the cut you asked for.

Measured with a Subtract sphere cutting a box, Symmetry X on:

- cut placed at X = +2 → correct result, both before and after
- cut placed at X = −2 → **before: the uncut box. After: identical to the +2 case.**

Intersect behaved the same way. Both are fixed, and the fix is in the Windows, macOS and Linux
builds. If you had shapes on the positive side only, you would never have seen this — which is
part of why it took an outside report to find.

### Selecting layers in The Stack

Also fixed. Only the layer's *name* was clickable before; anywhere else in the row moved the
highlight but left the viewport selection alone, so the panel and the scene disagreed about what
you had selected. The whole row now selects, as you would expect. Selecting objects in the
viewport still updates the panel the other way, and a multi-selection made in the viewport is
preserved.

### Baking the GPU preview mesh

Here I need to ask you something, because there may already be a button for what you want and I
would rather find out than build a second one.

SDF.R has **Bake Mesh**, **Generate Mesh** and **Finalize** — these turn the SDF result into a
regular Blender mesh. If you did not find them, that is a UI problem worth fixing on my side, and
knowing where you looked would help.

But if you mean something different — for example converting what the Ghost Preview is showing
right now, at preview quality and preview speed, rather than running a full generation — that is
a separate feature and a reasonable request. Could you tell me which of the two you had in mind?

### A tutorial on a real project

Fair, and I agree. The written documentation covers the controls but not the judgement calls, and
those are the hard part. I cannot promise a date, but it is on the list and your message moved it
up.

### Navigating the stacks

You also mentioned that organising collections to separate parts gets tricky. I have not changed
anything there yet, and I would like to. If you have a concrete moment where it got in your
way — what you were trying to do, and what you had to do instead — that would help me a lot more
than my own guesses.

Thanks again for taking the time to write all of this out. It is genuinely the sort of report
that makes the add-on better.

— hinata_hugu

---

## 参考訳（確認用・送付しません）

いただいたご報告、ありがとうございます。SDF.R について頂いた中でも特に有益なもので、4点のうち
2点は **V16.1.3**（無償アップデート、公開済み）で修正しました。

**対称化とブーリアンの問題** — ご指摘のとおりで、原因は私のコードでした。「プレビューには出るが
最終メッシュに出ない」という表現も正確でした。

原因はブーリアンそのものではなくメッシュ生成側です。SDF.R はサンプリング前に「空間のどこを見るか」
を決めますが、対称軸が有効なときにその範囲を正側だけに切り詰めており、さらにメッシュ生成用シェーダーが
プレビュー用シェーダーと違ってプリミティブ位置を対称側へ折り返していませんでした。この2つにより、
**対称面の負側に中心があるプリミティブが、メッシュ生成の前に捨てられていました。**

ブーリアンの問題に見えた理由もここにあります。単体形状が負側にあると空メッシュになって明らかに
異常だと分かりますが、ブーリアンでは土台が正常にメッシュ化され、切り欠きだけが消えます。エラーも
出ず、プレビューには切り欠きが表示され続けます。

（以下、箱を球で減算した実測値、スタック選択の修正、ベイクについての逆質問、チュートリアル、
コレクション整理についての追加ヒアリング。英語版と同内容）

---

## 送信前の確認事項

1. **チュートリアルの表現** — 「on the list」「moved it up」と書いています。約束と受け取られたくない
   場合は弱めてください
2. **ベイクの逆質問** — 「既にあるかもしれない」と正直に書いています。UI で見つけられなかったのなら
   こちら側の問題、というスタンスです。この立て方でよいかご確認ください
3. **スタック整理の追加ヒアリング** — 原文1点目の前半（コレクション整理のしづらさ）は具体策が
   まだ無いため、事例を伺う形にしています。今回は触れない方針であれば削除してください
4. **クーポンや謝礼**の類は入れていません。付ける場合は末尾に追記してください
