SDF.R V17.0.2 - distribution packages
built 2026-11-18 / commit 7d9ecf8 / CI run 44300627214

| Platform | File | Size | SHA-256 |
|---|---|---:|---|
| Windows | SDF_R_17_0_2.zip | 14,620,581 | 1e73da33a12dc4c2a7101519513430ddb7ffdd9a91879c5ec04cb500a80afd8c |
| macOS (Apple Silicon) | SDF_R_17_0_2_Darwin.zip | 13,746,342 | 4ac9c09460c67f0b6ea4c78a3416a5704a6f373b86fe0fef76f6a2463430f8a3 |
| Linux (x86-64) | SDF_R_17_0_2_Linux.zip | 14,903,150 | 99d06c7a5e92c5aef822d0871bcbd70a142e0f1e5e5342bd6ef2bcb17082aba3 |

All three carry byte-identical Python sources; only the native module differs.
V17.0.2 fixes the Round edge profile ignoring Edge Size (now a circular fillet, radius = Edge Size) and changes the Edge Size default from 0.1 to 0.0.
macOS is arm64 only (built on a macos-15 runner; the macos-14 image is retired) and does not run on Intel Macs.
Linux requires glibc 2.35 or newer (built on ubuntu-22.04).
