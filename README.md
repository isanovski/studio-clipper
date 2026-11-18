# isanovski Studio

Potong video panjang jadi klip 9:16 (subtitle karaoke, bingkai ikut wajah), dan bikin motion graphic 9:16
dari satu topik. Semua diproses di mesin sendiri: tanpa watermark, tanpa kuota, tidak ada yang diunggah ke
server orang lain.

Fork pribadi dari [studio-maliki](https://github.com/malikisaputra-source/studio-maliki).
Kredit + lisensi di bagian paling bawah — wajib dibaca sebelum dibagikan.

---

## Cara kerja

```
                 ┌── browser / HP ──┐        (opsional, di laptop)
                 │  http://…:8787   │
                 ▼                  │
          studio/studio.py ─────────┘   server lokal + seluruh UI (HTML/CSS/JS satu file)
                 │  menjalankan skrip di bawah sebagai proses anak
                 │
   terminal ─────┤                      (jalur CLI: langsung panggil skripnya,
   (Codespaces)  │                       tanpa server, tanpa browser)
                 │
     ┌───────────┴────────────┐
     ▼                        ▼
klip/klip.py               motion/buat.mjs
yt-dlp ► faster-whisper    naskah JSON ► suara (TTS)
 ► ffmpeg                    ► Remotion/Chromium ► MP4
(potong 9:16, subtitle,
 bingkai ikut wajah)

hasil kerja ──► ~/Studio Maliki/   ·   CLI: folder --keluar / motion/hasil/
```

Intinya:

- **`studio.py` itu remote control.** Ia menyajikan UI, menerima perintah (JSON), menjalankan skrip di atas
  sebagai proses anak, lalu mengirim progres ke browser. Satu pekerjaan berat dalam satu waktu.
- **`klip.py` dan `buat.mjs` bisa dipakai tanpa UI** — keduanya CLI biasa.
- **Tidak ada database, tidak ada cloud.** Satu folder data: proyek, hasil render, dan kunci AI
  (`pengaturan.env`). Tidak ada yang dikirim ke mana pun selain ke penyedia AI yang kamu pilih.

## Isi repo

| Folder / file | Isi |
|---|---|
| `studio/` | `studio.py` (server + API) dan `index.html` (seluruh UI: CSS + JS inline) |
| `klip/` | `klip.py` — video panjang → klip pendek. Panduan: `klip/README.md` |
| `motion/` | `buat.mjs` — naskah → video animasi (Remotion). Panduan: `motion/README.md` |
| `suara/` | `suara.py` — teks → WAV (VoxCPM2, opsional) |
| `pasang-cloud.sh` | pemasang untuk VM Linux tanpa layar (Codespaces / Cloud Shell) |
| `pemasang/` | pembuat installer macOS/Windows (tidak dipakai di Linux) |
| `LISENSI.md` | syarat pemakaian |

## Jalan di laptop (Linux)

```bash
bash pasang-cloud.sh          # sekali saja: pasang uv, Node, dependensi, lalu nyalakan
```

Setelah itu, sehari-hari cukup (launcher ada di `~/.local/bin/isanovski-studio`):

```bash
isanovski-studio              # nyalakan + buka browser (lokal saja)
isanovski-studio mobile       # nyalakan, bisa dibuka dari HP di Wi-Fi yang sama
isanovski-studio stop         # matikan
```

Alamat: `http://127.0.0.1:8787`. Manual tanpa launcher:

```bash
uv run studio/studio.py            # jendela aplikasi sendiri
uv run studio/studio.py --browser  # buka di browser
```

## Isi `.env` (kunci AI)

Ini **opsional**. Tanpa kunci, pemilih momen memakai heuristik lokal (gratis, kualitas lebih sederhana).
Kunci hanya dibutuhkan kalau mau `--ai gemini` (atau penyedia lain).

Lokasinya **di sebelah skripnya**, bukan di root repo:

| Dipakai oleh | File |
|---|---|
| `klip/klip.py` | `klip/.env` |
| `motion/naskah.mjs` (bikin naskah pakai AI) | `motion/.env` |

```bash
cp klip/.env.contoh klip/.env     # lalu isi salah satu kunci
chmod 600 klip/.env               # hanya kamu yang bisa baca
```

Isi `klip/.env` — cukup **satu** penyedia, yang lain biarkan kosong:

```bash
# Gemini (paling gampang, ada kuota gratis): https://aistudio.google.com/apikey
GEMINI_API_KEY=AIza...isi_punyamu
GEMINI_MODEL=gemini-3.8-flash

# ATAU OpenAI-compatible: Ollama lokal (gratis), OpenAI, OpenRouter, Groq
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_API_KEY=
OPENAI_MODEL=llama3.1
```

Cara lain tanpa file: variabel lingkungan — ini yang dipakai kalau kunci disimpan sebagai Codespace secret.

```bash
export GEMINI_API_KEY="AIza..."     # berlaku selama terminal itu hidup
uv run klip/klip.py "video.mp4" --ai gemini --jumlah 3 --keluar hasil-klip
```

Cek kuncinya benar sebelum render panjang:

```bash
uv run klip/klip.py --uji-ai lokal     # → SIAP (mode lokal tidak memakai AI luar)
uv run klip/klip.py --uji-ai gemini    # tanpa kunci → "Isi GEMINI_API_KEY di .env…"
```

`klip/.gitignore` sudah menutup `.env`, jadi kunci tidak ikut ter-commit. Tapi tetap: jangan pernah
tempel isi `.env` ke chat, issue, atau screenshot.

## Codespace: perintah dari nol

Codespaces dipakai sebagai **mesin render tanpa layar** — tanpa web UI, tanpa port forwarding, tanpa browser
di dalam codespace. Repo sudah otomatis ada di `/workspaces/studio-clipper`, jadi **tidak perlu `git clone`**.

### Perintah pertama

Buka repo di GitHub → **Code** → tab **Codespaces** → **Create codespace on main**. Tunggu sampai terminal
di bawah muncul, lalu ketik **satu** perintah ini:

```bash
TANPA_WEB=1 bash pasang-cloud.sh
```

Itu saja. Skrip memasang uv, Node, dependensi Python, dan `npm install` untuk Motion (±5–10 menit, ±2 GB),
lalu **berhenti tanpa menyalakan server web**. Di akhir ia mencetak contoh perintah CLI.

Kalau Motion tidak dipakai:

```bash
TANPA_WEB=1 TANPA_NODE=1 bash pasang-cloud.sh
```

### Isi kunci AI (kalau mau `--ai gemini`)

```bash
cp klip/.env.contoh klip/.env
code klip/.env            # atau: nano klip/.env
```

Isi satu baris ini, simpan:

```bash
GEMINI_API_KEY=AIza...isi_punyamu
```

Kunci gratis di https://aistudio.google.com/apikey. Verifikasi:

```bash
uv run klip/klip.py --uji-ai gemini
```

Kalau tidak mau menyimpan kunci di file (dan ingin tetap ada setelah codespace di-rebuild): simpan sebagai
**Codespace secret** — GitHub → repo **Settings** → **Secrets and variables** → **Codespaces** → **New
repository secret**, nama `GEMINI_API_KEY`. Setelah codespace di-restart, nilainya muncul sebagai variabel
lingkungan dan langsung terbaca oleh `klip.py`.

### Taruh videonya

- **Seret file** ke panel Explorer di kiri (folder mana saja, misal root repo), atau
- dari laptopmu: `gh codespace cp ./video.mp4 remote:/workspaces/studio-clipper/`
  (butuh `gh auth refresh -h github.com -s codespace` sekali saja)

### Render

```bash
uv run klip/klip.py "video.mp4" --ai gemini --jumlah 3 --durasi 30 --keluar hasil-klip
```

`--ai gemini` boleh dihapus kalau tidak punya kunci. Prosesnya tercetak di terminal:

```
• Video: video.mp4 — 43 menit, 1920x1080
• Transkripsi dengan faster-whisper model 'small' …
• Mencari momen terbaik …
• Analisis selesai: 3 momen.
• Render 1/3 klip-01.mp4: 12:04–12:34  "…"
• Selesai. 3 klip di hasil-klip
```

Run pertama mengunduh model whisper (`small` ±464 MB) ke `~/.cache/huggingface`.

Isi `hasil-klip/`:

| File | Isi |
|---|---|
| `klip-01.mp4`, `klip-02.mp4`, … | klip 9:16 siap diunggah |
| `klip.json` | skor, judul, hook, kutipan, caption — boleh diedit, lalu render ulang |
| `transkrip.json` | transkrip lengkap |
| `info.json`, `gambar.jpg`, `gaya.json` | metadata, thumbnail, gaya subtitle |

Dua tahap (analisis dulu, render belakangan — hemat waktu kalau cuma mau lihat momen):

```bash
uv run klip/klip.py "video.mp4" --hanya-analisis --keluar hasil-klip
uv run klip/klip.py --keluar hasil-klip --render --pilih 1,3
```

### Ambil hasilnya

Klik kanan file `.mp4` di Explorer → **Download**. Atau dari laptopmu:

```bash
gh codespace cp remote:/workspaces/studio-clipper/hasil-klip/klip-01.mp4 .
```

### Lembar perintah lengkap

| Tujuan | Perintah |
|---|---|
| Perintah pertama | `TANPA_WEB=1 bash pasang-cloud.sh` |
| Pasang + web UI | `bash pasang-cloud.sh` |
| Pasang tanpa Motion | `TANPA_WEB=1 TANPA_NODE=1 bash pasang-cloud.sh` |
| Pasang tanpa Klip | `TANPA_WEB=1 LEWATI_KLIP=1 bash pasang-cloud.sh` |
| Cek AI | `uv run klip/klip.py --uji-ai gemini` |
| Analisis saja | `uv run klip/klip.py "v.mp4" --hanya-analisis --keluar hasil-klip` |
| Render pilihan | `uv run klip/klip.py --keluar hasil-klip --render --pilih 1,3` |
| Render semua | `uv run klip/klip.py "v.mp4" --jumlah 5 --durasi 45 --keluar hasil-klip` |
| Cari momen tertentu | `... --arahan "momen lucu" --rentang 10:00-25:30` |
| Tanpa wajah / subtitle | `... --tanpa-wajah --tanpa-subtitle` |
| Bantuan semua opsi | `uv run klip/klip.py -h` |
| Bikin naskah Motion | `cd motion && node naskah.mjs "topik video" --ai=gemini && cd ..` |
| Render Motion | `node motion/buat.mjs naskah/contoh.json --gaya=neon` |
| Lihat pemakaian disk | `du -sh hasil-klip ~/.cache/huggingface motion/node_modules` |
| Hapus hasil lama | `rm -rf hasil-klip` |
| Render tahan putus | `tmux new -s klip` … `tmux attach -t klip` |

### Kalau ada masalah

| Gejala | Sebab / solusi |
|---|---|
| `Isi GEMINI_API_KEY di .env` | kunci belum ada di `klip/.env` atau env terminal |
| `Sign in to confirm you're not a bot` | link YouTube diblokir dari IP GitHub → unduh di laptop, seret filenya |
| Render mati sendiri | codespace tidur (±30 menit idle) → jalankan di `tmux` |
| `No space left on device` | `rm -rf hasil-klip` dan hapus video sumber yang sudah tidak dipakai |
| Mau lihat log | semua progres ada di terminal; tidak ada file log di mode CLI |

### Yang perlu diingat

- Kuota gratis akun pribadi ±120 core-hour/bulan. Transkripsi video 1 jam memakan CPU penuh **±2,5–5 jam**
  di mesin 2 core — hitung pemakaianmu sebelum render video panjang.
- Semua file hilang kalau codespace dihapus. Unduh hasilnya dulu.
- `TANPA_WEB=1` hanya soal tidak menyalakan web. Kalau nanti mau UI-nya, jalankan `bash pasang-cloud.sh`
  (tanpa variabel itu), lalu buka port 8787 lewat tab PORTS.

## Pakai di HP (dari laptop sendiri, tanpa Codespaces)

```bash
isanovski-studio mobile
```

Buka `http://<IP-laptop>:8787` di HP, Wi-Fi yang sama (IP dicetak saat start). Sudah ada
`theme-color` + `apple-mobile-web-app-capable`, jadi bisa **Add to Home Screen**.

Di layar ≤760px: sidebar jadi tab bar bawah, konten satu kolom, wizard layar penuh, target sentuh ≥44px.

⚠️ Mode `mobile` membuka port ke seluruh jaringan lokal — matikan kalau di Wi-Fi publik.

## Batasan yang sudah terbukti

| Hal | Kenyataan |
|---|---|
| Berat render | whisper `small` ≈ **0,2–0,4× realtime** di 2 vCPU; encode 1080×1920 ≈ **0,5× realtime** |
| RAM | whisper `small` puncak **±790 MB**; Remotion ±1,5–2 GB → jangan dijalankan bersamaan |
| Video 60 menit | transkripsi bisa **2,5–5 jam** di mesin 2 core |
| YouTube dari cloud | diblokir; pakai upload file |
| Satu pekerjaan | `studio.py` menolak job kedua selama job pertama jalan |

## Lisensi

Template oleh **Maliki Saputra** ([@malikisaputra](https://github.com/malikisaputra)) — https://malikisaputra.biz.id.

**Lisensi Nonkomersial Maliki Studio 1.0**: boleh dipakai untuk belajar, pribadi, atau usaha sendiri; boleh
diubah dan dibagikan gratis **dengan kredit utuh**; **dilarang dijual, dijual ulang, disewakan, atau dipakai
untuk jasa berbayar ke pihak lain**. Teks lengkap: [`LISENSI.md`](LISENSI.md).
