# 個別返信案 — 「Move to SDF が動かない / コレクション内でスムーズさせない方法」

報告原文（2026-09）:

> Hi again, I noticed that the "Move to SDF" button may not be functioning correctly. Also, is it
> possible to prevent objects within a collection from being smoothed together? For example, I
> would like the eyes and eyelids, or the shell, to remain separate rather than merging and
> smoothing.

**英語版が送付用、日本語は確認用の参考訳です。** 実装側の対応は
[NEXT_TASKS_MoveToSDF_and_Layering.md](NEXT_TASKS_MoveToSDF_and_Layering.md) に次回着手案としてまとめています。

---

## 送付用（English）

Hi,

Thanks for both of these — the second one in particular is a good question, and the honest answer
is that the feature you want exists but needs two settings together, neither of which is named
well enough to guess. That is on me.

### Move to SDF

**Move to SDF only understands the basic primitive shapes.** It looks at the object you selected,
moves it into the SDF collection, and then has to decide which analytic SDF shape it represents —
sphere, box, torus, cylinder. It currently makes that decision from the object's name, and
anything it does not recognise silently becomes a sphere. There is no mesh-based SDF shape in the
addon yet, so an arbitrary sculpted or imported mesh cannot be brought in this way at all; it will
turn into a sphere sitting where your mesh was.

So if you selected something other than a default-named Cube / Sphere / Torus / Cylinder, what you
saw is the current limitation rather than a fault in your file. If you *were* using a basic shape
and it still went wrong, please tell me the object's name and I will look again — I have found two
smaller issues in that operator while checking this (it picks the wrong destination when a scene
holds more than one SDF output object, and it can leave a stale link behind when the object
belonged to several collections), and both are on my list to fix.

### Keeping the eyes, eyelids and shell from merging

Yes — and here is exactly how, including the part that is easy to miss.

Turning **Smoothness** down to 0 on its own only removes the soft blend. The shapes still union
into one solid, just with a hard seam. That is not what you are asking for.

The grouping control is **Layer Boundary**, on the collection divider row. Select the divider in
the SDF stack and you will find it in the panel below the list. When it is on, everything in that
group is evaluated on its own first, and the finished group is then merged into the rest of the
scene as **one single result** rather than shape by shape.

The part that is not obvious: that final merge is itself a smooth union, and the blend radius it
uses comes from the **Smoothness of the first primitive in the group**. So with the default
Smoothness of 0.2 still sitting on that first shape, the whole group blends into the head as one
soft lump — which I suspect is close to what you were seeing.

So the recipe for your snail is:

1. Add a collection divider above the eye and eyelid shapes and switch **Layer Boundary** on. The
   group is the rows *below* that divider, down to the next divider.
2. Set the **Smoothness of the first shape in that group to 0**. That is what makes the boundary
   between the group and the head hard.
3. The other shapes in the group keep their own Smoothness, so the eyes and eyelids still blend
   with each other as much as you like.
4. Do the same for the shell, in its own divider.

Two current limitations worth knowing, both of which I am fixing:

- A group ends at the next collection divider of any kind. If you want two separate layers, give
  each one its own Layer Boundary divider rather than relying on a plain divider to close the
  previous group.
- If a divider has a layout (Radial, Grid and so on) **and** Layer Boundary switched on, the
  layout is not applied at the moment. Keep those two on separate dividers until I have fixed it.

And one thing to be clear about: the SDF result is still a single mesh object. Layer Boundary stops
the shapes from blending, but it does not give you a separate object for the eyes. If you need the
eyes as their own mesh — for separate materials, or to animate them independently — build them as
a second SDF output object instead.

You have found a real rough edge here. The behaviour is correct but the controls do not explain
themselves, and the layout interaction is a genuine bug. Both are going into the next update, and I
will document this workflow properly. Thanks again for writing in; the snail looks great.

Best,

---

## 参考訳（日本語・送付しない）

### Move to SDF

Move to SDF は**基本プリミティブしか解釈できません**。オブジェクト名から sphere / box / torus /
cylinder を判定し、該当しないものはすべて無言で球になります。メッシュベースの SDF シェイプは未実装なので、
任意のメッシュを取り込むことはそもそもできません。

デフォルト名の基本形状で失敗したのなら別問題なので、オブジェクト名を教えてほしい旨を添えています。
確認中に見つけた2件（出力オブジェクトが複数あるとき行き先を誤る／複数コレクション所属時にリンクが残る）
は修正予定として先に開示しています。

### スムージングの分離

- Smoothness=0 は「柔らかいブレンドを消す」だけで Union 自体は残り一体化する → 求めている答えではない
- Collection divider の **Layer Boundary** でグループ単位の評価になるが、**それだけでは干渉は止まらない**。
  レイヤーをシーンへ戻す合流も smooth union で、その k は**グループ先頭プリミティブの Smoothness**
  （既定 0.2）。既定のままだとグループ全体がひと塊で頭に溶ける
- 正しい手順は「Layer Boundary ON」＋「グループ先頭プリミティブの Smoothness を 0」の**2つセット**
- グループはその divider の**下**の行（次の divider まで）である点も明記
- 既知の制限2件を先に開示: (a) レイヤーは次の divider で終わる (b) レイアウト付き divider で
  Layer Boundary を ON にするとレイアウト展開が効かない（バグ）
- 出力は単一メッシュのまま。目を別オブジェクトにしたいなら SDF 出力オブジェクトを分ける必要がある

---

## 送る前の確認事項

1. Move to SDF で報告者が何を選択していたか、こちらから聞く形にしてよいか（バグ確定と決めつけない構成にしています）
2. Move to SDF の未修正2件を先に開示する方針でよいか。伏せる場合は該当段落を削ってください
3. Layer Boundary の既知の制限2件も先に開示しています。伏せると報告者が試して同じ壁に当たる可能性が高いので
   開示を推奨しますが、判断はお任せします
4. 「次のアップデートで直す」と書いています。時期は明言していませんが、確約したくなければ最終段落を調整してください
