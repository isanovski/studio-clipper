# Isanovski Studio

Potong video panjang jadi klip 9:16 (subtitle, bingkai ikut wajah), dan bikin motion graphic 9:16 dari satu topik. Semua diproses di mesin sendiri: tanpa kuota, tidak ada yang diunggah ke server orang lain, dan watermark-nya milikmu sendiri (bisa dihapus sekali isi).

Fork pribadi dari [studio-isanovski](https://github.com/isanovskisaputra-source/studio-isanovski).
Kredit + lisensi di bagian paling bawah.

---

## 1. Install (satu kali)

Cara paling singkat — copy-paste semua sekaligus di Termux:

```bash
pkg install python git ffmpeg unzip wget -y && pip install uv && cd ~ && wget -q https://github.com/isanovski/studio-clipper/archive/refs/heads/main.zip && unzip -q main.zip && cd studio-clipper-main/klip && uv sync
```

Tunggu sampai selesai (bisa 2-5 menit). Tanpa git clone, tanpa password.

### Kalau sudah unduh salah (folder kosong / tidak ada klip.py)

```bash
cd ~
rm -rf studio-clipper-main main.zip studio.zip
wget -q https://github.com/isanovski/studio-clipper/archive/refs/heads/main.zip
unzip -q main.zip
cd studio-clipper-main/klip
uv sync
./mulai
```

URL yang benar: `github.com/isanovski/studio-clipper` (bukan `isanovskisaputra-source`).

Di Linux / VPS:

```bash
sudo apt install python3 git ffmpeg unzip wget -y
pip install uv
wget https://github.com/isanovski/studio-clipper/archive/refs/heads/main.zip
unzip main.zip
cd studio-clipper-main/klip
uv sync
```

---

## 2. Cara Pakai

### A. Via `./mulai` (disarankan)

```bash
./mulai
```

Akan ditanya satu per satu:

```bash
Video (file atau link YouTube): /sdcard/Download/raditya.mp4
Berapa klip [3]: 5
Durasi per klip (detik) [30]: 60

Pilih layout
  1. tunggal <== default
  2. split
  3. gamer
Pilih 1-3 [1]: 3

Pilih AI
  1. lokal <== default
  2. deepseek
  3. openrouter
  4. gemini
Pilih 1-4 [1]: 2

Pilih model Whisper
  1. small <== default
  2. medium
Pilih 1-2 [1]: 1

=== Ringkasan ===
  Sumber     : /sdcard/Download/raditya.mp4
  Jumlah     : 5 klip
  Durasi     : 60 detik
  Layout     : gamer
  AI         : deepseek
  Model      : small

Mulai proses? (Enter=y, n=batal):
```

Tekan **Enter** untuk mulai. Hasil ada di folder `hasil-klip/`.

Semua pertanyaan bisa dikosongkan (pakai default yang sudah aman).

### B. Via CLI langsung (`klip.py`)

Kalau tidak mau pakai menu, jalankan langsung:

```bash
uv run klip/klip.py "video.mp4" --keluar hasil-klip --jumlah 3 --durasi 30 --layout gamer --ai lokal --model small
```

| Opsi | Keterangan | Contoh |
|------|------------|--------|
| `sumber` | File video atau link YouTube | `/sdcard/Download/raditya.mp4` |
| `--jumlah` | Berapa klip yang dihasilkan | `5` |
| `--durasi` | Durasi setiap klip (detik) | `60` |
| `--layout` | `tunggal`, `split`, atau `gamer` | `gamer` |
| `--ai` | `lokal`, `deepseek`, `openrouter`, `gemini` | `lokal` |
| `--model` | Model Whisper: `small` atau `medium` | `small` |
| `--warna` | Warna judul/subtitle | `#FFB020` |
| `--momen` | `umum` atau `gamer` | `umum` |

Contoh lengkap:

```bash
uv run klip/klip.py "/sdcard/Download/raditya.mp4" \
  --keluar hasil-klip \
  --jumlah 5 \
  --durasi 60 \
  --layout gamer \
  --ai deepseek \
  --model small \
  --warna "#FFB020"
```

Hasil ada di folder `hasil-klip/`.

---

## 3. Kunci AI (opsional)

Tanpa kunci AI, pemilih momen pakai heuristik lokal (gratis, hasil lebih sederhana). Untuk AI yang lebih cerdas, isi kunci di `klip/.env`:

```
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AIza...
OPENROUTER_API_KEY=sk-or-v1-...
```

Cek apakah terbaca:

```bash
uv run klip/klip.py --uji-ai deepseek   # → SIAP
uv run klip/klip.py --uji-ai gemini     # → SIAP
```

Kunci gratis:
- Gemini: https://aistudio.google.com/apikey
- DeepSeek: https://platform.deepseek.com/
- OpenRouter: https://openrouter.ai/

---

## 4. Web UI (opsional)

Kalau mau tampilan browser (lebih enak di HP/laptop):

```bash
uv run studio/studio.py --browser
```

Buka di browser: `http://127.0.0.1:8787`

Atau lewat menu launcher:

```bash
isanovski-studio              # lokal saja
isanovski-studio mobile       # bisa diakses HP di Wi-Fi yang sama
isanovski-studio stop         # matikan
```

Di web UI: pilih file video → pilih layout → klik Analisis → pilih momen → Render.

---

## 5. Isi Repo

| Folder / file | Isi |
|---|---|
| `mulai` | menu CLI interaktif — pintu masuk yang disarankan |
| `studio/` | `studio.py` (server + API) dan `index.html` (seluruh UI web) |
| `klip/` | `klip.py` — video panjang → klip pendek |
| `motion/` | `buat.mjs` — naskah → video animasi (Remotion) |
| `suara/` | `suara.py` — teks → WAV (VoxCPM2, opsional) |
| `pasang-cloud.sh` | pemasang dependensi untuk Linux / Codespaces / Cloud Shell |
| `LISENSI.md` | syarat pemakaian |

---

## 6. Batasan yang Sudah Terbukti

| Hal | Kenyataan |
|---|---|
| Berat render | whisper `small` ≈ **0,2–0,4× realtime** di 2 vCPU; encode 1080×1920 ≈ **0,5× realtime** |
| RAM | whisper `small` puncak **±790 MB**; `medium` ±1,6 GB — jangan jalankan yang lain saat render |
| Run pertama | unduh model whisper `small` ±464 MB |
| Satu pekerjaan | satu render dalam satu waktu |
| Video 60 menit | transkripsi bisa **2,5–5 jam** di mesin 2 core |

---

## 7. Lisensi

Template oleh **Isanovski Saputra** ([@isanovskisaputra](https://github.com/isanovskisaputra)) — https://isanovskisaputra.biz.id.

**Lisensi Nonkomersial Isanovski Studio 1.0**: boleh dipakai untuk belajar, pribadi, atau usaha sendiri; boleh diubah dan dibagikan gratis **dengan kredit utuh**; **dilarang dijual, dijual ulang, disewakan, atau dipakai untuk jasa berbayar ke pihak lain**. Teks lengkap: [`LISENSI.md`](LISENSI.md).
