# SDF.R クロスプラットフォーム（Mac/Linux）ビルド及び実装ノート

Windows版（通常版）とMac/Linux用のテストビルド（V15.9.8.1）の差異、およびGitHub Actionsによる自動ビルドにおける設定・注意点についてまとめています。

---

## 1. アドオンコード・フォルダ構造の比較

| 項目 | Windows通常版（例: V15.9.9.2） | macOS / Linux テスト版 (V15.9.8.1) |
|---|---|---|
| **Pythonローダー** | `__init__.py` で `from . import rust_gpu_sdf` を直接実行し、直下のDLLをロード。 | `__init__.py` で `from ._native import rust_gpu_sdf` を実行し、動的ローダーを経由。 |
| **動的ローダー (`_native.py`)** | なし。 | **あり（OSおよびPythonバージョンに応じてバイナリの読み込み元を動的に切り替え）。** |
| **バイナリ配置** | アドオンフォルダ直下に `rust_gpu_sdf.pyd` が置かれている。 | フォルダ直下には置かず、各OSごとに `bin/mac/rust_gpu_sdf.so` や `bin/linux/rust_gpu_sdf.so` に格納。 |
| **対象ビルドファイル** | `rust_gpu_sdf.pyd` (Windows 64bit用 DLL) | macOS: `rust_gpu_sdf.so` (または `.dylib`) |
| | | Linux: `rust_gpu_sdf.so` |

### 📁 Mac/Linux版のアドオン展開時のフォルダ構成
```text
rust_gpu_sdf_addon/
├── __init__.py        <-- ロード元を _native.py へ書き換えてインポート
├── _native.py         <-- [重要] OS別バイナリの動的ローダー
├── constants.py
├── engine.py
├── ... (Pythonソースファイル)
└── bin/               <-- プラットフォーム別バイナリフォルダ
    ├── mac/
    │   └── rust_gpu_sdf.so  <-- macOS用コンパイル成果物
    └── linux/
        └── rust_gpu_sdf.so  <-- Linux用コンパイル成果物
```

---

## 2. インポートエラー解決の技術詳細

### 発生していた問題
Blender 4.2以降および5.1（Tahoe 26.4.1等）環境でレガシーアドオンをZIPから新規インストールする際、Blenderは一時フォルダで拡張機能としての適合チェック（`exec_legacy`）を行います。
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

---

## 3. GitHub Actions による自動ビルド設定と注意点

### macOS用ビルド (`macos-14` ランナー)
* **ランナー:** Apple Silicon Mシリーズ対応のため `macos-14` ランナーを指定し、アドオンZIPを生成。
* **出力ファイル:** `SDF_R_15_9_8_1_MAC.zip`

### Linux用ビルド (`ubuntu-22.04` ランナーの明示指定)
* **互換性のための注意点（glibcへの配慮）:**
  Linuxバイナリは、ビルド環境の `glibc` バージョンに依存します。最新版（`ubuntu-latest` / `ubuntu-24.04` 等）でビルドすると、glibcの要求バージョンが高くなり、古いLinux OSや、古いBlenderを動かす環境で `GLIBC_2.xx not found` エラーが発生し、起動しなくなります。
* **ランナー設定の変更:**
  GitHub Actionsで現在サポートされている中で最も古く安定している **`ubuntu-22.04`** を明示的に指定してビルドを行っています。（※廃止された `ubuntu-20.04` を指定すると割り当て待ちのままフリーズするため注意してください。）

---

## 4. 配布・パッケージ作成時の重要ルール

### ⚠️ 二重ZIP問題の回避
GitHub Actionsの「Artifacts」からダウンロードしたZIPファイル（例: `SDF_R_15_9_8_1_MAC_20260709.zip`）は、**GitHub Actionsのパッケージ化仕様により、中に本物のアドオンZIPが1つ入っている二重ZIP構造**になっています。
これをそのままGumroadに載せて配布すると、購入者がBlenderでインストールした際に構造エラーになります。

**【正しい配布手順】**
1. ActionsからダウンロードしたZIPを一度解凍する。
2. 中から出てくる **`SDF_R_15_9_8_1_MAC.zip`** （またはこれを `rust_gpu_sdf_addon_MAC.zip` にリネームした実ファイル）を取り出す。
3. 取り出したアドオンZIPのみをGumroadへアップロードする。

