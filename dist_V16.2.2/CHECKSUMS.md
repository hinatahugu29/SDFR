# SDF.R V16.2.2 - distribution packages

built 2026-09-12 / commit 6b3d2c4 / GitHub Actions run 34664033920

| Platform | File | Size | SHA-256 |
|---|---|---:|---|
| Windows | SDF_R_16_2_2.zip | 14,613,611 | 91e1f1b6ba2f6a6ca00d85a41cafac25af7811ad935368081a77e1be10787596 |
| macOS (Apple Silicon) | SDF_R_16_2_2_Darwin.zip | 13,712,944 | a04d80b006d4f28e14302bb822eefc32e7b76fb4bde66560718be9272a67e29e |
| Linux (x86-64) | SDF_R_16_2_2_Linux.zip | 14,877,406 | 905a7e3c962ee28f4d4e124ad635e7faa0cbae8d08bde5e899bb8024b7d96b11 |

All three carry byte-identical Python sources; only the native module differs.
macOS is arm64 only (built on a macos-14 runner, min macOS 11.0) and does not run on Intel Macs.
Linux requires glibc 2.35 or newer (built on ubuntu-22.04).

## 由来

**3本とも GitHub Actions の run 34664033920 の成果物**で、同じ `Rust-GPU-SDF-V16.2.2_CI/`
ツリーから windows-2022 / macos-14 / ubuntu-22.04 でビルドしたもの。V16.2.2 から
Windows も CI に載せたので、3プラットフォームが同一のソースとツールチェーン基準で
そろっている。手元ビルドを混ぜていない。

## 再現性について

**この成果物はバイト単位では再現しない。** ZIP がエントリごとにファイル更新時刻を
格納するため、ソースもツールチェーンも同一でもビルドのたびに SHA-256 が変わる。

実際、同じソースから作った macOS / Linux は**サイズが 1 バイトも違わない**のに
SHA-256 は前回ビルドと異なる。中身が同じであることの確認にはサイズと
`tools/verify_release.py` を使い、SHA-256 は「配布した特定のファイルと同じものか」の
確認にだけ使うこと。

参考として、同じコミットを本PC（cargo 1.98.1）で手元ビルドした Windows zip と
CI 版を突き合わせたところ、**13エントリ中 12が完全一致**し、違うのは `.pyd` の実体
のみだった（Python ソース・アセット・ライセンスはすべて一致）。別マシンでの
コンパイルなので実体が変わるのは想定どおり。

`py -3.11 tools/verify_release.py 16.2.2` は上記3点すべてで OK。
