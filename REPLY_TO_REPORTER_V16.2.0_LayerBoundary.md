# 個別返信案 — 「Move to SDF が動かない / コレクション内でスムーズさせない方法」（V16.2.0版）

報告原文（2026-09）:

> Hi again, I noticed that the "Move to SDF" button may not be functioning correctly. Also, is it
> possible to prevent objects within a collection from being smoothed together? For example, I
> would like the eyes and eyelids, or the shell, to remain separate rather than merging and
> smoothing.

**英語版が送付用、日本語は確認用の参考訳です。**

この案は [REPLY_TO_REPORTER_V16.1.4_MoveToSDF_Smoothing.md](REPLY_TO_REPORTER_V16.1.4_MoveToSDF_Smoothing.md)
の全面改稿です。旧案は「Layer Boundary ON ＋ グループ先頭プリミティブの Smoothness を 0」という
2ステップの回避策を案内していましたが、V16.2.0 でその必要がなくなり、かつ**グループの範囲が
Divider の上下で逆になった**ため、旧案のまま送ると誤った手順を教えることになります。**旧案は送らないでください。**

**送付は V16.2.0 の公開後にしてください。** 内容が「直しました」で構成されているためです。

---

## 送付用（English）

Hi,

Thank you for both of these, and for waiting. The second question turned out to be a much better
question than it looked, so I will start there.

### Keeping the eyes, eyelids and shell separate

**Yes — and when you asked, my honest answer would have had to be "yes, but the feature does not
actually do that yet."** Looking into it properly, the control you needed existed but did not
work the way its name promised. I have rebuilt it, and it is out now as **V16.2.0**, a free update.

Here is what was wrong, because it explains why nothing you tried would have worked.

The feature is **Layer Boundary**, a toggle on a collection divider. It evaluates a group on its
own and then merges the finished shape into the model. That part always worked. But the merge
itself was a smooth blend, and the strength of that blend was taken from the Smoothness of
whichever shape happened to be first in the group. That value does nothing inside the group, so it
looked like a dead control while you were working, and then quietly decided how the entire group
met the rest of your model. With the default Smoothness of 0.2, switching Layer Boundary on gave
you a group that fused into one lump and blended into the body — which is precisely what you were
trying to avoid.

If you had tried turning Smoothness down, you would have had the right instinct and the wrong
control — and unless the shape you turned down was the first in the group, it would have done
nothing at all.

**In V16.2.0 the divider carries its own Layer Blend, and it defaults to 0 — a hard boundary.**
Turning Layer Boundary on is now enough.

The one thing worth knowing before you try it: **it takes one divider per part, including the
body.** A single layer on its own does very little, because a shape left outside every layer still
blends freely into whatever the layers have merged into. So if the body is not itself a layer, it
will melt into the eyes no matter what you do to the eyes.

For your snail:

```text
01 Body A
02 Body B
== Layer: Head ==     Layer Boundary on
03 Eye L
04 Eye R
05 Eyelid / Subtract  cuts the eyes only — the body is in another layer
== Layer: Eyes ==     Layer Boundary on
06 Shell
== Layer: Shell ==    Layer Boundary on
```

**The divider closes the group above it** — everything from the previous divider down to this one.
(If you have used Layer Boundary before, this is the other change in V16.2.0: it used to be the
rows below. Existing files may look different, and moving the divider is usually the fix.)

Inside each group, shapes still blend with each other exactly as before, so the eyes and eyelids
can be as soft together as you like. The eyelid set to Subtract now carves the eyes and nothing
else. If you *want* a part to settle into the body a little, raise that divider's Layer Blend.

One thing to be clear about: merging a layer is always a Union. Layer Boundary stops shapes from
blending, but overlapping shapes still form one connected solid — it will not give you the eyes as
a separate object. If you need that, for separate materials or to animate them independently,
build the eyes as a second SDF output object instead.

