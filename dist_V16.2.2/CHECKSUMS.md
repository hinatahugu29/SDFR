# SDF.R V16.2.2 - distribution packages

built 2026-09-12 / commit 74bcab3

| Platform | File | Size | SHA-256 |
|---|---|---:|---|
| Windows | SDF_R_16_2_2.zip | 14,612,353 | 5bc1342039cf6cef7e67ac2e3dac8d5dd2a234767b121ccedec0b3fd706f55f6 |
| macOS (Apple Silicon) | SDF_R_16_2_2_Darwin.zip | 13,712,158 | eedaf7d92bdd7bbf4f6c69cc01cd500e31ff2e81d99c268d20cfec5059077d45 |
| Linux (x86-64) | SDF_R_16_2_2_Linux.zip | 14,876,620 | a8683097a1340bba749bf6190960cc6e008c710a2a598dc6892fd8ba31e93132 |

All three carry byte-identical Python sources; only the native module differs.
macOS is arm64 only (built on a macos-14 runner, min macOS 11.0) and does not run on Intel Macs.
Linux requires glibc 2.35 or newer (built on ubuntu-22.04).

## 由来

- **macOS / Linux**: GitHub Actions の run 34545919928（commit cd0d5c6、ubuntu-22.04 /
  macos-14）の成果物をそのまま使っている。2026-09-11 の記録から**サイズ・SHA-256 とも不変**。
  cd0d5c6 以降、`Rust-GPU-SDF-V16.2.2_MAC/` と `Rust-GPU-SDF-V16.2.2_LINUX/` は変更されて
  いないので、この成果物は HEAD の内容と一致する。
- **Windows**: 2026-09-12 に本PCで `build_sdf_addon.ps1` により再ビルドした（cargo 1.92.0）。
  Rust ソースは無変更で、ツールチェーンが前回記録時（cargo 1.98.1）と異なるため、
  .pyd がバイト一致せず SHA-256 とサイズが変わっている。

`py -3.11 tools/verify_release.py 16.2.2` は上記3点すべてで OK。
