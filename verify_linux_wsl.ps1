# V16.2.2 の Linux 配布物を WSL で読み込み確認する。
#
# 前提: `wsl -l -v` に Ubuntu が出ること。
#       ディストリビューション導入直後は Windows の再起動が要る。さらに `--no-launch` で
#       入れた場合は rootfs が未展開なので、`ubuntu.exe install --root` で登録しておく。
#
# 見るのは「配布した .so が実際に読み込めるか」だけ。GPU は WSL で使えるとは限らないので
# エンジンの初期化やメッシュ生成はここでは試さない。そこはユーザー環境頼り。
#
# 注意: このファイルは UTF-8 BOM 付きで保存すること。BOM が無いと Windows PowerShell 5.1 が
#       ANSI として読み、日本語が壊れてヒアドキュメントの終端を見失う。

$ErrorActionPreference = 'Continue'
$ZIP    = 'C:\Users\T03000\Desktop\CODE\BLENDER-ADDON\SDFR\dist_V16.2.2\SDF_R_16_2_2_Linux.zip'
$DISTRO = 'Ubuntu'

if (-not (Test-Path $ZIP)) { Write-Error "配布物が見つかりません: $ZIP"; exit 1 }

# Windows パスを /mnt/... へ。wslpath に渡すと PowerShell 側でバックスラッシュが落ちるため、
# ここで自前に変換する。
function To-WslPath($p) {
    # -replace は正規表現なのでバックスラッシュの扱いが面倒。ここは .Replace() を使う。
    '/mnt/' + $p.Substring(0,1).ToLower() + $p.Substring(2).Replace('\', '/')
}

Write-Host "=== ディストリビューション ==="
wsl -d $DISTRO -u root -- bash -lc "grep PRETTY_NAME /etc/os-release; ldd --version | head -1; python3 --version"
if ($LASTEXITCODE -ne 0) {
    Write-Error "WSL の $DISTRO を起動できません。導入直後なら Windows を再起動してください。"
    exit 1
}

# bash 側は ASCII のみ。PowerShell が誤読しても壊れないようにしておく。
$bash = @'
set -e
ZIP="$1"
rm -rf /tmp/sdfr && mkdir -p /tmp/sdfr
cp "$ZIP" /tmp/sdfr/pkg.zip
cd /tmp/sdfr
python3 -c "import zipfile; zipfile.ZipFile('pkg.zip').extractall('.')"
SO=/tmp/sdfr/rust_gpu_sdf_addon/bin/linux/rust_gpu_sdf.so

echo "--- file ---"
file "$SO" 2>/dev/null || echo "(no file command)"

echo ""
echo "--- ldd ---"
ldd "$SO"
if ldd "$SO" | grep -q "not found"; then
  echo "NG: unresolved dependency"
  exit 1
fi

echo ""
echo "--- import ---"
cp "$SO" /tmp/sdfr/rust_gpu_sdf.so
python3 - <<'PY'
import sys
sys.path.insert(0, "/tmp/sdfr")
import rust_gpu_sdf as R
print("import OK:", R.__file__)
names = [n for n in dir(R) if not n.startswith("_")]
print("public symbols:", len(names))
print("sample:", ", ".join(sorted(names)[:12]))
assert "init_gpu" in names, "init_gpu missing"
print("init_gpu present")
PY
rm -rf /tmp/sdfr
'@

$tmp = Join-Path $env:TEMP 'sdfr_wsl_check.sh'
Set-Content -LiteralPath $tmp -Value ($bash -replace "`r`n", "`n") -Encoding ascii -NoNewline

Write-Host ""
Write-Host "=== 展開して読み込み確認 ==="
wsl -d $DISTRO -u root -- bash (To-WslPath $tmp) (To-WslPath $ZIP)
$code = $LASTEXITCODE

Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue

Write-Host ""
if ($code -eq 0) {
    Write-Host "RESULT: Linux モジュールの読み込み OK" -ForegroundColor Green
    Write-Host "（GPU 初期化とメッシュ生成は WSL では確認していない）"
} else {
    Write-Error "RESULT: 読み込みに失敗した (exit $code)"
}
exit 0
