# kredit-isanovski: Template oleh Isanovski Saputra (@isanovskisaputra) — https://isanovskisaputra.biz.id · Lisensi Nonkomersial Isanovski Studio 1.0 (alat/LISENSI.md)
# Membuat "Pasang-Studio-Isanovski-<versi>-windows.exe" (Inno Setup) yang membawa Python, ffmpeg, dan semua paket.
# HARUS dijalankan di Windows 10/11 64-bit:
#   1) pasang uv:          powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
#   2) pasang Inno Setup 6: https://jrsoftware.org/isdl.php  (atau: winget install JRSoftware.InnoSetup)
#   3) di folder repo:     powershell -ExecutionPolicy Bypass -File alat\pemasang\bangun-windows.ps1
# Hasil: alat\pemasang\hasil\Pasang-Studio-Isanovski-<versi>-windows.exe
$ErrorActionPreference = "Stop"
$Pemasang = $PSScriptRoot
$Alat = Split-Path -Parent $Pemasang
$Versi = (Get-Content "$Alat\VERSI" -Raw).Trim()
$Stage = Join-Path $Pemasang "hasil\windows"
$env:Path = "$env:USERPROFILE\.local\bin;$env:Path"

Write-Host "- Isanovski Studio $Versi untuk Windows x64"
if (Test-Path $Stage) { Remove-Item -Recurse -Force $Stage }
New-Item -ItemType Directory -Force "$Stage\bin", "$Stage\alat" | Out-Null

# 1) Python mandiri (python-build-standalone lewat uv)
uv python install cpython-3.12-windows-x86_64-none | Out-Null
$PySrc = uv python find cpython-3.12-windows-x86_64-none
$PyHome = Split-Path -Parent $PySrc
Copy-Item -Recurse "$PyHome" "$Stage\python"
$Py = "$Stage\python\python.exe"
Remove-Item -Force -ErrorAction SilentlyContinue "$Stage\python\Lib\EXTERNALLY-MANAGED"
foreach ($d in "Lib\test", "Lib\idlelib", "Lib\tkinter", "Lib\turtledemo", "tcl", "include") {
  Remove-Item -Recurse -Force -ErrorAction SilentlyContinue "$Stage\python\$d"
}
# pengaman: pastikan paket masuk ke salinan, bukan ke Python milik uv
$Prefix = & $Py -c "import sys;print(sys.prefix)"
if (-not $Prefix.StartsWith($Stage)) { throw "Python bukan salinan di folder build: $Prefix" }

# 2) Paket (ffmpeg ikut lewat imageio-ffmpeg; jendela memakai WebView2 bawaan Windows 10/11)
uv pip install -q --python $Py -r "$Pemasang\paket.txt"

# 3) Alat (tanpa hasil kerja, kunci, cache)
foreach ($d in "klip", "studio", "motion", "suara") {
  robocopy "$Alat\$d" "$Stage\alat\$d" /E /NFL /NDL /NJH /NJS /XD hasil-klip node_modules hasil naskah __pycache__ /XF .env | Out-Null
  if ($LASTEXITCODE -ge 8) { throw "robocopy gagal menyalin $d" }
}
$global:LASTEXITCODE = 0
Copy-Item "$Alat\LISENSI.md", "$Alat\VERSI" "$Stage\alat\"
Set-Content "$Stage\alat\BUNDEL" "installer"
Copy-Item (Get-Command uv).Source "$Stage\bin\uv.exe"
Get-ChildItem -Recurse -Directory -Filter __pycache__ $Stage | Remove-Item -Recurse -Force

# 4) Kompilasi installer
$Iscc = @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
          "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Iscc) { throw "Inno Setup 6 belum terpasang (https://jrsoftware.org/isdl.php)." }
# Bahasa Indonesia untuk wizard: bawaan Inno Setup, atau terjemahan resmi-tak-resmi dari repo Inno Setup
$Isl = Join-Path (Split-Path $Iscc) "Languages\Indonesian.isl"
if (-not (Test-Path $Isl)) {
  $Isl = Join-Path $env:TEMP "Indonesian.isl"
  try { Invoke-WebRequest "https://raw.githubusercontent.com/jrsoftware/issrc/main/Files/Languages/Unofficial/Indonesian.isl" -OutFile $Isl }
  catch { $Isl = Join-Path (Split-Path $Iscc) "Default.isl" }
}
& $Iscc "/DBahasaIsl=$Isl" "/DVersi=$Versi" "/DStage=$Stage" "/DAlat=$Alat" "/O$Pemasang\hasil" "$Pemasang\studio-isanovski.iss"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup gagal (kode $LASTEXITCODE)" }
Write-Host "Selesai: $Pemasang\hasil\Pasang-Studio-Isanovski-$Versi-windows.exe" -ForegroundColor Green
