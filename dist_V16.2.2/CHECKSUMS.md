SDF.R V16.2.2 - distribution packages
built 2026-09-11 / commit 97a0b71

| Platform | File | Size | SHA-256 |
|---|---|---:|---|
| Windows | SDF_R_16_2_2.zip | 14,612,661 | 1d9fb62742272e507a3f99e964992e2b7874dcf44840fcf630ae8f678c5a8f46 |
| macOS (Apple Silicon) | SDF_R_16_2_2_Darwin.zip | 13,712,158 | eedaf7d92bdd7bbf4f6c69cc01cd500e31ff2e81d99c268d20cfec5059077d45 |
| Linux (x86-64) | SDF_R_16_2_2_Linux.zip | 14,876,620 | a8683097a1340bba749bf6190960cc6e008c710a2a598dc6892fd8ba31e93132 |

All three carry byte-identical Python sources; only the native module differs.
macOS is arm64 only (built on a macos-14 runner, min macOS 11.0) and does not run on Intel Macs.
Linux requires glibc 2.35 or newer (built on ubuntu-22.04).

The Windows module was rebuilt on the replacement PC (cargo 1.98.1), so it is not
byte-identical to the .pyd carried over from the previous machine. The Rust sources
are unchanged; only the toolchain differs.
