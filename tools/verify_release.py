"""配布物をリリース前に機械的に確認する。

    py -3.11 tools/verify_release.py            # dist_V*/ のうち最も新しい版
    py -3.11 tools/verify_release.py 16.2.2     # 版を指定

`cross_platform_build_notes.md` セクション6-B の `verify_artifacts.py` を土台に、
3プラットフォームの相互一致・バイナリのアーキテクチャ・Linux の依存と glibc 要求・
チェックサム表との照合をまとめたもの。パスはこのファイルの位置から相対で解く。

**これは静的な確認しかしない。** 読み込んで動くかは別問題で、
Linux は `verify_linux_wsl.ps1`、Windows と macOS は実機に頼る。
"""

import hashlib
import io
import os
import re
import struct
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = "rust_gpu_sdf_addon/"
PY = ["__init__.py", "constants.py", "engine.py", "handlers.py",
      "operators.py", "properties.py", "shader.py", "ui.py"]

ok = True


def check(label, cond, detail=""):
    global ok
    if not cond:
        ok = False
    print("  [%s] %s%s" % ("OK" if cond else "NG", label, ("  -> " + detail) if detail else ""))


def pick_version(argv):
    if len(argv) > 1:
        return argv[1]
    vers = [d[len("dist_V"):] for d in os.listdir(ROOT)
            if d.startswith("dist_V") and os.path.isdir(os.path.join(ROOT, d))]
    if not vers:
        raise SystemExit("dist_V* が見つかりません。版を引数で指定してください。")
    return max(vers, key=lambda v: [int(n) for n in re.findall(r"\d+", v)])


# --- バイナリのアーキテクチャ ------------------------------------------------

_MACHO = {0x0100000C: "arm64", 0x01000007: "x86_64"}
_ELF = {0x3E: "x86-64", 0xB7: "aarch64"}
_PE = {0x8664: "x86-64", 0xAA64: "arm64"}


