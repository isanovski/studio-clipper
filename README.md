# isanovski Studio

Potong video panjang jadi klip 9:16 (subtitle karaoke, bingkai ikut wajah), dan bikin motion graphic 9:16 dari satu topik. Semua diproses di mesin sendiri: tanpa kuota, tidak ada yang diunggah ke server orang lain, dan watermark-nya milikmu sendiri (bisa dihapus sekali isi).

Fork pribadi dari [studio-isanovski](https://github.com/isanovskisaputra-source/studio-isanovski).
Kredit + lisensi di bagian paling bawah.

---

## Cara Install

Butuh Python 3 dan `uv`. Jika belum ada:

```bash
# 1. Clone repo
git clone https://github.com/isanovskisaputra-source/studio-clipper.git
cd studio-clipper

# 2. Pasang dependensi (Python, uv, ffmpeg, whisper model)
TANPA_WEB=1 bash pasang-cloud.sh

# 3. Jalankan
./mulai
```

`pasang-cloud.sh` akan menginstall:
- Python 3, `uv`, `ffmpeg`
- Model Whisper `small` (±464 MB, unduh sekali)
- Semua dependensi Python untuk klip dan motion

Cukup jalankan sekali saja. Setelah itu, setiap kali mau kerja cukup ketik `./mulai`.

---

## Cara Pakai

### Via menu interaktif (`./mulai`) — disarankan

```bash
./mulai
```

Menu yang muncul:

```
  isanovski Studio  ·  terminal
────────────────────────────────────────────────────────────
  kunci AI: ada   ·   Node: ada   ·   studio-clipper
────────────────────────────────────────────────────────────

  › 1 Potong video jadi klip 9:16
    2 Topik jadi video animasi
    3 Kunci AI (Gemini)
    4 Bantuan & perintah manual
    5 Keluar

  Mau bikin apa? [1]:
```

Pilih **1**. Video yang sudah ada di folder `unggahan/` langsung didaftar — tinggal ketik nomornya:

```
  Video yang ketemu (urut dari yang terbaru):

    1 video.mp4                                    62.3 MB
    2 unggahan/podcast-ep12.mp4                    71.5 MB
    3 tempel jalur lain / link YouTube
    4 batal

  Pilih video [1]:
```

Kalau videonya belum ada di daftar: pilih **tempel jalur lain**, lalu seret file ke terminal atau tempel link YouTube. Berikutnya ditanya jumlah klip, durasi, dan pemilih momen — semua ada nilai bawaan, jadi **Enter terus saja** kalau tidak mau mikir. Progres berjalan di layar:

```
  ✓ 3 klip · total 41.2 MB · hasil/podcast-20261118-1411
    klip-01.mp4  13.8 MB
    klip-02.mp4  14.1 MB
    klip-03.mp4  13.3 MB

  Lanjut apa?
  › 1 sudah cukup, kembali ke menu
    2 lihat judul & hook tiap klip
    3 render ulang klip tertentu
    4 cara mengambil file ini
```

Hasilnya ada di folder `hasil/`.

---

### Via CLI langsung (`klip.py`)

Kalau tidak mau pakai menu:

```bash
uv run klip/klip.py "video.mp4" --keluar hasil-klip --jumlah 3 --durasi 30 --layout gamer --ai deepseek --model small
```

| Opsi | Keterangan |
|------|------------|
| `--jumlah 3` | Berapa klip yang dihasilkan |
| `--durasi 30` | Durasi setiap klip (detik) |
| `--layout tunggal\|split\|gamer` | Tunggal (satu layar), Split (dua pembicara atas-bawah), atau Gamer (wajah atas + gameplay bawah + branding) |
| `--ai lokal\|deepseek\|openrouter\|gemini` | Penyedia AI untuk memilih momen |
| `--model small\|medium` | Model Whisper untuk transkripsi |
| `--warna #FFB020` | Warna judul/subtitle |

Contoh lengkap:

```bash
uv run klip/klip.py "/sdcard/Download/raditya.mp4" \
  --keluar hasil-klip \
  --jumlah 5 \
  --durasi 60 \
  --layout gamer \
  --ai deepseek \
  --model small
```

Hasil ada di folder `hasil-klip/`.

---

## Web UI (opsional)

Kalau mau tampilan browser (lebih enak di HP/laptop):

```bash
# Jalankan server
uv run studio/studio.py --browser

# Buka di browser
http://127.0.0.1:8787
```

Atau lewat menu launcher:

```bash
isanovski-studio              # lokal saja
isanovski-studio mobile       # bisa diakses HP di Wi-Fi yang sama
isanovski-studio stop         # matikan
```

Di web UI: pilih file video → pilih layout → klik Analisis → pilih momen → Render.

---

## Kunci AI (opsional)

Tanpa kunci AI, pemilih momen pakai heuristik lokal (gratis, hasil lebih sederhana). Untuk AI yang lebih cerdas:

**Lewat menu:** `./mulai` → **3 · Kunci AI**. Kunci disimpan di `klip/.env` (izin 600, tidak ikut ke GitHub).

**Atau manual:**

```bash
cp klip/.env.contoh klip/.env
chmod 600 klip/.env
# Edit klip/.env, isi GEMINI_API_KEY=AIza...
```

Kunci gratis: https://aistudio.google.com/apikey

Cek apakah terbaca:
```bash
uv run klip/klip.py --uji-ai gemini   # → SIAP
```

---

## Isi repo

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

## Batasan yang sudah terbukti

| Hal | Kenyataan |
|---|---|
| Berat render | whisper `small` ≈ **0,2–0,4× realtime** di 2 vCPU; encode 1080×1920 ≈ **0,5× realtime** |
| RAM | whisper `small` puncak **±790 MB**; Remotion ±1,5–2 GB → jangan bersamaan |
| Run pertama | unduh model whisper `small` ±464 MB |
| Satu pekerjaan | satu render dalam satu waktu |
| Video 60 menit | transkripsi bisa **2,5–5 jam** di mesin 2 core |

---

## Lisensi

Template oleh **Isanovski Saputra** ([@isanovskisaputra](https://github.com/isanovskisaputra)) — https://isanovskisaputra.biz.id.

**Lisensi Nonkomersial Isanovski Studio 1.0**: boleh dipakai untuk belajar, pribadi, atau usaha sendiri; boleh diubah dan dibagikan gratis **dengan kredit utuh**; **dilarang dijual, dijual ulang, disewakan, atau dipakai untuk jasa berbayar ke pihak lain**. Teks lengkap: [`LISENSI.md`](LISENSI.md).
