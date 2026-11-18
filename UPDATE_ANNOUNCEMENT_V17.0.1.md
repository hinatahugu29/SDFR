# SDF.R V17.0.1 — Update Announcement Email

Copy-paste ready. English version first (for Superhive / Blender Market / Gumroad buyers),
Japanese version below.

> **V17.0.0 のときとの違い:** 前回はメジャーアップデート(ギズモ)でした。**今回は小さな修正
> リリース**です。新機能はありません。Snapshot MeshやFinalizeで確定したはずのメッシュの色が、
> その後ライブ側を触ると一緒に変わってしまう、という不具合の修正です。
>
> **対象は Snapshot Mesh / Finalize を使っている人だけ**です。使っていない人には見える
> 変化がありません。

---

## Subject line options

1. `SDF.R V17.0.1 — Snapshot Mesh and Finalize now keep their own material`
2. `SDF.R V17.0.1 is out (free update) — a frozen snapshot wasn't actually frozen`

**Japanese subject:** `SDF.R V17.0.1 公開 — Snapshot/Finalizeの色がライブ側と連動してしまう不具合を修正しました`

---

## Body (English)

Hi, and thank you for supporting SDF.R.

**V17.0.1 is now available as a free update for all owners.** It's a small fix release: one bug,
fixed.

### 🐛 A frozen snapshot wasn't actually frozen

If you used **Snapshot Mesh** or **Finalize (Bake All)** and later noticed the frozen copy's
**colors change along with the live tree** — that was a real bug, and it's fixed.

Snapshotting or finalizing duplicated the mesh, but not the material it used — both ended up
pointing at the exact same material, so a later Reset or Apply Material All on the live tree
changed the "frozen" copy too. A new tree could also silently inherit an old material left behind
by a past Finalize, if it happened to land on a reused output name.

**Nothing you've already saved changes.** This only affects what happens the next time you press
Snapshot Mesh or Finalize — existing files keep whatever material they already have.

### Upgrading

Install over V17.0.0 as usual. No migration needed.

Windows, macOS and Linux builds are all available.

---

## Body (日本語)

いつも SDF.R をご利用いただきありがとうございます。

**V17.0.1 を公開しました。既存ユーザーの方は無償アップデートです。** 修正1件のみの小さな
リリースです。

### 🐛 「凍結したはずのスナップショット」が実は凍結していませんでした

**Snapshot Mesh** や **Finalize (Bake All)** を使った後、確定したはずのメッシュの色が
**ライブ側の編集と一緒に変わってしまう**現象に気づいた方がいらっしゃるかもしれません。これは
実在する不具合で、今回修正しました。

SnapshotやFinalizeはメッシュ自体は複製していましたが、使っているマテリアルまでは複製して
いませんでした。そのため両者が全く同じマテリアルを指したままになっており、後でライブ側で
ResetやApply Material Allを押すと、「確定したはず」の側まで一緒に変わっていました。また、
出力名がたまたま使い回された場合、新しいツリーが過去のFinalizeで残っていた古いマテリアルを
静かに引き継いでしまうこともありました。

**既に保存済みのファイルには影響ありません。** 今回の修正が効くのは、次に Snapshot Mesh や
Finalize を押した時からです。

### アップデート方法

V17.0.0 に上書きインストールしてください。移行作業は不要です。

Windows / macOS / Linux 版すべて公開済みです。
