"""テストが対象にする作業ツリーを解決する。

以前は各テストが `E:\\blender_addon\\外部テスト\\Rust-GPU-SDF-V16.2.1` という
旧PCの絶対パスを既定値に直書きしていた。PC を入れ替えた時点で全部外れたので、
**このファイルの位置から相対で** 解決するようにしてある。

優先順位:
  1. コマンドラインの最終引数（`-- <path>` で渡したもの）。ディレクトリなら採用。
  2. リポジトリ直下で最も版番号の大きい Windows 作業ツリー。

2 を既定にしているのは、テストが版をまたいで使い回されるため。特定の版を直書きすると
次の版を切ったときに必ず古いほうを向く。

使い方（テスト側）:

    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _tree import default_tree
    TREE = sys.argv[-1] if os.path.isdir(sys.argv[-1]) else default_tree()
"""

import os
import re

#: `_MAC` / `_LINUX` は CI 用のコピーなので、Windows の作業ツリーとしては選ばない。
_SUFFIX_SKIP = ("_MAC", "_LINUX")
_PREFIX = "Rust-GPU-SDF-V"


def repo_root():
    """このファイル (`<repo>/tests_V16.2.1/_tree.py`) からリポジトリ直下を返す。"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _version_key(name):
    return [int(n) for n in re.findall(r"\d+", name)]


def candidates(root=None):
    """選択肢になる作業ツリーを、版の新しい順に返す。"""
    root = root or repo_root()
    found = []
    for d in os.listdir(root):
        if not d.startswith(_PREFIX) or d.endswith(_SUFFIX_SKIP):
            continue
        if os.path.isdir(os.path.join(root, d, "rust_gpu_sdf_addon")):
            found.append(d)
    return [os.path.join(root, d) for d in sorted(found, key=_version_key, reverse=True)]


def default_tree(root=None):
    """最も新しい作業ツリーの絶対パス。見つからなければ理由を添えて止まる。

    **選んだツリーは必ず表示する。** Windows の作業ツリーは .gitignore の対象なので、
    クローン直後に残っているのは追跡されている古い版（`Rust-GPU-SDF-V15.9.7.1`）だけ、
    ということが起きる。黙って古い版を測ると、結果が正しく見えるぶん質が悪い。
    """
    found = candidates(root)
    if not found:
        raise SystemExit(
            "作業ツリーが見つかりません: %s\n"
            "Windows の作業ツリー (%s*) は .gitignore の対象なので、"
            "クローン直後には存在しません。\n"
            "Rust-GPU-SDF-V*_MAC を複製して作るか、"
            "テストの最終引数でツリーのパスを渡してください。"
            % (repo_root() if root is None else root, _PREFIX)
        )
    print("_tree: 引数が無いので %s を使う" % found[0], flush=True)
    if len(found) > 1:
        print("_tree: 他の候補 %s（明示するにはテストの最終引数でパスを渡す）"
              % ", ".join(os.path.basename(f) for f in found[1:]), flush=True)
    return found[0]


if __name__ == "__main__":
    for p in candidates():
        print(p)
