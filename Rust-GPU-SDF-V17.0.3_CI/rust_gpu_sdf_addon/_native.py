import importlib.machinery
import importlib.util
import os
import platform


_PACKAGE_DIR = os.path.dirname(__file__)
# __package__ が None または空になる環境（Blender 4.2+ / 5.1 のレガシーインストール一時処理等）に対応するための安全な解決
_parent_package = __package__ or __name__.rpartition('.')[0]
if not _parent_package:
    _parent_package = os.path.basename(_PACKAGE_DIR)
_MODULE_NAME = f"{_parent_package}.rust_gpu_sdf"
_PLATFORM_SUBDIRS = {
    "Windows": "win",
    "Darwin": "mac",
    "Linux": "linux",
}


def _iter_candidate_paths():
    suffixes = list(importlib.machinery.EXTENSION_SUFFIXES)
    filenames = [f"rust_gpu_sdf{suffix}" for suffix in suffixes]
    legacy_filenames = ["rust_gpu_sdf.pyd", "rust_gpu_sdf.so", "rust_gpu_sdf.dylib"]
    seen = set()

    platform_dir = _PLATFORM_SUBDIRS.get(platform.system())
    if platform_dir:
        for filename in filenames:
            path = os.path.join(_PACKAGE_DIR, "bin", platform_dir, filename)
            if path not in seen:
                seen.add(path)
                yield path

    for filename in filenames + legacy_filenames:
        path = os.path.join(_PACKAGE_DIR, filename)
        if path not in seen:
            seen.add(path)
            yield path


def _load_native_module():
    """ネイティブモジュールを読み込む。

    候補は「プラットフォーム別の bin/<os>/」→「パッケージ直下」の順。同じものを
    2箇所に置いてあるのは、片方が読めなかったときの保険なので、
    **読み込みに失敗しても次の候補へ進む**。以前はここで例外がそのまま抜けていたため、
    最初の候補で転ぶと保険が働かなかった。

    全部だめだったときは、試したパスと**それぞれの失敗理由**を添えて投げる。
    アーキテクチャ違い（Apple Silicon 用のバイナリを Intel Mac で読んだ場合など）は
    ここでしか分からないので、CPU 種別も一緒に出す。
    """
    attempted = []
    failures = []
    for candidate in _iter_candidate_paths():
        attempted.append(candidate)
        if not os.path.exists(candidate):
            continue

        loader = importlib.machinery.ExtensionFileLoader(_MODULE_NAME, candidate)
        spec = importlib.util.spec_from_file_location(_MODULE_NAME, candidate, loader=loader)
        if spec is None:
            failures.append((candidate, "spec could not be created"))
            continue

        try:
            # 拡張モジュールは module_from_spec の時点で共有ライブラリが
            # 実際に dlopen される。アーキテクチャ不一致や依存ライブラリ不足は
            # exec_module ではなくここで出るので、両方を囲む必要がある。
            module = importlib.util.module_from_spec(spec)
            loader.exec_module(module)
        except BaseException as exc:
            # アーキテクチャ不一致・依存ライブラリ不足・壊れたファイルなど。
            # ここで止めず、残りの候補を試す。
            failures.append((candidate, f"{type(exc).__name__}: {exc}"))
            continue
        return module

    detail = ""
    if failures:
        detail = ("\nLoad errors:\n - " +
                  "\n - ".join(f"{path}: {reason}" for path, reason in failures))
    raise ImportError(
        "rust_gpu_sdf native module could not be loaded for this platform.\n"
        f"Detected platform: {platform.system()} ({platform.machine()}), "
        f"Python {platform.python_version()}\n"
        "Checked paths:\n - " + "\n - ".join(attempted) + detail
    )


rust_gpu_sdf = _load_native_module()
