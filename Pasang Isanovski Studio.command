#!/bin/bash
# Installer Isanovski Studio untuk macOS — klik dua kali file ini.
# Memasang: uv (kalau belum ada), dependensi Klip & Motion, lalu membuat
# aplikasi "Isanovski Studio" di folder Applications pengguna dan pintasan di Desktop.
set -e
ALAT="$(cd "$(dirname "$0")" && pwd)"
APP="$HOME/Applications/Isanovski Studio.app"
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

echo ""
echo "  ┌─────────────────────────────────────┐"
echo "  │   Memasang Isanovski Studio (Klip+Motion) │"
echo "  └─────────────────────────────────────┘"
echo ""

# 1) uv — pengelola Python resmi dari Astral (astral.sh/uv)
if ! command -v uv >/dev/null 2>&1; then
  echo "• Memasang uv…"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi
echo "• uv siap: $(uv --version)"

# 2) Jendela aplikasi (komponen lain dipasang lewat wizard di dalam Studio, lengkap dengan progres)
echo "• Menyiapkan jendela aplikasi…"
uv sync -q --script "$ALAT/studio/studio.py"

# 4) Buat aplikasi .app
echo "• Membuat aplikasi Isanovski Studio…"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

IKON="$(mktemp -d)/ikon.iconset"
mkdir -p "$IKON"
for s in 16 32 128 256 512; do
  sips -z $s $s "$ALAT/studio/aset/ikon.png" --out "$IKON/icon_${s}x${s}.png" >/dev/null
  sips -z $((s*2)) $((s*2)) "$ALAT/studio/aset/ikon.png" --out "$IKON/icon_${s}x${s}@2x.png" >/dev/null
done
iconutil -c icns "$IKON" -o "$APP/Contents/Resources/ikon.icns"

cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>Isanovski Studio</string>
  <key>CFBundleDisplayName</key><string>Isanovski Studio</string>
  <key>CFBundleIdentifier</key><string>id.biz.isanovskisaputra.studio</string>
  <key>CFBundleVersion</key><string>1.0</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>CFBundleExecutable</key><string>studio</string>
  <key>CFBundleIconFile</key><string>ikon</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>LSMinimumSystemVersion</key><string>12.0</string>
</dict></plist>
PLIST

cat > "$APP/Contents/MacOS/studio" <<LAUNCH
#!/bin/bash
# Peluncur Isanovski Studio: nyalakan server lokal (kalau belum), lalu buka jendela aplikasi.
export PATH="\$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:\$PATH"
DATA="\$HOME/Isanovski Studio"
mkdir -p "\$DATA"
# Jendela native (WebKit bawaan macOS) — tidak butuh Chrome. Tutup jendela = mesin berhenti.
exec uv run -q "$ALAT/studio/studio.py" > "\$DATA/studio.log" 2>&1
LAUNCH
chmod +x "$APP/Contents/MacOS/studio"
touch "$APP"

# 5) Pintasan di Desktop
ln -sfn "$APP" "$HOME/Desktop/Isanovski Studio"

echo ""
echo "✅ Selesai! Buka \"Isanovski Studio\" dari Desktop atau Launchpad/Applications."
echo "   Hasil kerja tersimpan di: $HOME/Isanovski Studio"
echo "   Kalau folder alat ini dipindah, jalankan installer ini lagi."
echo ""
open "$APP"
