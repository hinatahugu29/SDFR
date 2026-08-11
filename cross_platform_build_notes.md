# SDF.R クロスプラットフォーム（Mac/Linux）ビルド及び実装ノート

Windows版（通常版）と Mac/Linux 用テストビルドの差異、および GitHub Actions による自動ビルドの設定・注意点をまとめています。

**最終更新: 2026-08-11 / 直近の実施バージョン: V16.1.1**

> このノートは「次に移植するときにミスを減らす」ことを目的としています。
> **まず [セクション0のチェックリスト](#0-移植チェックリスト必ずここから) を上から順に潰してください。**
> 各手順の背景や技術的な理由は、セクション1以降に置いてあります。

---

## 0. 移植チェックリスト（必ずここから）

Windows 通常版 `Rust-GPU-SDF-VX.Y.Z` を Mac/Linux 用に移植するときの全項目です。
**「抜けたときに何が起きるか」を各項目に書いてあります。実際に踏んだものには ⚠️ を付けています。**

### A. ディレクトリ作成

- [ ] `Rust-GPU-SDF-VX.Y.Z_MAC` と `Rust-GPU-SDF-VX.Y.Z_LINUX` を作成した
      → **MAC と LINUX の中身は完全に同一でよい。** ビルドスクリプトが `uname` で分岐する
- [ ] 含めるファイルは Windows 通常版のうち以下だけ（**34ファイル**になるのが正解）
      - ルート: `Cargo.lock` / `Cargo.toml` / `build_sdf_addon.sh` / 各種 `.md`（5個）
      - `src/` 配下すべて（15ファイル）
      - `rust_gpu_sdf_addon/` の Python 9個 + `_native.py` + `license.txt` + `assets/nodes.blend`
- [ ] **含めてはいけないもの**: `build_sdf_addon.ps1` / `patch*.py` / `target/` / `*.zip` / `__pycache__`

### B. アドオンコードの改修

- [ ] 前バージョンの `_MAC` から `_native.py` をコピーした
      → 無いと `ImportError`。**新規に書き起こさないこと**（セクション2の修正が入っている）
- [ ] `__init__.py` / `engine.py` / `ui.py` の3ファイルで
      `from . import rust_gpu_sdf` → `from ._native import rust_gpu_sdf` に書き換えた
      → ⚠️ **1つでも漏れると `partially initialized module ... (circular import)`**
      → 漏れがないかは `grep -rn "from . import rust_gpu_sdf"` が空になることで確認
- [ ] Windows 専用の `rust_gpu_sdf.pyd` を含めていない
      → パッケージ肥大化と混同の元。`.gitignore` で無視されるので commit はされないが、
        手元の zip 作成時に混入しうる
- [ ] 改行コードを LF に統一した
      → 必須ではないが、既存の `_MAC` が LF なので揃えると差分が読みやすい

### C. ビルドスクリプト（`build_sdf_addon.sh`）

- [ ] `ZIP_FILE="SDF_R_X_Y_Z_$(uname).zip"` の版数を更新した
      → 古いままだと前バージョン名の zip が生成され、配布時に取り違える
- [ ] ⚠️⚠️ **`cargo build --release` の直前に macOS 用 RUSTFLAGS が入っている**

      ```bash
      if [ "$(uname)" == "Darwin" ]; then
          export RUSTFLAGS="-C link-arg=-undefined -C link-arg=dynamic_lookup"
      fi
      ```

      → 無いと macOS ビルドが `ld: symbol(s) not found for architecture arm64` で必ず失敗する
      → **これは V16.1.1 の準備でも実際に欠落していた。最頻出のミス**（詳細はセクション8）
      → **対策**: 通常版の `.sh` から流用せず、**前バージョンの `_MAC` の `.sh` をベースにして
        版数だけ差し替える**のが確実

### D. GitHub Actions ワークフロー

- [ ] 前バージョンの `.yml` を複製して新規作成した（`.github/workflows/build-sdf-r-vX-Y-Z-cross-platform.yml`）
- [ ] `on.push.paths` に新フォルダ2つと **yml 自身のパス**を書いた
- [ ] 両ジョブの `working-directory` を新フォルダ名に変更した
      → 変更漏れがあると前バージョンをビルドしてしまい、**成功するのに中身が古い**という
        最も気づきにくい事故になる
- [ ] `upload-artifact` の `path:` を新フォルダ名・新 zip 名に変更した
- [ ] macOS ジョブが `runs-on: macos-14`（Apple Silicon）である
- [ ] Linux ジョブが `runs-on: ubuntu-22.04` である
      → `ubuntu-latest` / `24.04` にすると glibc 要求が上がり、古い環境で
        `GLIBC_2.xx not found` になる
      → ⚠️ 廃止済みの `ubuntu-20.04` を指定すると**割り当て待ちのままフリーズする**
- [ ] yml 内に旧バージョン番号が1つも残っていない（`grep` で確認）

### E. 検証（push 前）

- [ ] [セクション6の検証スクリプト](#6-機械的な検証push-前に必ず流す) を流して全項目 OK
- [ ] `git add -An -- Rust-GPU-SDF-VX.Y.Z_MAC` が **34ファイル**（前バージョンと同数）

### F. push とビルド

- [ ] commit & push
      → `paths` トリガーに該当するので**自動でビルドが走る**。手動実行は不要
- [ ] Actions が両ジョブとも成功した
      → 失敗しても `build-*.log` は `if: always()` で artifact 化されるので、まずログを見る

### G. 配布物の取り出し（⚠️ ここで事故りやすい）

- [ ] Artifacts からダウンロードした zip を**一度解凍**した
      → ⚠️ **二重ZIP問題**。Actions の Artifacts は必ずもう一枚 zip で包まれる（セクション4）
- [ ] 中から出てきた `SDF_R_X_Y_Z_Darwin.zip` / `SDF_R_X_Y_Z_Linux.zip` が本物のアドオン zip
      → 中身のルートが `rust_gpu_sdf_addon/` であることを確認する
- [ ] 配布名へリネームした（**再圧縮は不要**）
      | CI の出力 | 配布名 |
      |---|---|
      | `SDF_R_X_Y_Z_Darwin.zip` | `SDF_R_X_Y_Z_MAC.zip` |
      | `SDF_R_X_Y_Z_Linux.zip` | `SDF_R_X_Y_Z_LINUX.zip` |
      → ドキュメント類には `_MAC` / `_LINUX` 表記で記載しているため、この対応付けが必要
- [ ] （再圧縮する場合のみ）`rust_gpu_sdf_addon` フォルダを**外側から**圧縮した
      → 中身を選んで圧縮すると階層が消えてインポートエラーになる
- [ ] **展開に使った作業フォルダを削除し、`Other_OS/` 直下を zip 2個だけにした**
      → 中間ファイルが残ると、次に見たときどれが配布物か分からなくなる（セクション4の最終レイアウト）
- [ ] [セクション6-B の配布物検証](#6-b-配布物の検証アップロード直前)を流して ALL OK

---

## 1. アドオンコード・フォルダ構造の比較

| 項目 | Windows通常版 | macOS / Linux テスト版 |
|---|---|---|
| **Pythonローダー** | `__init__.py` で `from . import rust_gpu_sdf` を直接実行し、直下のDLLをロード。 | `__init__.py` で `from ._native import rust_gpu_sdf` を実行し、動的ローダーを経由。 |
| **動的ローダー (`_native.py`)** | なし。 | **あり（OSおよびPythonバージョンに応じてバイナリの読み込み元を動的に切り替え）。** |
| **バイナリ配置** | アドオンフォルダ直下に `rust_gpu_sdf.pyd` が置かれている。 | 直下と `bin/mac/` `bin/linux/` の両方に `rust_gpu_sdf.so` を配置（ビルドスクリプトが両方へコピーする）。 |
| **対象ビルドファイル** | `rust_gpu_sdf.pyd` (Windows 64bit用 DLL) | macOS: `librust_gpu_sdf.dylib` → `rust_gpu_sdf.so` にリネームして配置 |
| | | Linux: `librust_gpu_sdf.so` → `rust_gpu_sdf.so` |
| **Python差分** | — | **import 3行のみ。** `handlers.py` `operators.py` `shader.py` 等は完全に同一 |

### 📁 Mac/Linux版のアドオン展開時のフォルダ構成
```text
rust_gpu_sdf_addon/
├── __init__.py        <-- ロード元を _native.py へ書き換えてインポート
├── _native.py         <-- [重要] OS別バイナリの動的ローダー
├── constants.py
├── engine.py
├── ... (Pythonソースファイル)
├── rust_gpu_sdf.so    <-- 直下にも配置（レガシー互換）
└── bin/               <-- プラットフォーム別バイナリフォルダ
    ├── mac/
    │   └── rust_gpu_sdf.so  <-- macOS用コンパイル成果物
    └── linux/
        └── rust_gpu_sdf.so  <-- Linux用コンパイル成果物
```

> **リポジトリ上では `bin/mac` `bin/linux` は空ディレクトリです。**
> `.gitignore` が `**/*.so` を無視するため、バイナリは commit されず、CI が毎回生成します。
> したがって `_MAC` / `_LINUX` ディレクトリに手元のバイナリを置いても push されません。

---

## 2. インポートエラー解決の技術詳細

### 発生していた問題
Blender 4.2以降および5.x 環境でレガシーアドオンをZIPから新規インストールする際、Blenderは一時フォルダで拡張機能としての適合チェック（`exec_legacy`）を行います。
この一時ロードのプロセス中、Pythonのパッケージ境界が正しく設定されず、モジュールの `__package__` 属性が `None`（または空文字列）になります。

このため、元の `_native.py` のコード：
```python
_MODULE_NAME = f"{__package__}.rust_gpu_sdf"
```
が評価されると、モジュール名が `"None.rust_gpu_sdf"` と解釈されてしまい、インポート時に親パッケージが見つからず、以下のエラーをスローしていました：
`RuntimeError: Error: attempted relative import with no known parent package`

また、これが原因でアドオンの初期化に失敗するため、有効化時（チェックボックスをONにした際）には、初期化しきれていないモジュールからインポートしようとしているように見え、`cannot import name 'rust_gpu_sdf' from partially initialized module ... (circular import)` というエラーが誘発されていました。

### 解決策（`_native.py` の修正内容）
`__package__` が `None` の場合でも、`__name__` （例: `rust_gpu_sdf_addon._native`）からパッケージ名を安全に推測し、それも不可能な場合の最終防衛策として現在のフォルダ名（`os.path.basename`）を親パッケージ名とする処理を実装しました。

```python
# 安全なパッケージ名解決のフォールバック
_parent_package = __package__ or __name__.rpartition('.')[0]
if not _parent_package:
    _parent_package = os.path.basename(_PACKAGE_DIR)
_MODULE_NAME = f"{_parent_package}.rust_gpu_sdf"
```
この修正により、Blenderがアドオンをどのように一時ロード・リネームしてロードしたとしても、エラーを吐かずにインポートできるようになりました。

> **この修正が入った `_native.py` を必ず前バージョンからコピーしてください。**
> 書き起こすと上記のフォールバックが抜け、Blender 4.2+ で再発します。

---

## 3. GitHub Actions による自動ビルド設定と注意点

### macOS用ビルド (`macos-14` ランナー)
* **ランナー:** Apple Silicon Mシリーズ対応のため `macos-14` ランナーを指定し、アドオンZIPを生成。
* **出力ファイル:** `SDF_R_X_Y_Z_Darwin.zip`（`$(uname)` が `Darwin` を返すため）
* **⚠️ PyO3リンクエラー対策 (macOS特有):**
  macOS上で PyO3 拡張モジュールをビルドする際、Pythonのシンボル（`_Py_IsInitialized` 等）が解決できずに `ld: symbol(s) not found for architecture arm64` エラーでビルドが失敗する現象を防止するため、ビルドスクリプト (`build_sdf_addon.sh`) 内で `RUSTFLAGS="-C link-arg=-undefined -C link-arg=dynamic_lookup"` を事前に設定（エクスポート）しておく必要があります。

### Linux用ビルド (`ubuntu-22.04` ランナーの明示指定)
* **出力ファイル:** `SDF_R_X_Y_Z_Linux.zip`（`$(uname)` が `Linux` を返すため）
* **互換性のための注意点（glibcへの配慮）:**
  Linuxバイナリは、ビルド環境の `glibc` バージョンに依存します。最新版（`ubuntu-latest` / `ubuntu-24.04` 等）でビルドすると、glibcの要求バージョンが高くなり、古いLinux OSや、古いBlenderを動かす環境で `GLIBC_2.xx not found` エラーが発生し、起動しなくなります。
* **ランナー設定:**
  GitHub Actionsで現在サポートされている中で最も古く安定している **`ubuntu-22.04`** を明示的に指定してビルドを行っています。（※廃止された `ubuntu-20.04` を指定すると割り当て待ちのままフリーズするため注意してください。）
* **追加パッケージ:** `pkg-config libx11-dev libxkbcommon-dev libwayland-dev libasound2-dev libudev-dev`

### ビルドスクリプト側の検証
`build_sdf_addon.sh` は zip 生成後に自動で検証を行います。ここで落ちたら**成果物を配布してはいけません**。

* `rust_gpu_sdf_addon/__init__.py` / `rust_gpu_sdf.so` / `assets/nodes.blend` が zip 内に存在するか
* `__pycache__` / `.pyc` が混入していないか
* 実際に `import rust_gpu_sdf` して読み込めるか

---

## 4. 配布・パッケージ作成時の重要ルール

### ⚠️ 二重ZIP問題の回避
GitHub Actionsの「Artifacts」からダウンロードしたZIPファイルは、**GitHub Actionsのパッケージ化仕様により、中に本物のアドオンZIPが1つ入っている二重ZIP構造**になっています。
これをそのまま配布すると、購入者がBlenderでインストールした際に構造エラーになります。

**【正しい配布手順】**
1. ActionsからダウンロードしたZIPを一度解凍する。
2. 中から出てくる `SDF_R_X_Y_Z_Darwin.zip` / `SDF_R_X_Y_Z_Linux.zip` を取り出す。
   **中身のルートが `rust_gpu_sdf_addon/` になっていることを確認する。**
3. 配布名（`SDF_R_X_Y_Z_MAC.zip` / `SDF_R_X_Y_Z_LINUX.zip`）にリネームしてアップロードする。
   **再圧縮は不要**。中身はそのままで正しい。

### 命名の対応表

| 場面 | macOS | Linux |
|---|---|---|
| CI の artifact 名 | `SDF_R_X_Y_Z_MAC` | `SDF_R_X_Y_Z_LINUX` |
| artifact の中身（本物のアドオンzip） | `SDF_R_X_Y_Z_Darwin.zip` | `SDF_R_X_Y_Z_Linux.zip` |
| 配布名・ドキュメント記載 | `SDF_R_X_Y_Z_MAC.zip` | `SDF_R_X_Y_Z_LINUX.zip` |

> `Darwin` / `Linux` はビルドスクリプト内の `$(uname)` に由来します。
> **ドキュメント側は `_MAC` / `_LINUX` で統一している**ため、配布時にリネームが必要です。

### ✅ 配布物の最終レイアウト（`Other_OS/`）

**プラットフォームごとに zip 1個だけ。展開フォルダも中間 zip も残さない。**

```text
Other_OS/
├── SDF_R_X_Y_Z_MAC.zip      ← 配布物そのもの（中を開くと rust_gpu_sdf_addon/）
└── SDF_R_X_Y_Z_LINUX.zip    ← 配布物そのもの
```

**なぜ徹底するか:** 名前と中身が1対1なら取り違えようがないためです。
V16.1.1 の作業では、`SDF_R_16_1_1_MAC.zip` という**配布名のファイルの中身が artifact のまま（二重ZIP）**という状態が発生しました。
名前が正しいぶん、開かない限り気づけません。**この状態のままアップロードすると購入者のインストールが構造エラーになります。**

展開に使った作業フォルダは削除して構いません。すべて復元可能です。

* Python ソース → git の `Rust-GPU-SDF-VX.Y.Z_MAC` / `_LINUX`
* バイナリを含む完全な中身 → 残した zip を展開すれば取り出せる
* そもそも中身の重複が大半（`nodes.blend` 34MB × 2、バイナリが直下と `bin/` に二重）

**削除は必ず「昇格 → 検証 → 検証が通ってから削除」の順で行ってください。**
消してから間違いに気づくと、Actions からダウンロードし直しになります。

### ⚠️ フォルダ構造の維持（圧縮時のルール）
手動でアドオンを再圧縮する場合は、**必ず `rust_gpu_sdf_addon` というフォルダそのものを外側から圧縮**してください。
フォルダの中身（`__init__.py` など）を直接選択して圧縮すると、解凍した際にフォルダ階層が無くなり、インポートエラーになります。

---

## 5. 【AI・開発者向け】Windows通常版からMac/Linuxテスト版への移植・準備手順

新しいWindows通常版をベースに、MacやLinux用のテストパッケージをゼロから準備・ビルドする際の手順です。
**以下は V16.1.1 で実際に通した手順です。** チェックリストはセクション0を参照。

### ステップ1: 移植用ディレクトリの作成
通常版のフォルダ（例: `Rust-GPU-SDF-V16.1.1`）から、Mac用 `Rust-GPU-SDF-V16.1.1_MAC` および Linux用 `Rust-GPU-SDF-V16.1.1_LINUX` を作成します。

**丸ごとコピーではなく、必要なファイルだけを選んでコピーしてください。**
通常版には `build_sdf_addon.ps1` / `patch*.py` / `target/` / 各種 `.zip` が同居しており、これらは不要です。
完成後のファイル数が **34** になれば正解です（前バージョンの `_MAC` と同数）。

### ステップ2: アドオンコードの改修（共通）
コピーした作業フォルダ内の `rust_gpu_sdf_addon` フォルダに対して、以下の改修を行います。

1. **ローダーファイルの追加**: 前バージョンの `_MAC` から `_native.py` をコピーして直下に配置。
   **新規に書き起こさないこと**（セクション2の修正が入っているため）。
2. **インポート処理の書き換え**: 以下の3ファイルで
   `from . import rust_gpu_sdf` → `from ._native import rust_gpu_sdf`
   * `__init__.py`（`init_gpu_engine()` 内、180行目付近）
   * `engine.py`（5行目付近）
   * `ui.py`（2行目付近）
   ※ **1つでも漏れると `partially initialized module ... (circular import)` が発生します。**
3. **不要バイナリの除去**: Windows専用の `rust_gpu_sdf.pyd` を含めない。

### ステップ3: ビルドスクリプトの調整
1. **前バージョンの `_MAC` の `build_sdf_addon.sh` をベースにする。**
   通常版（Windowsツリー）の `.sh` から流用すると、次項の RUSTFLAGS が欠落している可能性があります。
2. `ZIP_FILE="SDF_R_X_Y_Z_$(uname).zip"` の版数を更新する。
3. **macOSビルド用のリンカフラグの確認**:
   `cargo build --release` の直前に、`Darwin` の場合のみ
   `export RUSTFLAGS="-C link-arg=-undefined -C link-arg=dynamic_lookup"`
   を行うブロックがあることを確認する。

### ステップ4: GitHub Actions ワークフローの設定
前バージョンの `.yml` を複製し、`build-sdf-r-vX-Y-Z-cross-platform.yml` として作成します。
置換が必要な箇所は以下の5種類です。**旧バージョン番号が1つも残っていないことを `grep` で確認してください。**

1. `name:`
2. `on.push.paths`（yml 自身のパス + 新フォルダ2つ）
3. 両ジョブの `working-directory`
4. `upload-artifact` の `name:`（4箇所：本体2 + ログ2）
5. `upload-artifact` の `path:`（4箇所）

ランナー指定（`macos-14` / `ubuntu-22.04`）は変更しないこと。

### ステップ5: 検証 → Gitへの反映 → 成果物の配布
1. セクション6の検証スクリプトを流し、全項目 OK を確認する。
2. commit & push する。`paths` トリガーにより自動でビルドが走ります。
3. Actions 完了後、「Artifacts」から zip をダウンロード。
4. **一度解凍し**、内側のアドオンZIPを取り出して配布名にリネームしてアップロードする（セクション4）。

---

## 6. 機械的な検証（push 前に必ず流す）

目視だけでは `working-directory` の変更漏れなどを見落とします。以下を実行して全項目 OK を確認してください。
`VER` と `PREV` を書き換えるだけで使えます。

```python
# verify_cross_platform.py
import os, re, subprocess

BASE = r"E:\blender_addon\外部テスト"
VER  = "16.1.1"          # 今回のバージョン
PREV = "16.1.0"          # 手本にした前バージョン
NEW  = [f"Rust-GPU-SDF-V{VER}_MAC", f"Rust-GPU-SDF-V{VER}_LINUX"]
REF  = os.path.join(BASE, f"Rust-GPU-SDF-V{PREV}_MAC")
WIN  = os.path.join(BASE, f"Rust-GPU-SDF-V{VER}", "rust_gpu_sdf_addon")
WF   = os.path.join(BASE, ".github", "workflows",
                    "build-sdf-r-v%s-cross-platform.yml" % VER.replace(".", "-"))
UND  = VER.replace(".", "_")     # 16_1_1
ok = True

def check(label, cond, detail=""):
    global ok
    if not cond: ok = False
    print("  [%s] %s%s" % ("OK" if cond else "NG", label, ("  -> " + detail) if detail else ""))

def tree(root):
    out = set()
    for cur, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", "target")]
        for n in files:
            out.add(os.path.relpath(os.path.join(cur, n), root).replace("\\", "/"))
    return out

ref_tree = tree(REF)
for name in NEW:
    t = os.path.join(BASE, name); print("===", name)
    got = tree(t)
    check("前バージョンとファイル構成が一致", got == ref_tree,
          "+%s -%s" % (sorted(got - ref_tree), sorted(ref_tree - got)))
    for f in ("engine.py", "ui.py", "__init__.py"):
        s = open(os.path.join(t, "rust_gpu_sdf_addon", f), encoding="utf-8").read()
        check("%s が ._native 経由" % f,
              "from ._native import rust_gpu_sdf" in s and "from . import rust_gpu_sdf" not in s)
    for f in ("engine.py","ui.py","__init__.py","handlers.py","operators.py",
              "shader.py","properties.py","constants.py"):
        a = open(os.path.join(WIN, f), encoding="utf-8-sig").read()
        a = a.replace("from . import rust_gpu_sdf", "from ._native import rust_gpu_sdf")
        b = open(os.path.join(t, "rust_gpu_sdf_addon", f), encoding="utf-8-sig").read()
        check("%s の中身が通常版と一致" % f, a.replace("\r\n","\n") == b.replace("\r\n","\n"))
    sh = open(os.path.join(t, "build_sdf_addon.sh"), encoding="utf-8", newline="").read()
    check("sh: macOS RUSTFLAGS あり", "dynamic_lookup" in sh)
    check("sh: ZIP名が今回の版数", 'ZIP_FILE="SDF_R_%s_$(uname).zip"' % UND in sh)
    check("sh: 旧版数の残骸なし", PREV.replace(".", "_") not in sh)
    check("バイナリ未混入", not [p for p in got if p.endswith((".so",".pyd",".dylib"))])
    ini = open(os.path.join(t, "rust_gpu_sdf_addon", "__init__.py"), encoding="utf-8").read()
    check("bl_info の version が正しい", "(%s)" % VER.replace(".", ", ") in ini)
    print()

print("=== workflow")
wf = open(WF, encoding="utf-8").read()
for p in NEW + ["SDF_R_%s_Darwin.zip" % UND, "SDF_R_%s_Linux.zip" % UND]:
    check("参照あり: %s" % p, p in wf)
check("旧バージョンの残骸なし", PREV not in wf and PREV.replace(".", "_") not in wf)
for path in re.findall(r"path: (Rust-GPU-SDF-[^\s]+)", wf):
    check("path の親が実在: %s" % path, os.path.isdir(os.path.join(BASE, os.path.dirname(path))))

print()
def _paths(cmd):
    r = subprocess.run(cmd, cwd=BASE, capture_output=True, text=True)
    return {l.strip() for l in r.stdout.splitlines() if l.strip()}

for name in NEW:
    # 「追跡済み」と「未追跡（無視対象を除く）」の和集合を数える。
    # 足し算にすると、変更済みのファイルが両方に出て二重に数えられる。
    # 集合で持てば commit の前後どちらでも同じ数になる。
    n = len(_paths(["git", "ls-files", "--", name]) |
            _paths(["git", "ls-files", "--others", "--exclude-standard", "--", name]))
    check("%s の対象ファイル数が34" % name, n == 34, "実際 %d" % n)

print()
print("RESULT:", "ALL OK" if ok else "PROBLEMS FOUND")
```

---

## 6-B. 配布物の検証（アップロード直前）

セクション6は「push 前にソースが正しいか」を見ます。**こちらは「出来上がった zip が正しいか」を見ます。**
CI が緑でも、取り出し方を間違えれば配布物は壊れます。**アップロード直前に必ず流してください。**

```python
# verify_artifacts.py
import os, zipfile

BASE = r"E:\blender_addon\外部テスト\Other_OS"
WIN  = r"E:\blender_addon\外部テスト\Rust-GPU-SDF-V16.1.1\rust_gpu_sdf_addon"  # 通常版のアドオン
UND  = "16_1_1"
P    = "rust_gpu_sdf_addon/"
PY   = ["__init__.py","constants.py","engine.py","handlers.py",
        "operators.py","properties.py","shader.py","ui.py"]
ok = True

def check(label, cond, detail=""):
    global ok
    if not cond: ok = False
    print("  [%s] %s%s" % ("OK" if cond else "NG", label, ("  -> " + detail) if detail else ""))

for name, zf, binrel in [
    ("macOS", "SDF_R_%s_MAC.zip"   % UND, "bin/mac/rust_gpu_sdf.so"),
    ("Linux", "SDF_R_%s_LINUX.zip" % UND, "bin/linux/rust_gpu_sdf.so"),
]:
    print("===", name, zf)
    z = zipfile.ZipFile(os.path.join(BASE, zf))
    names = [n for n in z.namelist() if not n.endswith("/")]
    check("二重ZIPでない", not [n for n in names if n.endswith(".zip")],
          str([n for n in names if n.endswith(".zip")]))
    check("ルートが rust_gpu_sdf_addon 単一",
          sorted({n.split("/")[0] for n in names}) == ["rust_gpu_sdf_addon"])
    for req in ["__init__.py","_native.py","assets/nodes.blend","license.txt",binrel]:
        check("必須: %s" % req, P + req in names)
    if P + binrel in names:
        sz = z.getinfo(P + binrel).file_size / 1024 / 1024
        check("ネイティブバイナリが実体を持つ", sz > 1.0, "%.1f MB" % sz)
    check("キャッシュ/.pyd 混入なし",
          not [n for n in names if "__pycache__" in n or n.endswith((".pyc",".pyd"))])
    for f in ("__init__.py","engine.py","ui.py"):
        s = z.read(P + f).decode("utf-8-sig")
        check("%s が ._native 経由" % f,
              "from ._native import rust_gpu_sdf" in s and "from . import rust_gpu_sdf" not in s)
    diff = []
    for f in PY:
        a = open(os.path.join(WIN, f), encoding="utf-8-sig").read()
        a = a.replace("from . import rust_gpu_sdf", "from ._native import rust_gpu_sdf")
        b = z.read(P + f).decode("utf-8-sig")
        if a.replace("\r\n","\n") != b.replace("\r\n","\n"): diff.append(f)
    check("Python が通常版と一致", not diff, str(diff))
    check("bl_info version", "(%s)" % UND.replace("_", ", ") in
          z.read(P + "__init__.py").decode("utf-8-sig"))
    print()

print("=== Other_OS 直下（zip 2個だけが理想）")
for n in sorted(os.listdir(BASE)):
    if UND in n:
        p = os.path.join(BASE, n)
        print("  %-32s %s" % (n, "dir ← 消す" if os.path.isdir(p)
                              else "%.1f MB" % (os.path.getsize(p)/1024/1024)))
print()
print("RESULT:", "ALL OK" if ok else "PROBLEMS FOUND")
```

**「Python が通常版と一致」が特に重要です。** ここが通れば、CI が意図したバージョンをビルドしたこと
（＝`working-directory` の変更漏れが無かったこと）を成果物側から裏付けられます。

さらに、そのリリースの修正が実際に入っているかを成果物ベースで確認しておくと確実です。
V16.1.1 では以下を見ました。

```python
h = z.read(P + "handlers.py").decode("utf-8-sig")
e = z.read(P + "engine.py").decode("utf-8-sig")
o = z.read(P + "operators.py").decode("utf-8-sig")
check("修正1: ビューポート別のビュー判定",      "_last_view_hashes" in h)
check("修正2: オフスクリーンのサイズ別キャッシュ", "_offscreens" in h)
check("修正3: 頂点インデックス範囲ガード",      "vertex index out of range" in e)
check("修正4: users_collection のスナップショット", "list(obj.users_collection)" in o)
```

---

## 7. 【macOS特有の注意点】Gatekeeper（実行ブロック）の回避方法

GitHub ActionsなどのCI環境でビルドされたmacOS用のバイナリ（`rust_gpu_sdf.so`）は、Appleのデジタル署名がされていないため、インストール後の有効化時、またはBlender起動時に「開発元を検証できないため開けません」というOS側のGatekeeperエラーによってブロックされる場合があります。

#### ユーザー（テスター）側の対処方法
1. ブロックのエラーダイアログが出た場合、一度「キャンセル」を押します。
2. macOSの「システム設定」＞「プライバシーとセキュリティ」を開きます。
3. 画面の下部に「"rust_gpu_sdf.so" は開発元を確認できないため、使用がブロックされました」と表示されているので、**「このまま開く」**をクリックします。
4. Blenderに戻り、アドオンの有効化チェックボックスを再度オンにします。

> この案内は製品ドキュメント（`BlenderMarket_Documentation_*.html` の FAQ）とリリースノートにも記載済みです。
> 新バージョンでも消さないこと。

---

## 8. 過去に実際に踏んだミスの記録

再発防止のため、実際に起きたものだけを記録しています。

| 時期 | 内容 | 原因 | 対策 |
|---|---|---|---|
| V16.1.1 準備時 | 通常版の `build_sdf_addon.sh` に macOS 用 RUSTFLAGS が無かった | RUSTFLAGS は `_MAC` を作るときに追加されたもので、**通常版のツリーへ戻されていなかった**。そのため通常版から流用するたびに欠落が再発する | ① 通常版 `Rust-GPU-SDF-V16.1.1/build_sdf_addon.sh` にも同ブロックを追加済み（`Darwin` 判定付きなので Windows/Linux では無害）<br>② それでも**前バージョンの `_MAC` をベースにする**のが確実 |
| — | Artifacts の zip をそのまま配布すると構造エラー | GitHub Actions の仕様で二重ZIPになる | セクション4の手順。**必ず一度解凍する** |
| — | `ubuntu-20.04` 指定で CI がフリーズ | ランナーが廃止済み | `ubuntu-22.04` を明示。`latest` も使わない（glibc） |
| Blender 4.2+ 対応時 | `attempted relative import with no known parent package` | `__package__` が `None` になる一時ロード | `_native.py` のフォールバック（セクション2）。**必ず前バージョンからコピー** |

### 特に気をつけるべき「成功するのに間違っている」パターン

以下は **CI が成功してしまう**ため、成果物を配って初めて気づくことになります。セクション6の検証で潰してください。

- `working-directory` の変更漏れ → **前バージョンをビルドしている**
- `ZIP_FILE` の版数更新漏れ → 中身は新しいが**ファイル名が古い**
- import 書き換え漏れ → ビルドは通るが、**ユーザーの環境で有効化時に落ちる**
  （CI の検証は `import rust_gpu_sdf` 単体なので、アドオンとしてのロードまでは見ていない）
