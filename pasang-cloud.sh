#!/bin/bash
# Pasang isanovski Studio di VM Linux tanpa layar:
#   GitHub Codespaces · Google Cloud Shell · Firebase Studio · VM Ubuntu/Debian lain.
#
# Pakai (dari dalam folder repo):
#   bash pasang-cloud.sh              # pasang semua (Klip + Motion)
#   LEWATI_KLIP=1 bash pasang-cloud.sh   # hanya UI + Motion (hemat ~2 GB)
#   TANPA_NODE=1 bash pasang-cloud.sh    # tanpa Node (Motion tidak bisa render)
#   TANPA_WEB=1 bash pasang-cloud.sh     # CLI saja: pasang dependensi, jangan nyalakan web UI
#   STUDIO_PORT=8080 bash pasang-cloud.sh
#
# Setelah selesai, buka port yang dicetak di akhir lewat port-forwarding
# (Codespaces: tab "Ports" → Open in Browser · Cloud Shell: tombol "Web Preview").
set -e
AKAR="$(cd "$(dirname "$0")" && pwd)"
export PATH="$HOME/.local/bin:$PATH"
PORT_APP="${STUDIO_PORT:-8787}"
# nama folder data sengaja "Isanovski Studio" supaya sama dengan default studio.py
DATA="${STUDIO_DATA:-$HOME/Isanovski Studio}"

echo ""
echo "  ┌────────────────────────────────────────┐"
echo "  │ isanovski Studio — pasang di VM Linux  │"
echo "  └────────────────────────────────────────┘"
echo ""

# 1) uv — pengelola Python resmi Astral
if ! command -v uv >/dev/null 2>&1; then
  echo "• Memasang uv…"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi
echo "• uv: $(uv --version)"

# 2) Node.js LTS (untuk Motion/Remotion) — tarball resmi, tanpa sudo
if ! command -v node >/dev/null 2>&1 && [ "${TANPA_NODE:-0}" != "1" ]; then
  V=$(curl -fsSL https://nodejs.org/dist/index.json |
      python3 -c "import sys,json; print(next(v['version'] for v in json.load(sys.stdin) if v['lts']))")
  echo "• Memasang Node.js $V…"
  mkdir -p "$HOME/.local/node"
  curl -fsSL "https://nodejs.org/dist/$V/node-$V-linux-x64.tar.xz" |
    tar -xJ -C "$HOME/.local/node" --strip-components=1
  for b in node npm npx; do ln -sf "$HOME/.local/node/bin/$b" "$HOME/.local/bin/$b"; done
fi
[ -x "$HOME/.local/bin/node" ] && echo "• node: $($HOME/.local/bin/node --version)"

# 3) Izinkan akses lewat proxy port-forwarding (Codespaces/Cloud Shell/Firebase Studio).
#    Tanpa ini semua tombol di UI dibalas 403 karena Origin bukan localhost.
python3 - "$AKAR/studio/studio.py" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1])
s = p.read_text(encoding="utf-8")
if "netloc.lower() == inang" in s:
    print("• Patch proxy: sudah ada, dilewati")
    sys.exit(0)
lama = '''        asal = self.headers.get("Origin")
        return asal is None or asal in (f"http://127.0.0.1:{PORT}", f"http://localhost:{PORT}")'''
baru = '''        asal = self.headers.get("Origin")
        if asal is None:
            return True
        if asal.rstrip("/") in (f"http://127.0.0.1:{PORT}", f"http://localhost:{PORT}"):
            return True
        inang = (self.headers.get("Host") or "").strip().lower()
        return bool(inang) and urlparse(asal).netloc.lower() == inang'''
if lama not in s:
    print("• Patch proxy: pola tidak cocok, dilewati (versi kode berbeda?)")
    sys.exit(0)
p.write_text(s.replace(lama, baru, 1), encoding="utf-8")
print("• Patch proxy: dipasang")
PY

# 4) Dependensi
echo "• Menyiapkan UI (pywebview)…"
uv sync -q --script "$AKAR/studio/studio.py"
if [ "${LEWATI_KLIP:-0}" != "1" ]; then
  echo "• Menyiapkan Klip (yt-dlp, faster-whisper, opencv — ±1,5 GB, sabar)…"
  uv sync -q --script "$AKAR/klip/klip.py"
fi
if [ "${TANPA_NODE:-0}" != "1" ] && command -v node >/dev/null 2>&1; then
  echo "• Menyiapkan Motion (Remotion — ±400 MB)…"
  ( cd "$AKAR/motion" && npm install --no-audit --no-fund --silent )
fi

# 5) Mode CLI: pasang saja, tanpa server web
if [ "${TANPA_WEB:-0}" = "1" ]; then
  mkdir -p "$DATA"
  echo ""
  echo "✅ Terpasang. Mode CLI (tanpa web UI)."
  echo ""
  echo "   Mulai:"
  echo "     ./mulai"
  echo ""
  echo "   Itu saja — di dalamnya sudah ada menu: potong klip, video animasi,"
  echo "   kunci AI, dan bantuan. Tidak perlu hafal perintah."
  echo ""
  echo "   Data: $DATA"
  exit 0
fi

# 6) Nyalakan mesin di latar belakang
mkdir -p "$DATA"
if curl -s -o /dev/null --max-time 2 "http://127.0.0.1:$PORT_APP/"; then
  echo "• Studio sudah jalan di port $PORT_APP"
else
  setsid nohup env STUDIO_PORT="$PORT_APP" uv run -q "$AKAR/studio/studio.py" --tanpa-buka \
    > "$DATA/studio.log" 2>&1 &
  for _ in $(seq 1 30); do
    curl -s -o /dev/null --max-time 2 "http://127.0.0.1:$PORT_APP/" && break
    sleep 2
  done
fi

if curl -s -o /dev/null --max-time 3 "http://127.0.0.1:$PORT_APP/"; then
  echo ""
  echo "✅ isanovski Studio jalan di http://127.0.0.1:$PORT_APP (di dalam VM)."
  echo "   Buka lewat port-forwarding:"
  echo "     Codespaces     : tab PORTS → baris $PORT_APP → Open in Browser"
  echo "     Cloud Shell    : tombol Web Preview → Change port → $PORT_APP"
  echo "     Firebase Studio: panel Preview → port $PORT_APP"
  echo ""
  echo "   CLI         : ./mulai   (menu interaktif, tanpa browser)"
  echo "   Hasil kerja : $DATA"
  echo "   Log         : $DATA/studio.log"
  echo "   Matikan     : pkill -f '[s]tudio.py'"
else
  echo "⚠️  Gagal start. 20 baris log terakhir:"
  tail -20 "$DATA/studio.log"
  exit 1
fi
