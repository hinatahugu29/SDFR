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

---

# フォローアップ返信案 — 「プレビューのベイク」について

報告者から画像付きで補足あり。「the blue mesh」＝ゴーストプレビュー（レイマーチング描画）を
指しており、"clean, sharp edges" が生成メッシュでは失われる、という趣旨。

**要点:** 青い表示はメッシュではないので「そのままベイク」は原理的にできません。ただし
「プレビューのような見た目のメッシュが欲しい」という目的なら、**既存設定でかなり詰められます。**
既定値（MC / 解像度48 / Live Normals オフ）が不利に働いている可能性が高いです。

---

## 送付用（English）

Thanks for the screenshot — that clears it up, and it changes my answer.

First, the honest part: **the blue shape is not a mesh.** It is the SDF evaluated per pixel, in
real time, by a raymarching shader. There is no geometry behind it — nothing that could be handed
to Blender as-is. That is why "bake the preview" cannot be done literally, and I would rather say
so than promise a button that cannot exist.

But what you actually want — a generated mesh that looks like that — is largely reachable today,
and I think the defaults are working against you. Three settings matter, and two of them are off
by default:

**1. Switch to Dual Contouring.** In Mesh Settings there are two buttons, Marching Cubes and Dual
Contouring. MC is the default because it gives fast feedback, but by construction it can only
place vertices along the edges of its sampling grid, so sharp creases get rounded off. Dual
Contouring exists specifically to keep them. If "clean, sharp edges" is what you are after, this
is the single biggest change.

**2. Raise the resolution.** The default is 48, which is a value chosen for responsive editing,
not for final output. There is a **High** button next to Low in Mesh Settings (256), and the
Res field goes to 1024. Above 512 the engine automatically switches to chunked meshing so it does
not run out of memory. Circular openings like the ones in your screenshot are where low resolution
shows first — they go polygonal before anything else does.

**3. Turn on Live Normals.** Part of why the preview looks so clean is that its shading normals
come from the SDF itself rather than from polygons. Live Normals does the same thing to the
generated mesh, so it shades like the preview even where the tessellation is coarser. It is off by
default because it costs time on every update. It is labelled "Live Normals (Heavy)" for that
reason, but for a final bake that cost does not matter.

Some gap will always remain. Raymarching evaluates per pixel and adapts to whatever you are
looking at; meshing samples a fixed grid and has to commit. They cannot be made identical. But
between DC, resolution and live normals, most of what you are seeing should close.

Could I ask which part degrades for you? "Sharp edges" could mean a few different things:

- creases and corners becoming rounded → that is Marching Cubes, use DC
- the circular openings turning polygonal → that is resolution
- the surface looking faceted while the silhouette is fine → that is shading, use Live Normals

If you try DC at 256 with Live Normals on and there is still a specific gap, send me a screenshot
of the two side by side. Either it is a limitation I should document properly, or it is a bug, and
I would like to know which.

— hinata_hugu

---

## 参考訳（確認用・送付しません）

まず正直にお伝えすると、**青い形状はメッシュではありません。** レイマーチングシェーダーが
リアルタイムにピクセル単位でSDFを評価した描画結果で、背後にジオメトリは存在しません。
そのため「プレビューをそのままベイクする」ことは原理的にできません。実現できないボタンを
約束するより、この点は正直にお伝えします。

ただし「プレビューのような見た目のメッシュが欲しい」という目的であれば、**現状の設定でかなり
近づけられます。** そして既定値が不利に働いている可能性が高いです。

1. **Dual Contouring に切り替える** — MC は原理上サンプリング格子の辺上にしか頂点を置けず、
   角が丸まります。DC はシャープなエッジを保つための実装です。最も効きます
2. **解像度を上げる** — 既定の48は編集時の応答性のための値です。High ボタン（256）があり、
   最大1024。512超は自動でチャンク分割されます。画像のような円形の開口部は、解像度不足が
   最初に出る場所です
3. **Live Normals をオンにする** — プレビューが滑らかに見える理由の一部は、法線をポリゴンでは
   なくSDFから取っていることです。Live Normals は生成メッシュで同じことをします。既定オフは
   毎回の更新コストのためで、最終出力なら問題になりません

そのうえで、どの部分が劣化するのかを逆質問（角が丸まる／円が多角形になる／面がファセット状に
見える、で原因が違うため）。DC・256・Live Normals で試してなお差があれば、比較画像を送って
ほしい、と締めています。

---

## 送信前の確認事項

1. **「ベイクできない」と明言しています。** 実装できないものを約束しないための書き方ですが、
   要望を突き返す印象になっていないかご確認ください。「目的は達成できる」に重心を置いています
2. **既定値が不利、という書き方**をしています。製品側の設定設計への批判とも読めるので、
   表現を和らげたい場合は「編集時の応答性を優先した既定値です」の側を強調してください
3. **逆質問を3択にしています。** 相手に切り分けを頼む形なので、負担に感じさせるようなら
   削って「比較画像を送ってください」だけにしてもよいです

## 製品側で検討の余地（今回の返信には含めていません）

報告者が既定値のまま比較していたのだとすると、**「最終出力用の設定」への導線が弱い**可能性が
あります。解像度の High ボタンはありますが、DC と Live Normals は個別に切り替える必要があります。
「Final Quality」のようなプリセット（DC + 高解像度 + Live Normals を一括）が有効かもしれません。
同種の問い合わせが続くようなら検討対象です。
