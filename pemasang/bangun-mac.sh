#!/bin/bash
# kredit-isanovski: Template oleh Isanovski Saputra (@isanovskisaputra) — https://isanovskisaputra.biz.id · Lisensi Nonkomersial Isanovski Studio 1.0 (alat/LISENSI.md)
# Membuat "Isanovski Studio.app" + "Studio-Isanovski-<versi>-mac-<arsitektur>.dmg" yang sudah membawa Python, ffmpeg, dan
# semua paket. Pengguna tidak perlu membuka Terminal: buka .dmg → seret ke Applications.
#
# Jalankan di Mac (sekali per arsitektur):
#   bash alat/pemasang/bangun-mac.sh            # arsitektur Mac ini (arm64 = Apple Silicon)
#   ARSITEKTUR=x86_64 bash alat/pemasang/bangun-mac.sh   # untuk Mac Intel (dibangun dari Mac mana pun)
# Butuh: uv (astral.sh/uv). Hasil: alat/pemasang/hasil/
set -euo pipefail
PEMASANG="$(cd "$(dirname "$0")" && pwd)"
ALAT="$(dirname "$PEMASANG")"
VERSI="$(tr -d '[:space:]' < "$ALAT/VERSI")"
ARS="${ARSITEKTUR:-$(uname -m)}"
case "$ARS" in arm64|aarch64) ARS=arm64; PYARS=aarch64 ;; x86_64) PYARS=x86_64 ;; *) echo "Arsitektur tidak dikenal: $ARS"; exit 1 ;; esac
HASIL="$PEMASANG/hasil"
APP="$HASIL/Isanovski Studio.app"
RES="$APP/Contents/Resources"
export PATH="$HOME/.local/bin:$PATH"

echo "• Isanovski Studio $VERSI untuk macOS $ARS"
mkdir -p "$HASIL"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$RES/bin"

# 1) Python mandiri (python-build-standalone, lewat uv) — dapat dipindah, tidak bergantung Python sistem
uv python install "cpython-3.12-macos-$PYARS-none" >/dev/null
PYSRC="$(uv python find "cpython-3.12-macos-$PYARS-none")"
PYHOME="$(cd "$(dirname "$PYSRC")/.." && pwd -P)"   # -P: folder asli, bukan symlink
cp -R "$PYHOME/" "$RES/python/"
PY="$RES/python/bin/python3.12"
# pengaman: jangan pernah memasang paket ke Python milik uv di luar aplikasi
[ -L "$RES/python" ] && { echo "Salinan Python masih berupa symlink, berhenti."; exit 1; }
case "$("$PY" -c 'import sys;print(sys.prefix)')" in "$RES/python"*) ;; *) echo "Python bukan salinan di dalam aplikasi, berhenti."; exit 1 ;; esac
rm -f "$RES/python/lib/python3.12/EXTERNALLY-MANAGED"
rm -rf "$RES/python/lib/python3.12/test" "$RES/python/lib/python3.12/idlelib" "$RES/python/lib/python3.12/tkinter" \
       "$RES/python/lib/python3.12/turtledemo" "$RES/python/lib/tcl"* "$RES/python/lib/tk"* "$RES/python/lib/itcl"* \
       "$RES/python/lib/thread"* "$RES/python/share" "$RES/python/include"

# 2) Paket: sama dengan header skrip klip.py & studio.py (ffmpeg ikut lewat imageio-ffmpeg)
uv pip install -q --python "$PY" --python-platform "$PYARS-apple-darwin" --only-binary av,ctranslate2,numpy,opencv-python-headless,tokenizers,onnxruntime \
  -r "$PEMASANG/paket.txt"

# 3) Alat (tanpa hasil kerja, kunci, atau cache)
mkdir -p "$RES/alat"
for d in klip studio motion suara; do
  rsync -a --exclude 'hasil-klip' --exclude '.env' --exclude '__pycache__' --exclude 'node_modules' \
        --exclude 'hasil' --exclude 'naskah' "$ALAT/$d" "$RES/alat/"
done
cp "$ALAT/LISENSI.md" "$ALAT/VERSI" "$RES/alat/"

# 4) uv ikut dibundel: dipakai fitur opsional (Suara VoxCPM) yang memasang paketnya sendiri
cp "$(command -v uv)" "$RES/bin/uv"
[ "$ARS" = "$(uname -m | sed s/aarch64/arm64/)" ] || echo "  (catatan: uv yang dibundel adalah arsitektur Mac ini; fitur Suara di Mac lain butuh uv sendiri)"

# 5) Ikon, Info.plist, peluncur
IKON="$(mktemp -d)/ikon.iconset"; mkdir -p "$IKON"
for s in 16 32 128 256 512; do
  sips -z $s $s "$ALAT/studio/aset/ikon.png" --out "$IKON/icon_${s}x${s}.png" >/dev/null
  sips -z $((s*2)) $((s*2)) "$ALAT/studio/aset/ikon.png" --out "$IKON/icon_${s}x${s}@2x.png" >/dev/null
done
iconutil -c icns "$IKON" -o "$RES/ikon.icns"

cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>Isanovski Studio</string>
  <key>CFBundleDisplayName</key><string>Isanovski Studio</string>
  <key>CFBundleIdentifier</key><string>id.biz.isanovskisaputra.studio</string>
  <key>CFBundleVersion</key><string>$VERSI</string>
  <key>CFBundleShortVersionString</key><string>$VERSI</string>
  <key>CFBundleExecutable</key><string>studio</string>
  <key>CFBundleIconFile</key><string>ikon</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>LSMinimumSystemVersion</key><string>12.0</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>NSHumanReadableCopyright</key><string>Template oleh Isanovski Saputra (@isanovskisaputra) — isanovskisaputra.biz.id</string>
</dict></plist>
PLIST

cat > "$APP/Contents/MacOS/studio" <<'LAUNCH'
#!/bin/bash
# Peluncur Isanovski Studio (versi installer): Python & paket ada di dalam aplikasi.
RES="$(cd "$(dirname "$0")/../Resources" && pwd)"
export STUDIO_PY="$RES/python/bin/python3.12" STUDIO_UV="$RES/bin/uv" PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1
export PATH="$RES/bin:$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
DATA="$HOME/Isanovski Studio"; mkdir -p "$DATA"
exec "$STUDIO_PY" "$RES/alat/studio/studio.py" > "$DATA/studio.log" 2>&1
LAUNCH
chmod +x "$APP/Contents/MacOS/studio"

# 6) Bersihkan cache & tandatangani ad-hoc (tanpa akun Apple Developer)
find "$RES" -name '__pycache__' -type d -prune -exec rm -rf {} +
codesign --force --deep --sign - "$APP" 2>/dev/null
codesign --verify --deep "$APP" && echo "• Tanda tangan ad-hoc OK"

# 7) DMG: aplikasi + pintasan Applications (seret untuk memasang / memperbarui)
DMG="$HASIL/Studio-Isanovski-$VERSI-mac-$ARS.dmg"
STAGE="$(mktemp -d)"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
cp "$PEMASANG/BACA-DULU-mac.txt" "$STAGE/Baca dulu.txt"
rm -f "$DMG"
hdiutil create -quiet -volname "Isanovski Studio $VERSI" -srcfolder "$STAGE" -fs HFS+ -format UDZO -imagekey zlib-level=9 "$DMG"
rm -rf "$STAGE"
echo "✅ $(du -sh "$APP" | cut -f1) aplikasi · $(du -h "$DMG" | cut -f1) DMG"
echo "   $DMG"