Two problems I mentioned might exist are also fixed: a divider with a layout (Radial, Grid) no
longer loses that layout when Layer Boundary is on, and a layer no longer ends unexpectedly at the
next divider.

### Move to SDF

I could not reproduce a definite fault here, so I want to ask rather than guess — but I did find
three real problems in that button while looking, and all three are fixed in V16.2.0.

**The most likely explanation is a limitation rather than a bug.** Move to SDF has to decide which
analytic SDF shape your object represents, and it does that from the object's *name* — box, cube,
torus, cylinder. Anything else becomes a sphere. There is no mesh-based SDF shape in the addon yet,
so an arbitrary sculpted or imported mesh cannot be brought in this way at all: it turns into a
sphere sitting where your mesh was. Until now it did this in complete silence, which is what makes
it look like the button failed. **It now tells you which objects it had to guess at**, so if this
was what you hit, V16.2.0 will say so plainly.

The other two were genuine bugs: it picked its destination from the first SDF output object it
happened to find, so a scene with more than one output sent objects to an unpredictable collection;
and it could leave the old collection link in place for an object that belonged to several.

If you were using a basic named shape and it still went wrong, please tell me the object's name and
what you expected, and I will look again.

### Getting the update

V16.2.0 is a free update for all owners, on Windows, macOS and Linux. Install it over the previous
version as usual — no cache clearing needed.

I have also rewritten the documentation chapter on this. The old version taught the feature with a
single divider, which is the one arrangement where it barely does anything, so following it exactly
produced the melted result you were describing. That was the real failure here, and your question
is what surfaced it. Thank you.

Best,

---

## 参考訳（日本語・送付しない）

### 融合させない方法

- **旧案の2ステップは不要になった。** V16.2.0 では Layer Boundary を ON にするだけで硬い境界になる
  （Divider が専用の Layer Blend を持ち、既定 0.0）
- 効かなかった理由を正直に説明している。合流の強さが「グループ先頭プリミティブの Smoothness」から
  取られており、その値はグループ内部では何も変えないため、触っても無反応に見えながら裏で境目を
  決めていた。既定 0.2 なので ON にしただけでは溶けた
- **本体も含めて、分けたい部品の数だけ Divider を立てる**必要がある点を明記。レイヤーに入れなかった
  形は合流後の塊に普通にブレンドするため、本体を野放しにすると効かない
- **グループは Divider の上**。旧案では「下」と説明していたので、ここが逆になっている
- 合流は必ず Union なので、くっつくことは止められない。目を別オブジェクトにしたいなら SDF 出力を分ける
- 旧案で「既知の制限」として詫びていた2件（レイアウト消失／レイヤーが次の divider で切れる）は解消済み

### Move to SDF

- **原因は依然として未確定**。断定せず、オブジェクト名を聞く構成は旧案から維持
- 最有力は「任意メッシュを取り込もうとした」という制限。これは未解決だが、**無言で球になるのをやめて
  警告を出す**ようにしたので、次回は利用者自身が切り分けられる
- 実在した2件（行き先が不定／リンクが残る）は修正済みとして開示

### 末尾

- ドキュメントが単独 Divider で教えていたこと自体が今回の失敗の本体だった、と認めている

---

## 送る前の確認事項

1. **V16.2.0 の公開後に送ること。** 「直しました」で構成されているため、公開前に送ると入手できない
2. **Blender 実機での GPU パス確認が未了。** プレビューとベイクの一致を目視してから送ってください
3. 報告者の OS が不明。Mac / Linux 版も CI でビルド済みなので、どの環境でも案内できます
4. 「私の答えは答えになっていなかった」というトーンで書いています。過剰だと感じる場合は、
   最初の段落と末尾を削るだけで事実ベースの報告に落とせます
5. Move to SDF について、報告者が何を選択していたかを聞く形は旧案から維持しています。バグと
   決めつけない構成です