def describe(b):
    if b[:2] == b"MZ":
        off = struct.unpack_from("<I", b, 0x3C)[0]
        if b[off:off + 4] == b"PE\0\0":
            return "PE/COFF", _PE.get(struct.unpack_from("<H", b, off + 4)[0], "?")
        return "PE/COFF", "?"
    if b[:4] == b"\x7fELF":
        return "ELF%s" % ("64" if b[4] == 2 else "32"), _ELF.get(struct.unpack_from("<H", b, 0x12)[0], "?")
    if b[:4] in (b"\xcf\xfa\xed\xfe", b"\xce\xfa\xed\xfe"):
        return "Mach-O", _MACHO.get(struct.unpack_from("<I", b, 4)[0], "?")
    if b[:4] in (b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca"):
        return "Mach-O", "universal (fat)"
    return "unknown", "?"


# --- Linux の依存と glibc 要求 ------------------------------------------------

def elf_requirements(blob):
    """DT_NEEDED と、要求している最大の GLIBC_x.y を返す。"""
    e_shoff = struct.unpack_from("<Q", blob, 0x28)[0]
    e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHH", blob, 0x3A)

    def sec(i):
        o = e_shoff + i * e_shentsize
        name, typ, flags, addr, off, size = struct.unpack_from("<IIQQQQ", blob, o)
        return dict(name=name, off=off, size=size)

    secs = [sec(i) for i in range(e_shnum)]
    shstr = secs[e_shstrndx]

    def cstr(base, off):
        return blob[base + off:blob.index(b"\0", base + off)].decode("utf-8", "replace")

    byname = {cstr(shstr["off"], s["name"]): s for s in secs}
    dyn, dynstr = byname.get(".dynamic"), byname.get(".dynstr")

    needed = []
    if dyn and dynstr:
        o, end = dyn["off"], dyn["off"] + dyn["size"]
        while o < end:
            tag, val = struct.unpack_from("<qQ", blob, o)
            if tag == 0:
                break
            if tag == 1:
                needed.append(cstr(dynstr["off"], val))
            o += 16

    vers = [v for v in set(re.findall(rb"GLIBC_[0-9.]+", blob))]
    key = lambda v: [int(x) for x in re.findall(rb"\d+", v)]
    return needed, (max(vers, key=key).decode() if vers else None)


# --- 本体 --------------------------------------------------------------------

def main():
    ver = pick_version(sys.argv)
    und = ver.replace(".", "_")
    dist = os.path.join(ROOT, "dist_V%s" % ver)
    win_tree = os.path.join(ROOT, "Rust-GPU-SDF-V%s" % ver, "rust_gpu_sdf_addon")

    print("版:", ver)
    print("配布物:", dist)
    print()

    targets = [
        ("Windows", "SDF_R_%s.zip" % und, "bin/win/rust_gpu_sdf.pyd", "rust_gpu_sdf.pyd", "PE/COFF", "x86-64"),
        ("macOS", "SDF_R_%s_Darwin.zip" % und, "bin/mac/rust_gpu_sdf.so", "rust_gpu_sdf.so", "Mach-O", "arm64"),
        ("Linux", "SDF_R_%s_Linux.zip" % und, "bin/linux/rust_gpu_sdf.so", "rust_gpu_sdf.so", "ELF64", "x86-64"),
    ]

    pysrc = {}
    have_win_tree = os.path.isdir(win_tree)
    if not have_win_tree:
        print("注意: Windows 作業ツリーが無いので「通常版と一致」は飛ばす")
        print("      (%s)" % win_tree)
        print()

    for name, zf, binrel, flat, want_fmt, want_arch in targets:
        path = os.path.join(dist, zf)
        print("===", name, zf)
        if not os.path.exists(path):
            check("配布物が存在する", False, path)
            print()
            continue

        z = zipfile.ZipFile(path)
        names = [n for n in z.namelist() if not n.endswith("/")]

        check("二重ZIPでない", not [n for n in names if n.endswith(".zip")])
        roots = sorted({n.split("/")[0] for n in names})
        check("ルートが rust_gpu_sdf_addon 単一", roots == ["rust_gpu_sdf_addon"], str(roots))

        for req in ["__init__.py", "_native.py", "assets/nodes.blend", "license.txt", binrel, flat]:
            check("必須: %s" % req, P + req in names)

        for rel in (binrel, flat):
            if P + rel in names:
                mb = z.getinfo(P + rel).file_size / 1024 / 1024
                check("実体を持つ: %s" % rel, mb > 1.0, "%.1f MB" % mb)

        plat_dir = binrel.rsplit("/", 2)[-2]
        foreign = [n for n in names if n.startswith(P + "bin/") and plat_dir not in n]
        check("他OSのバイナリを含まない", not foreign, str(foreign[:4]))
        check("キャッシュ/中間物なし",
              not [n for n in names if "__pycache__" in n or n.endswith((".pyc", ".pdb", ".lib", ".exp"))])

        if P + binrel in names:
            head = z.open(P + binrel).read(4096)
            fmt, arch = describe(head)
            check("アーキテクチャ", fmt == want_fmt and arch == want_arch,
                  "%s / %s (期待 %s / %s)" % (fmt, arch, want_fmt, want_arch))

            if name == "Linux":
                blob = z.read(P + binrel)
                needed, glibc = elf_requirements(blob)
                check("依存が基本ライブラリのみ",
                      all(n.startswith(("libc.", "libm.", "libgcc_s.", "ld-linux")) for n in needed),
                      ", ".join(needed))
                mx = [int(x) for x in re.findall(r"\d+", glibc or "0")]
                check("要求 glibc が 2.35 以下", mx <= [2, 35], glibc)

        init = z.read(P + "__init__.py").decode("utf-8-sig")
        check("bl_info version", "(%s)" % und.replace("_", ", ") in init)
        check("Loader Marker が V%s" % ver, "V%s" % ver in init)

        for f in ("__init__.py", "engine.py", "ui.py"):
            s = z.read(P + f).decode("utf-8-sig")
            check("%s が ._native 経由" % f,
                  "from ._native import rust_gpu_sdf" in s and "from . import rust_gpu_sdf" not in s)

        pysrc[name] = {f: z.read(P + f).decode("utf-8-sig").replace("\r\n", "\n") for f in PY}

        if have_win_tree:
            diff = []
            for f in PY:
                a = io.open(os.path.join(win_tree, f), encoding="utf-8-sig").read()
                a = a.replace("from . import rust_gpu_sdf", "from ._native import rust_gpu_sdf")
                if a.replace("\r\n", "\n") != pysrc[name][f]:
                    diff.append(f)
            check("Python が Windows 通常版と一致", not diff, str(diff))

        z.close()
        print()

    print("=== 3プラットフォーム間の Python 一致")
    if len(pysrc) == 3:
        for other in ("macOS", "Linux"):
            d = [f for f in PY if pysrc["Windows"][f] != pysrc[other][f]]
            check("Windows と %s が同一" % other, not d, str(d))
    else:
        check("3点そろっている", False, str(sorted(pysrc)))

    print()
    print("=== CHECKSUMS.md との照合")
    cs_path = os.path.join(dist, "CHECKSUMS.md")
    if not os.path.exists(cs_path):
        check("CHECKSUMS.md がある", False, cs_path)
    else:
        cs = io.open(cs_path, encoding="utf-8").read()
        for name, zf, _, _, _, _ in targets:
            p = os.path.join(dist, zf)
            if not os.path.exists(p):
                continue
            h = hashlib.sha256(io.open(p, "rb").read()).hexdigest()
            check("%s SHA-256" % zf, h in cs, h[:16] + "...")
            check("%s サイズ" % zf, "{:,}".format(os.path.getsize(p)) in cs,
                  "{:,}".format(os.path.getsize(p)))

    print()
    print("=== リリース文書")
    for f in ["RELEASE_NOTES_V%s.md" % ver, "RELEASE_NOTES_V%s.html" % ver,
              "UPDATE_ANNOUNCEMENT_V%s.md" % ver, "SNS_POSTS_V%s.md" % ver]:
        check(f, os.path.exists(os.path.join(ROOT, f)))

    print()
    print("RESULT:", "ALL OK" if ok else "PROBLEMS FOUND")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