### ⚠️ フォルダ構造の維持（圧縮時のルール）
手動でアドオンを再圧縮する場合は、**必ず `rust_gpu_sdf_addon` というフォルダそのものを外側から圧縮**してください。
フォルダの中身（`__init__.py` など）を直接選択して圧縮すると、解凍した際にフォルダ階層が無くなり、インポートエラーになります。

---

## 5. 【AI・開発者向け】Windows通常版からMac/Linuxテスト版への移植・準備手順

新しいWindows通常版（例: `Rust-GPU-SDF-V15.9.9.2`）をベースに、MacやLinux用のテストパッケージをゼロから準備・ビルドする際の手順です。

### ステップ1: 移植用ディレクトリの作成
1. 通常版のフォルダ（例: `Rust-GPU-SDF-V15.9.9.2`）をコピーし、Mac用（例: `Rust-GPU-SDF-V15.9.9.2_MAC`）およびLinux用（例: `Rust-GPU-SDF-V15.9.9.2_LINUX`）の作業フォルダを作成する。

### ステップ2: アドオンコードの改修（共通）
コピーした作業フォルダ内の `rust_gpu_sdf_addon` フォルダに対して、以下のコード改修を行います。

1. **ローダーファイルの追加**:
   * 前バージョンのMac/Linux版から `_native.py` をコピーし、`rust_gpu_sdf_addon` ディレクトリの直下に配置する。
2. **インポート処理の書き換え**:
   * **`__init__.py`**: 以下のように変更する。
     * **[変更前]** `from . import rust_gpu_sdf` (178行目付近)
     * **[変更後]** `from ._native import rust_gpu_sdf`
   * **`engine.py` および `ui.py`**:
     * パッケージ直下からのインポート（`from . import rust_gpu_sdf`）を、動的ローダー経由（`from ._native import rust_gpu_sdf`）に書き換える。
     * ※これを怠ると、アドオンのロード完了前にモジュールを探しに行ってしまい、`partially initialized module ... (circular import)` エラーが発生します。
3. **不要バイナリの除去**:
   * `rust_gpu_sdf_addon` 直下に置かれている Windows専用の `.pyd` ファイル（`rust_gpu_sdf.pyd`）を削除する。（※残しておくとパッケージサイズが肥大化し、混同を招くため）

### ステップ3: ビルドスクリプトの調整
1. 作業フォルダ直下にある `build_sdf_addon.sh` をテキストエディタで開く。
2. スクリプト下部（60行目付近）の `ZIP_FILE="..."` のバージョン表記を、今回ビルドするバージョン名（例: `SDF_R_15_9_9_2_MAC.zip`）へ書き換える。

### ステップ4: GitHub Actions ワークフローの設定
1. `.github/workflows/build-sdf-r-v15-9-8-1-cross-platform.yml` などのCI設定ファイル（必要に応じて最新版用に複製）を開く。
2. トリガーパス（`paths`）に対象の新規フォルダ（例: `Rust-GPU-SDF-V15.9.9.2_MAC/**`）を追加する。
3. ジョブ実行の `working-directory` を、新しく作成したフォルダ名に変更する。
4. Linux版ビルドジョブのランナー設定が `runs-on: ubuntu-22.04` になっていることを確認する。

### ステップ5: Gitへの反映と成果物の配布
1. 変更をすべてGitにコミットし、GitHubに `push` する。
2. GitHub Actionsの完了後、詳細画面 of 「Artifacts」から生成されたZIPをダウンロードする。
3. ダウンロードしたZIPを一度解凍し、内側に入っている本来のアドオンZIP（例: `SDF_R_15_9_9_2_MAC.zip`）を取り出してGumroad等にアップロードする。

---

## 6. 【macOS特有の注意点】Gatekeeper（実行ブロック）の回避方法

GitHub ActionsなどのCI環境でビルドされたmacOS用のバイナリ（`rust_gpu_sdf.so`）は、Appleのデジタル署名がされていないため、インストール後の有効化時、またはBlender起動時に「開発元を検証できないため開けません」というOS側のGatekeeperエラーによってブロックされる場合があります。

#### ユーザー（テスター）側の対処方法
1. ブロックのエラーダイアログが出た場合、一度「キャンセル」を押します。
2. macOSの「システム設定」＞「プライバシーとセキュリティ」を開きます。
3. 画面の下部に「"rust_gpu_sdf.so" は開発元を確認できないため、使用がブロックされました」と表示されているので、**「このまま開く」**をクリックします。
4. Blenderに戻り、アドオンの有効化チェックボックスを再度オンにします。
