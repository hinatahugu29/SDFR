# V16.2.2 の Linux 配布物を WSL で読み込み確認する。
#
# 前提: Windows を再起動済みで、`wsl -l -v` に Ubuntu が出ること。
#       （WSL のディストリビューション導入直後は再起動するまで起動できない）
#
# 見るのは「配布した .so が実際に読み込めるか」だけ。GPU は WSL で使えるとは限らないので
# エンジンの初期化やメッシュ生成はここでは試さない。そこはユーザー環境頼り。

$ErrorActionPreference = 'Continue'
$ZIP    = 'C:\Users\T03000\Desktop\CODE\BLENDER-ADDON\SDFR\dist_V16.2.2\SDF_R_16_2_2_Linux.zip'
$DISTRO = 'Ubuntu'

if (-not (Test-Path $ZIP)) { Write-Error "配布物が見つかりません: $ZIP"; exit 1 }

Write-Host "=== ディストリビューション ==="
wsl -d $DISTRO -u root -- bash -lc "grep PRETTY_NAME /etc/os-release; ldd --version | head -1; python3 --version"
if ($LASTEXITCODE -ne 0) {
    Write-Error "WSL の $DISTRO を起動できません。Windows を再起動してから実行してください。"
    exit 1
}

# zip を WSL 側へ渡す。/mnt 経由だと展開が遅いので、いったん WSL のファイルシステムへコピーする。
$wslZip = (wsl -d $DISTRO -u root -- wslpath -a "$ZIP").Trim()

Write-Host ""
Write-Host "=== 展開して読み込み確認 ==="
$script = @'
set -e
rm -rf /tmp/sdfr && mkdir -p /tmp/sdfr
cp "__ZIP__" /tmp/sdfr/pkg.zip
cd /tmp/sdfr
python3 -c "import zipfile; zipfile.ZipFile('pkg.zip').extractall('.')"
SO=/tmp/sdfr/rust_gpu_sdf_addon/bin/linux/rust_gpu_sdf.so

echo "--- file ---"
file "$SO" 2>/dev/null || echo "(file コマンドなし)"

echo ""
echo "--- ldd（未解決が無いこと） ---"
ldd "$SO"
if ldd "$SO" | grep -q "not found"; then
  echo "NG: 解決できない依存があります"
  exit 1
fi

echo ""
echo "--- import ---"
# PyO3 の extension-module は拡張子なしの名前で import する
cp "$SO" /tmp/sdfr/rust_gpu_sdf.so
cd /tmp/sdfr
python3 - <<'PY'
import sys
sys.path.insert(0, "/tmp/sdfr")
import rust_gpu_sdf as R
print("import OK:", R.__file__)
names = [n for n in dir(R) if not n.startswith("_")]
print("公開シンボル数:", len(names))
print("主なもの:", ", ".join(sorted(names)[:12]))
assert "init_gpu" in names, "init_gpu が見当たらない"
print("init_gpu あり")
PY
'@
$script = $script.Replace('__ZIP__', $wslZip)

$tmp = Join-Path $env:TEMP 'sdfr_wsl_check.sh'
Set-Content -LiteralPath $tmp -Value ($script -replace "`r`n", "`n") -Encoding utf8 -NoNewline
$wslScript = (wsl -d $DISTRO -u root -- wslpath -a "$tmp").Trim()
wsl -d $DISTRO -u root -- bash "$wslScript"
$code = $LASTEXITCODE

Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
wsl -d $DISTRO -u root -- rm -rf /tmp/sdfr 2>$null

Write-Host ""
if ($code -eq 0) {
    Write-Host "RESULT: Linux モジュールの読み込み OK" -ForegroundColor Green
    Write-Host "（GPU 初期化とメッシュ生成は WSL では確認していません）"
} else {
    Write-Error "RESULT: 読み込みに失敗しました (exit $code)"
}
exit 0
