# SDF.R V17.0.4 — Update Announcement Email

Ready to copy and paste. The English version comes first (for Superhive / Blender Market / Gumroad buyers), and the Japanese version follows.

> **V17.0.3 のときとの違い:** 今回は小さな修正リリースです。影響するのは、**GPU Chunked MC** を自分で選んでいる人と、
> GPU のメモリが少なく **AUTO** がチャンク処理に切り替わる人だけです。普段の使い方で問題が出ていなかった人には、
> 見た目の変化はありません。
>
> - V17.0.3 からすぐ続けての更新になるので、「V17.0.3 を入れた直後の人も、もう一度更新を」と一言入れると親切です。
> - Windows の更新手順は V17.0.3 と同じです(無効化 → 再起動 → インストール)。毎回書いておくのが安全です。
> - 告知を短くしたい場合は、V17.0.3 と V17.0.4 をまとめて1通にする手もあります。V17.0.3 をまだ告知していない
>   なら、そのほうが受け取る側の負担が少なく済みます。

---

## Subject line options

1. `SDF.R V17.0.4 — No more seam holes in chunked meshes`
2. `SDF.R V17.0.4 is out (free update) — a small fix for GPU Chunked MC`

**Japanese subject:** `SDF.R V17.0.4 公開 — GPU Chunked MC の継ぎ目の穴を修正しました`

---

## Body (English)

Hi, and thank you for supporting SDF.R.

**V17.0.4 is now available as a free update for all owners.** It's a small fix release that
follows straight on from V17.0.3, so even if you installed V17.0.3 just recently, please update
once more.

### 🐛 No more seam holes in chunked meshes

At some resolutions, the **GPU Chunked MC** backend left a row of small holes along a straight line
across the model, where it splits the work into chunks. **AUTO** could produce them too, because it
switches to GPU Chunked MC when the GPU doesn't have enough memory for a single pass.

The cause was a chunk's sampling grid sitting half a voxel off its neighbours, too far apart for
Weld to join. Every chunk now lines up exactly, so the seams close. On our test scene the result is
now identical to the mesh made without chunks. Resolutions that were already clean give exactly
the same mesh as before.

If you never saw holes like these, nothing changes for you.

### ⚠️ Updating on Windows — same order as V17.0.3

1. **Edit → Preferences → Add-ons**, and **disable** SDF.R.
2. **Restart Blender.**
3. Install the V17.0.4 zip and enable SDF.R.

If the panel shows **Engine version mismatch**, repeat the three steps. macOS and Linux can install
over the previous version as usual. Existing files open unchanged.

Windows, macOS (Apple Silicon) and Linux builds are all available.

---

## Body (日本語)

いつも SDF.R をご利用いただきありがとうございます。

**V17.0.4 を公開しました。既存ユーザーの方は無償アップデートです。** V17.0.3 に続く小さな修正
リリースです。V17.0.3 を入れたばかりの方も、もう一度更新をお願いします。

### 🐛 チャンク処理したメッシュの継ぎ目の穴を修正しました

**GPU Chunked MC** を使うと、一部の解像度で、モデルを分割処理する境目に沿って小さな穴が一列に
並ぶことがありました。GPU のメモリが足りないときは **AUTO** もこの方式に切り替わるため、同じ穴が
出ることがありました。

原因は、一部のチャンクの格子が隣のチャンクから半ボクセルずれていて、Weld でつなげない距離に
なっていたことです。今回からすべてのチャンクの格子がそろうようになり、継ぎ目が閉じます。テスト
用のシーンでは、チャンクに分けずに作ったメッシュと完全に同じ結果になりました。もともと穴が
出ていなかった解像度では、結果はこれまでとまったく変わりません。

このような穴を見たことがなければ、今回の更新で変わることはありません。

### ⚠️ Windows では、V17.0.3 と同じ順番で更新してください

1. **Edit → Preferences → Add-ons** で SDF.R を**無効**にする
2. **Blender を再起動**する
3. V17.0.4 の zip をインストールして、有効にする

パネルに「**Engine version mismatch**」と出たら、上の3手順をもう一度行ってください。macOS /
Linux はこれまでどおり上書きインストールで問題ありません。既存のファイルはそのまま開けます。

Windows / macOS(Apple Silicon)/ Linux 版すべて公開済みです。
