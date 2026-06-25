import importlib.machinery
import importlib.util
import os
import platform


_PACKAGE_DIR = os.path.dirname(__file__)
_MODULE_NAME = f"{__package__}.rust_gpu_sdf"
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
    attempted = []
    for candidate in _iter_candidate_paths():
        attempted.append(candidate)
        if not os.path.exists(candidate):
            continue

        loader = importlib.machinery.ExtensionFileLoader(_MODULE_NAME, candidate)
        spec = importlib.util.spec_from_file_location(_MODULE_NAME, candidate, loader=loader)
        if spec is None:
            continue

        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        return module

    raise ImportError(
        "rust_gpu_sdf native module was not found for this platform.\n"
        f"Detected platform: {platform.system()}\n"
        "Checked paths:\n - " + "\n - ".join(attempted)
    )


rust_gpu_sdf = _load_native_module()
