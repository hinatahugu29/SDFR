"""ネイティブモジュールのローダーが、失敗しても分かる形で終わるかを見る。

Mac は手元で動かせないので、ここは静的に近い形で押さえておきたい箇所。
Apple Silicon 用の .so を Intel Mac で読むと exec_module が
「incompatible architecture」で落ちる。以前はその例外がそのまま抜けていたため、
(1) パッケージ直下に置いた予備の候補が試されず、
(2) 利用者にはアドオン有効化時の生のトレースバックしか残らなかった。
"""
import sys, os, types, importlib, tempfile, shutil

TREE = sys.argv[-1]
sys.path.insert(0, TREE)

fail = []
def check(label, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + label + ("   " + detail if detail else ""), flush=True)
    if not cond:
        fail.append(label)

print("TESTING TREE:", TREE, flush=True)

# --- 1. 通常はちゃんと読める ------------------------------------------------
from rust_gpu_sdf_addon import _native
check("正常系: ネイティブモジュールが読める", hasattr(_native.rust_gpu_sdf, "init_gpu"))

# --- 2. 最初の候補が壊れていても、次の候補で読める --------------------------
# bin/<os>/ を壊れたファイルに差し替えた複製を作り、直下の正物で救えるか見る。
work = tempfile.mkdtemp()
pkg = os.path.join(work, "rust_gpu_sdf_addon")
shutil.copytree(os.path.join(TREE, "rust_gpu_sdf_addon"), pkg,
                ignore=shutil.ignore_patterns("__pycache__", "assets"))
import platform
subdir = {"Windows": "win", "Darwin": "mac", "Linux": "linux"}[platform.system()]
ext = ".pyd" if platform.system() == "Windows" else ".so"
broken = os.path.join(pkg, "bin", subdir, "rust_gpu_sdf" + ext)
check("前提: プラットフォーム別の候補が存在する", os.path.exists(broken), broken)
with open(broken, "wb") as f:
    f.write(b"not a real shared library")   # アーキ違い/破損の代役

sys.path.insert(0, work)
for name in [n for n in list(sys.modules) if n.startswith("rust_gpu_sdf_addon")]:
    del sys.modules[name]
try:
    mod = importlib.import_module("rust_gpu_sdf_addon._native")
    check("壊れた候補を飛ばして予備の候補で読める", hasattr(mod.rust_gpu_sdf, "init_gpu"))
except BaseException as e:
    check("壊れた候補を飛ばして予備の候補で読める", False, f"{type(e).__name__}: {e}")

# --- 3. 全滅したときのメッセージに必要な情報が入っているか ------------------
# 一度読み込んだファイルは Windows ではロックされて上書きできないので、
# 最初から両方を壊した別のツリーを作る。
work2 = tempfile.mkdtemp()
pkg2 = os.path.join(work2, "rust_gpu_sdf_addon")
shutil.copytree(os.path.join(TREE, "rust_gpu_sdf_addon"), pkg2,
                ignore=shutil.ignore_patterns("__pycache__", "assets"))
broken2 = os.path.join(pkg2, "bin", subdir, "rust_gpu_sdf" + ext)
for cand in [broken2, os.path.join(pkg2, "rust_gpu_sdf" + ext)]:
    if os.path.exists(cand):
        with open(cand, "wb") as fh:
            fh.write(b"not a real shared library")

for name in [n for n in list(sys.modules) if n.startswith("rust_gpu_sdf_addon")]:
    del sys.modules[name]
sys.path.insert(0, work2)
try:
    importlib.import_module("rust_gpu_sdf_addon._native")
    check("全滅したら ImportError を投げる", False, "例外が出なかった")
except ImportError as e:
    msg = str(e)
    print("--- 実際のメッセージ ---")
    print(msg)
    print("-----------------------")
    check("全滅したら ImportError を投げる", True)
    check("メッセージに OS と CPU 種別が入る",
          platform.system() in msg and platform.machine() in msg)
    check("メッセージに試したパスが入る", broken2 in msg)
    check("メッセージに失敗理由が入る", "Load errors:" in msg)
except BaseException as e:
    check("全滅したら ImportError を投げる", False, f"{type(e).__name__}: {e}")

shutil.rmtree(work, ignore_errors=True)
shutil.rmtree(work2, ignore_errors=True)
print("\nRESULT: " + ("ALL PASS" if not fail else f"{len(fail)} FAILED: {fail}"), flush=True)
