# SDF.R V16.1.2 — Update Announcement Email

Copy-paste ready. English version first (for Blender Market / Gumroad buyers),
Japanese version below.

---

## Subject line options

1. `SDF.R V16.1.2 — macOS crash fixed, and a word about the Mac and Linux builds`
2. `SDF.R V16.1.2 is out (free update) — macOS crash fix`
3. `[SDF.R] V16.1.2 released — the macOS crash is fixed, and it was my fault`

*Recommended: option 1 — it names the fix and signals the platform statement, which is the part
returning Mac and Linux users will care about.*

---

## Body (English)

Hi, and thank you for supporting SDF.R.

**V16.1.2 is now available as a free update for all owners.**

This is a bug-fix release. Nothing about mesh generation or the preview changes — the geometry
SDF.R produces is identical to V16.1.1. But one of the fixes matters, and there is something I
want to say alongside it.

### 🐛 The macOS crash is fixed — and it was mine

A user reported Blender crashing the instant they added a primitive, every time, on macOS with
Blender 5.2. It took several rounds of back and forth to find, and the answer deserves to be
stated plainly: **the fault was in SDF.R, not in their setup.**

While SDF.R waits for the mesh calculation to finish, it runs a repeating timer. That timer was
asking Blender for the scene's dependency graph — and in Blender, that request does not merely
hand one over. If Blender decides an update is due, it re-evaluates the entire scene right there.
Inside an operator that is the flow Blender expects. From a timer it begins evaluating at a
moment Blender never scheduled, and the evaluator can read past the end of its own object list.

The timer no longer forces an evaluation.

**One detail worth knowing:** with Factory Settings and only SDF.R enabled, the crash never
happened. That made it look like a conflict with another add-on, and it nearly sent me in the
wrong direction. A quiet scene simply lets the unsafe call survive. If you hit this and concluded
that something in your own setup was to blame, it was not.

**Was I affected?** Only if this specific timing lined up on your machine. It never once occurred
on my own Windows system, across both Blender 5.1 and 5.2 — which is exactly why it took an
outside report to find. If SDF.R has been stable for you, nothing changes. But the fragile call
was there in every earlier version, so this update is worth taking on any platform.

### 🖥️ About the macOS and Linux builds

I am retiring the "experimental test build" label, and I would rather explain why than quietly
change the wording.

SDF.R ships for Windows, macOS (Apple Silicon) and Linux (x86-64). All three are built from the
same source, by the same automated pipeline, in every release. They are not side projects.

I want to be straightforward about one thing: **I develop on Windows, and I do not own a Mac or a
Linux machine.** I cannot sit down and reproduce a problem on those platforms myself. What I can
do is read a crash report and fix what it points to — and that works. The crash above was found
entirely from one user's crash log.

So these platforms improve exactly as fast as people tell me things.

**That includes telling me when things work.** A crash report tells me something is broken. A
message saying "runs fine on macOS 26.6, M3 Max, Blender 5.2" tells me where the line is, and
that is just as valuable — I currently have very few of those. If SDF.R is working for you on
macOS or Linux, one sentence would genuinely help.

And if you tried SDF.R on a Mac in the past, hit this crash and gave up: please try again.

**If something breaks**, the fastest route to a fix is to launch Blender from Terminal (on macOS,
`/Applications/Blender.app/Contents/MacOS/Blender`), reproduce the problem, and send me what the
Terminal printed — plus `blender.crash.txt` from your temporary folder (`open $TMPDIR`). That
file carries the add-on's own line numbers.

### ✅ Updating — nothing to do

The GPU shader code is unchanged since V16.1.0, so **clearing the shader cache is not required**
when coming from V16.1.0 or V16.1.1.

If you are coming from **V16.0.x or earlier**, please still clear it:

1. Close Blender completely.
2. Delete `%APPDATA%\Blender Foundation\Blender\<your version>\datafiles\rust_gpu_sdf\shader_cache.bin`
3. Restart Blender. The first startup after clearing takes the full warm-up time again.

### Downloads

- **Windows:** `SDF_R_16_1_2.zip` (standard package)
- **macOS:** `SDF_R_16_1_2_MAC.zip` — Apple Silicon (arm64)
- **Linux:** `SDF_R_16_1_2_LINUX.zip` — x86-64

The macOS build is not notarized, so if Gatekeeper blocks it, open
**System Settings → Privacy & Security** and click **Open Anyway**.

Full release notes and updated documentation are on the product page.

Thanks again — and my thanks in particular to the user who kept sending logs until this was
findable.

— hinata_hugu

---

## Body (日本語)

いつも SDF.R をご利用いただきありがとうございます。

**V16.1.2 を、すべての購入者様向けの無償アップデートとして公開しました。**

今回は不具合修正のリリースです。メッシュ生成もプレビューも変更しておらず、出力される
ジオメトリは V16.1.1 と同一です。ただ、修正のひとつは重要なもので、あわせてお伝えしたいことが
あります。

### 🐛 macOS のクラッシュを修正しました。原因は私のコードでした

macOS / Blender 5.2 の環境で、プリミティブを追加した瞬間に必ず Blender が落ちる、という報告を
いただいていました。特定までに何往復もかかりましたが、結論ははっきり書くべきものでした。
**原因は SDF.R 側にあり、その方の環境の問題ではありませんでした。**

SDF.R はメッシュ計算の完了を待つ間、繰り返し動くタイマーを回しています。そのタイマーが
Blender にシーンの依存グラフを要求していました。この要求は単に受け取るだけのものではなく、
Blender が「更新が必要」と判断すれば、**その場でシーン全体を再評価します**。オペレーターの
中でならそれは Blender が想定している流れです。しかしタイマーから呼ぶと、Blender が予定して
いないタイミングで評価が始まり、評価側が自身のオブジェクト一覧の範囲外を読むことがあります。

タイマーは、評価を強制しないようになりました。

**ひとつ書いておきたいこと。** Factory Settings で SDF.R だけを有効にした状態では、
クラッシュは一度も起きませんでした。そのため他アドオンとの競合に見え、危うく調査の方向を
誤るところでした。実際には、シーンが静かだと危険な呼び出しがたまたま生き延びるだけです。
**もしこの症状に当たり、ご自身の環境に問題があると結論づけられた方がいらしたら、それは
違います。**

**自分は影響を受けていたのか？** この特定のタイミングが噛み合った環境でのみ発生します。
私自身の Windows 環境では、Blender 5.1 でも 5.2 でも一度も起きませんでした。だからこそ外部
からの報告がなければ見つけられませんでした。これまで安定してお使いでしたら、体感は変わり
ません。ただし危うい呼び出し自体は過去の全バージョンに存在していたため、プラットフォームを
問わず更新をおすすめします。

### 🖥️ macOS / Linux 版の位置づけについて

「experimental test build（実験的テストビルド）」という表記をやめます。黙って書き換えるのでは
なく、理由をお伝えしたいと思います。

SDF.R は Windows、macOS (Apple Silicon)、Linux (x86-64) 向けに提供しています。3つとも同じ
ソースから、同じ自動ビルドで、毎リリース同時に生成しています。おまけではありません。

ひとつ正直にお伝えします。**私は Windows で開発しており、Mac も Linux の実機も持っていません。**
それらの環境で問題を自分で再現することができません。できるのは、クラッシュレポートを読んで
原因を突き止めることです。そしてそれは機能します。上記のクラッシュは、あるユーザーの方が
送ってくださったログだけを頼りに特定できました。

つまりこれらのプラットフォームは、**皆さんが教えてくださる分だけ良くなります。**

**これには「動いています」という報告も含まれます。** クラッシュ報告は「壊れている」ことを
教えてくれますが、「macOS 26.6 / M3 Max / Blender 5.2 で問題なく動いています」の一言は
「どこまでが大丈夫か」を教えてくれます。同じくらい価値があり、そして今は圧倒的に足りて
いません。もし問題なくお使いでしたら、一言いただけると本当に助かります。

そして、以前 Mac で試してこのクラッシュに当たり、諦めてしまった方がいらしたら、もう一度
試していただけると嬉しいです。

**不具合に遭遇された場合**、最も早い解決経路は、ターミナルから Blender を起動し
（macOS では `/Applications/Blender.app/Contents/MacOS/Blender`）、問題を再現させて、
ターミナルの出力をお送りいただくことです。あわせて一時フォルダ内の `blender.crash.txt`
（`open $TMPDIR` で開けます）もいただけると確実です。このファイルにはアドオン側の行番号が
記録されています。

### ✅ アップデート前の作業は不要です

GPU シェーダーのコードは V16.1.0 から変更していないため、**V16.1.0 / V16.1.1 からの更新では
シェーダーキャッシュの削除は不要**です。

**V16.0.x 以前**からの更新の場合は、従来どおり削除をお願いします。

1. Blender を完全に終了する
2. `%APPDATA%\Blender Foundation\Blender\<バージョン>\datafiles\rust_gpu_sdf\shader_cache.bin` を削除
3. Blender を再起動する（初回起動はウォームアップに 15〜45 秒ほどかかります）

### ダウンロード

- **Windows:** `SDF_R_16_1_2.zip`（標準パッケージ）
- **macOS:** `SDF_R_16_1_2_MAC.zip` — Apple Silicon (arm64) 用
- **Linux:** `SDF_R_16_1_2_LINUX.zip` — x86-64 用

macOS 版は公証（notarize）を受けていないため、Gatekeeper にブロックされた場合は
「システム設定 → プライバシーとセキュリティ」から**「このまま開く」**をクリックしてください。

詳細なリリースノートと更新済みドキュメントは製品ページに掲載しています。

そして今回、粘り強くログを送り続けてくださったユーザーの方に、あらためて感謝します。

— hinata_hugu

---

## Short version (for social / changelog blurb)

> **SDF.R V16.1.2 — macOS crash fixed**
> A crash when adding a primitive on macOS is fixed. The cause was in SDF.R: a timer was making
> Blender re-evaluate the whole scene at a moment it never scheduled. Factory Settings hid the
> problem, which made it look like an add-on conflict — it was not.
> Mesh output is unchanged, and no shader cache clearing is needed from V16.1.x.
> Also: the macOS and Linux builds are no longer labelled "experimental". I build all three
> platforms every release, but I own neither a Mac nor a Linux machine — so reports are how they
> improve. **Including reports that it simply works.**
> Free update for all owners.
