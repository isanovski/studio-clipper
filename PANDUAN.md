# 📖 Panduan Lengkap — isanovski Studio (CLI)

Panduan ini untuk sistem yang sudah ada di repo ini: **yt-dlp + custom command + potong video dari CLI**, dan menu interaktif `./mulai` yang nggak perlu hafal perintah.

Semua proses jalan di mesin sendiri (lokal / Codespace). Tidak ada yang diunggah ke server orang lain.

---

## 1. Ringkasan Alur

```
Video sumber (file lokal / YouTube)
        │
        ▼
yt-dlp → faster-whisper (transkrip + waktu kata)
        │
        ▼
klip.py pilih momen terbaik (lokal atau Gemini)
        │
        ▼
ffmpeg → potong 9:16, subtitle karaoke, bingkai ikut wajah,
         watermark tengah, judul atas, progress bar
        │
        ▼
hasil/klip-01.mp4, klip-02.mp4, … + klip.json
```

---

## 2. Instalasi (sekali saja)

Di dalam folder repo (`/workspaces/studio-clipper` di Codespace):

```bash
TANPA_WEB=1 bash pasang-cloud.sh
```

Itu akan:
- Pasang `uv` (pengelola Python)
- Pasang Node.js (kalau belum ada, untuk Motion/Remotion)
- Pasang dependensi Python: `yt-dlp`, `faster-whisper`, `ffmpeg`, `opencv`, dll.
- Tidak nyalakan server web (mode CLI saja)

Setelah selesai, jalankan:

```bash
./mulai
```

---

## 3. Menu Interaktif `./mulai`

Ketik `./mulai` (atau `python3 mulai` kalau permission error). Muncul menu:

```
  is isanovski Studio  ·  terminal
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

### Menu 1 — Potong video jadi klip 9:16

Pilih **1**. Sistem akan:

1. **Daftar video otomatis** — file `.mp4 .mov .mkv .webm .m4v .avi .ts .flv` di folder repo, `unggahan/`, dan `~/Isanovski Studio/unggahan`, urut dari yang terbaru.
2. Pilih nomor video, atau pilih **"tempel jalur lain / link YouTube"** kalau videonya belum muncul.
3. Ditanya **jumlah klip** (default 3) dan **durasi tiap klip** (default 30 detik). Enter saja kalau mau bawaan.
4. Pilih **pemilih momen**: lokal (gratis, tanpa kunci) atau Gemini (butuh kunci API).
5. Ditanya **cari momen tertentu?** — kosongkan kalau bebas, atau ketik mis. `"tips lucu"` / `"momen pecah"`.
6. Ditanya **Watermark tengah ('-' = tanpa)** — default `isanovski Studio`. Ketik `-` kalau tidak mau watermark, atau ketik teks sendiri.
7. Konfirmasi `Mulai sekarang? [Y/n]` — Enter untuk mulai.

Hasil disimpan di `hasil/<nama>-<tanggal>/`.

#### Contoh layar saat selesai:

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

Pilih **4** untuk tahu cara download file hasilnya (di Codespace: klik kanan `.mp4` di Explorer → Download).

---

## 4. Mode Bingkai Wajah (Face Framing)

Studio-clipper sekarang mendeteksi wajah dalam video secara otomatis dan mengikuti pembicara aktif saat memotong 9:16. Cocok untuk video gaming, wawancara, dan podcast.

### Opsi di menu `./mulai`

Saia memilih tampilan klip, Studio akan menanyakan **Mode Bingkai Wajah**:

| Mode | Keterangan |
|------|------------|
| **Auto (ikuti wajah bicara)** | Deteksi wajah per shot, ikuti wajah yang bicara (gerak mulut seirama suara). Wajah bergeser di layar saat pembicara berganti. |
| **Manual (tentukan posisi)** | Kamu menentukan posisi wajah secara manual dengan slider 0.0 (kiri) … 1.0 (kanan). Cocok untuk mood atau komposisi tertentu. |
| **Fit (layar penuh)** | Tidak dipotong. Video ditampilkan penuh dengan blurred backdrop di sisi kiri-kanan. |

### Opsi CLI (`klip/klip.py`)

```bash
# Auto: ikuti wajah bicara (default)
uv run klip/klip.py video.mp4 --face-mode auto

# Manual: wajah di posisi 70% dari kiri
uv run klip/klip.py video.mp4 --face-mode manual --face-x 0.7

# Fit: layar penuh, tidak dipotong
uv run klip/klip.py video.mp4 --face-mode fit

# Gabung dengan layout gamer
uv run klip/klip.py game.mp4 --layout gamer --face-mode auto --facecam kamera.mp4
```

### Cara kerja internal

1. Video di-scan per shot (potongan kamera).
2. Setiap shot di-analisis 1×/detik dengan model **YuNet** (bundled di `klip/model/`).
3. Wajah yang gerak mulutnya paling seirama dengan suara = pembicara aktif.
4. Crop window 9:16 mengikuti wajah tersebut; pindah seketika di cut kamera, atau halus (ease) saat pembicara berganti dalam satu shot.
5. Tanpa wajah atau wajah tidak muat window → `fit` (layar penuh dengan blurred backdrop).

### Contoh hasil

- **Solo gamer**: wajah di pojok kanan otomatis diikuti saat bergerak.
- **Duo podcast**: dua wajah diframe bersama jika muat; jika tidak, yang bicara difokuskan.
- **Gameplay tanpa wajah**: tampilan penuh (fit), tidak ada crop aneh.

---


### A. Analisis + render (paling sering dipake)

```bash
uv run klip/klip.py "video.mp4" --jumlah 3 --durasi 30 --keluar hasil-x
```

### B. Dari YouTube (langsung)

```bash
uv run klip/klip.py "https://www.youtube.com/watch?v=XXXX" \
  --jumlah 3 --durasi 30 --keluar hasil-y
```

> ⚠️ Di Codespace/IP GitHub, YouTube sering blok unduhan (`Sign in to confirm you're not a bot`). Unduh dulu di laptop, baru seret file ke Codespace.

### C. Analisis saja (cari momen tanpa render)

```bash
uv run klip/klip.py "video.mp4" --hanya-analisis --keluar hasil-x
```

### D. Render ulang klip tertentu dari hasil sebelumnya

```bash
uv run klip/klip.py --keluar hasil/x --render --pilih 1,3
```

### E. Semua opsi

```bash
uv run klip/klip.py -h
```

#### Tabel opsi penting:

| Opsi | Arti | Contoh |
|------|------|--------|
| `sumber` | File video atau link YouTube | `video.mp4` |
| `--jumlah N` | Banyaknya klip | `--jumlah 5` |
| `--durasi N` | Target detik per klip | `--durasi 45` |
| `--model` | Model Whisper: `tiny`, `base`, `small`, `medium`, `large-v3` | `--model small` (default) |
| `--bahasa` | Kode bahasa: `id`, `en`, atau `auto` | `--bahasa id` |
| `--keluar` | Folder hasil | `--keluar hasil-x` |
| `--ai` | Pemilih momen: `lokal`, `gemini`, `openai`, `claude-code`, `codex`, `opencode` | `--ai gemini` |
| `--arahan` | Momen yang dicari | `--arahan "tips lucu"` |
| `--rentang` | Bagian video yang dianalisis | `--rentang 10:00-25:30` |
| `--subtitle-file` | Pakai .srt sendiri (lewati transkrip) | `--subtitle-file video.srt` |
| `--watermark` | Teks di tengah klip (±50% transparan) | `--watermark "@akunmu"` |
| `--gaya` | JSON gaya render | `--gaya '{"subtitle":false}'` |
| `--tanpa-wajah` | Bingkai tengah, tidak ikuti wajah | `--tanpa-wajah` |
| `--layout gamer` | **Mode 2 kamera gamer**: facecam kotak di tengah atas + gameplay di bawah | `--layout gamer --facecam kamera.mp4` |
| `--facecam FILE` | File video kamera untuk mode gamer (pakai dengan `--layout gamer`) | `--facecam kamera.mp4` |
| `--momen` | Preset cari momen: `umum` atau `gamer` (kosong = ikut layout) | `--momen gamer` |
| `--beam N` | Strategi decode Whisper: `1` greedy (cepat, hemat RAM) … `5` beam search (default) | `--beam 1` |
| `--potong N` | Pecah audio jadi chunk N detik saat transkripsi (0 = off) | `--potong 120` |
| `--tanpa-subtitle` | Klip tanpa subtitle | `--tanpa-subtitle` |
| `--uji-ai` | Cek sambungan AI | `--uji-ai gemini` |

---

> **Model `small` masih cukup akurat untuk Bahasa Indonesia lisan.**  
> Dengan initial prompt berisi kata santai ("nggak", "gimana", "banget", "sih", dll.) dan `condition_on_previous_text=False`, hasil transkrip sudah layak pakai untuk klip pendek. Kalau masih terlalu banyak salah tangkap kata, naikkan ke `--model medium` (tapi RAM akan lebih besar dan waktu lebih lama).

---

## 5. yt-dlp / Unduh Video (CLI Custom)

Sistem ini sudah pakai **yt-dlp** bawaan lewat `klip.py`. Kalau mau unduh video manual dulu (khusus Codespace karena YouTube sering blok):

```bash
# Unduh video YouTube ke folder repo
uv run klip/klip.py --hanya-analisis "https://www.youtube.com/watch?v=XXXX" --keluar hasil-temp
# Atau pakai yt-dlp langsung kalau sudah terpasang:
yt-dlp -f "bestvideo[height<=1080]+bestaudio/best" -o "video-saya.%(ext)s" "URL_YOUTUBE"
```

Setelah file `.mp4` ada di folder Codespace (panel Explorer kiri), jalankan `./mulai` → pilih **1** → videonya sudah muncul di daftar.

---

## 6. Potong Video dari CLI (Custom Command)

Kalau hanya mau potong video tanpa AI / tanpa transkrip, pakai `ffmpeg` langsung (sudah terpasang oleh `pasang-cloud.sh`):

```bash
# Potong 00:10:00 sampai 00:10:30, paksa 9:16 (1080x1920)
ffmpeg -i video.mp4 -ss 00:10:00 -to 00:10:30 \
  -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black" \
  -c:a copy -c:v libx264 -preset fast -crf 23 \
  hasil-potong.mp4
```

Kalau mau bingkai ikut wajah + subtitle karaoke, pakai `klip.py` (lihat bagian 4).

---

## 6b. Mode Gamer (Facecam Atas + Gameplay Bawah)

Mode ini untuk konten gaming: **facecam kotak di tengah atas**, **gameplay landscape di bawah**, canvas hitam 1080×1920. Butuh **dua file video terpisah**:

```bash
uv run klip/klip.py gameplay.mp4 --layout gamer --facecam kamera.mp4 \
  --momen gamer --jumlah 3 --durasi 30 --keluar hasil-gamer
```

- `gameplay.mp4` — video game, jadi gameplay di bawah
- `kamera.mp4` — video kamera orang, jadi facecam di atas tengah
- Facecam **di-crop kotak dari tengah** (tidak diregangkan) lalu diskalakan ke 600×600
- Gameplay **tinggi penuh tetap utuh**, dilebihkan zoom lalu **dipotong kiri-kanan** dari tengah, jadi 1080×1080
- **Tanpa subtitle** (mode gamer mematikan subtitle otomatis)
- Tanpa judul/banner/watermark

### Menyesuaikan ukuran & zoom

Semua lewat `--gaya` (JSON):

```bash
uv run klip/klip.py gameplay.mp4 --layout gamer --facecam kamera.mp4 \
  --gaya '{"fc_size": 600, "game_h": 1080, "game_zoom": 1.15}'
```

| Kunci | Default | Arti |
|-------|---------|------|
| `fc_size` | `600` | sisi facecam (bujur). Makin besar, makin memenuhi bagian atas |
| `game_h` | `1080` | tinggi gameplay di canvas. `1080` = 1:1 (potong kiri-kanan banyak) |
| `game_zoom` | `1.0` | >1 memperbesar gameplay (potong kiri-kanan makin banyak, zoom ke tengah) |

Di `./mulai` menu 1, setelah pilih video, akan ditanya:

```
  Tampilan klip
    1 tunggal (layar penuh)
    2 facecam (wajah atas)
    3 pip (wajah kecil kanan bawah)
    4 gamer (wajah atas + gameplay bawah)

  Preset cari momen
    1 gamer (teriakan + reaksi wajah + aksi game)
    2 umum (hook + bicara padat)
```

Pilih **4**, lalu ketik nama file facecam-nya.

---

## 6c. Preset Cari Momen

`--momen` menentukan **algoritma pemilihan momen**. Dua mode:

| Mode | Sinyal yang dipakai | Cocok untuk |
|------|--------------------|-------------|
| `umum` | hook kata pemikat, kata tanya, pembuka kuat, kepadatan bicara, rata-rata energi suara, heatmap YouTube | podcast, wawancara, edukasi, vlog |
| `gamer` | **puncak** energi suara (teriakan), lonjakan vs baseline 5 detik, **reaksi facecam** (motion frame), **aksi gameplay** (motion frame), kamus kata + interjeksi gaming | konten gaming, stream highlight |

```bash
# paksa mode gamer
uv run klip/klip.py gameplay.mp4 --layout gamer --facecam kamera.mp4 --momen gamer

# paksa mode umum walau layout gamer
uv run klip/klip.py gameplay.mp4 --layout gamer --facecam kamera.mp4 --momen umum
```

Kalau `--momen` dikosongkan: layout `gamer` otomatis pakai mode `gamer`, layout lain pakai mode `umum`.

**Bedanya nyata** — video gaming 36 menit, momen ke-2 di mode umum adalah *"Tadinya mau ke T.C.T, pisang, tapi ternyata udah tutup, kenapa?"* (cerita), sedangkan mode gamer mengambil *"gila gue merintis anjir parah gue gak tau..."* (teriakan + reaksi wajah + aksi game).

Alasan tiap momen otomatis terisi di `klip.json` (`teriakan · reaksi wajah · aksi game · kata gaming: gila, anjir, parah`), jadi kelihatan kenapa suatu klip dipilih.

> Mode gamer menambah satu kali pass ffmpeg untuk menghitung motion frame (gameplay + facecam, 4 fps, 64×64 abu-abu). Untuk video 36 menit ini sekitar 2–3 menit tambahan.

---

## 6d. Whisper di RAM Kecil (`--beam` & `--potong`)

Server kecil (RAM 3–4 GB) sering swap-thrash kalau pakai model besar. Dua flag ini yang azeite:

| Flag | Arti |
|------|------|
| `--beam N` | Strategi decode Whisper: `1` = greedy (cepat, hemat RAM), `5` = beam search (akurasi, boros). Default `5` |
| `--potong N` | Pecah audio jadi chunk N detik saat transkripsi (0 = off). Timestamp kata tetap dikembalikan ke waktu asli video |

```bash
# video panjang, RAM 4 GB → small + greedy + chunk 2 menit
uv run klip/klip.py video.mp4 --model small --beam 1 --potong 120 --layout gamer --facecam kamera.mp4
```

**Kenapa `medium` mentahan-nahan di RAM 3,6 GB** (terukur): model int8 ≈ 1,5 GB + workspace CTranslate2 → sistem swap-thrash, CPU efektif turun ke 7–12%, PSI memory `full` > 45%. `small` + `--potong` → CPU 166%, PSI 0,03, 19 chunk 120 detik selesai ~12 menit. Fix sebenarnya: RAM ≥ 8 GB.

---

---

## 6e. AI Produksi (semua tahap)

AI bisa nyusup ke **semua tahap produksi**, bukan cuma pilih momen. Tiap tahap opsional dan punya fallback ke heuristik lokal — kalau AI gagal atau tidak ada kunci, pipeline tetap jalan.

| Tahap | Yang dikerjakan AI | Fallback |
|-------|--------------------|----------|
| `transkrip` | Koreksi salah dengar ASR (tyo, nama kacau, slang keliru). Timing kata tidak diubah | transkrip mentah |
| `skor` | Nilai tiap window dengan rubric **2-second test** + bukti sinyal gaming (reaksi facecam, lonjakan suara, aksi game) | skor heuristik lokal |
| `hook` | Hook text (≤10 kata), judul YouTube, caption IG/TikTok + hashtag, alasan publish | judul lokal |
| `layout` | Saran layout per proyek (tunggal / facecam / pip) | layout manual |
| `qc` | Cek hasil render: durasi, resolusi, audio, frame hitam | QC lokal tetap jalan |

### Provider

`--ai openrouter` → **OpenRouter model FREE** (tanpa biaya, tapi rate-limited). Kuncinya di `klip/.env` atau lewat web UI (Pengaturan AI → OpenRouter).

Rantai model free (fallback otomatis saat 429/503), urut kualitas → kecepatan:

```
nvidia/nemotron-3-ultra-550b-a55b:free   → recursive/flint-v1.0:free
→ cohere/north-mini-code:free             → nvidia/nemotron-3.5-lightning:free
→ dots-studio/dots-3-note-preview:free    → particle-ai/particle-1:free
→ liquid/lfm-3-1.7b:free                  → baidu/ernie-5.5-flash-preview:free
```

Ganti rantainya sendiri:

```bash
uv run klip/klip.py video.mp4 --ai openrouter \
  --gaya '{"ai_tahap":"skor,hook","OPENROUTER_MODELS":"recursive/flint-v1.0:free"}'
```

### Hybrid: AI + bukti lokal

Skor akhir bukan murni penilaian AI:

```python
skor = skor_AI * 0.7 + heuristik_gamer * 0.3
```

Heuristik lokal = kata gaming + lonjakan suara + reaksi facecam + aksi gameplay. Bagian ini yang menangkap momen yang transkripnya jelek ("Gila-gila, keren-keren") — LLM dari teks doang akanrank-nya rendah.

### Contoh pemakaian

```bash
# hybrid penuh: pilih momen + metadata
uv run klip/klip.py gameplay.mp4 --layout gamer --facecam kamera.mp4 \
  --momen gamer --ai openrouter --ai-tahap skor,hook

# semua tahap
uv run klip/klip.py gameplay.mp4 --layout gamer --facecam kamera.mp4 \
  --momen gamer --ai openrouter --ai-tahap skor,hook,transkrip,qc

# matikan total AI (heuristik lokal saja)
uv run klip/klip.py gameplay.mp4 --momen gamer --ai-tahap off
```

Di web UI: tombol **"AI produksi"** (Lokal / OpenRouter free) + pilihan tahap. Di `./mulai`: prompts yang sama.

Hasil AI disimpan di `klip.json` per klip: `hook_text`, `judul_yt`, `caption_ig`, `caption_tiktok`, `why`, dan `qc` (hasil cek render).

> Batas free tier: 429 (rate limit) sering kena kalau request paralel. Rantai fallback otomatis pindah model; hasil tiap tahap di-cache di `.kerja/ai-*.json` jadi tidak bayar dua kali.

---

## 7. Kunci AI (Gemini) — Opsional

Tanpa kunci, pemilih momen pakai **lokal** (gratis, kualitas lebih sederhana). Kunci hanya perlu kalau mau `--ai gemini` atau bikin naskah Motion dengan AI.

### Cara isi kunci (pilih salah satu):

**A. Lewat menu (paling gampang):**
```bash
./mulai
# pilih 3 · Kunci AI, lalu tempel kunci saat muncul prompt "Kunci:"
# (layar tampak kosong saat tempel — itu normal, input disembunyikan)
```

**B. Lewat file:**
```bash
cp klip/.env.contoh klip/.env
chmod 600 klip/.env
# isi satu baris:  GEMINI_API_KEY=AIza... atau AQ....
```

**C. Lewat environment variable:**
```bash
export GEMINI_API_KEY="AIzaSy..."
```

**D. Lewat web UI** (kalau pernah nyalakan `studio.py`):
Kunci disimpan di `~/Isanovski Studio/pengaturan.env`, dan `./mulai` otomatis bisa baca dari sana.

### Lokasi kunci yang dibaca (urutan prioritas):

| Tempat | Prioritas |
|--------|-----------|
| `GEMINI_API_KEY` (environment) | 1 (tertinggi) |
| `klip/.env` | 2 |
| `~/Isanovski Studio/pengaturan.env` | 3 |

### Cek kunci:

```bash
uv run klip/klip.py --uji-ai gemini   # harus nyetak "SIAP"
```

Kunci format baru `AQ....` juga diterima. Jangan share kunci ke chat / issue / screenshot. File `klip/.env` sudah di-gitignore.

---

## 8. Watermark & Judul (default baru)

| Elemen | Default | Cara ubah |
|--------|---------|-----------|
| Watermark tengah | `isanovski Studio`, putih transparan ±50% | `./mulai` → ketik `-` untuk tanpa, atau teks lain. Manual: `--watermark "@akunmu"` atau `--watermark ""` |
| Judul atas | Tampil dari awal sampai klip habis, lalu memudar | Matikan: `--gaya '{"judul_buka":false}'` |
| Subtitle karaoke | Aktif, kata yang diucapkan menyala | Matikan: `--gaya '{"subtitle":false}'` |
| Progress bar | Aktif di dasar frame | Matikan: `--gaya '{"progres":false}'` |

Di `./mulai` menu 1, setelah pilih video, akan ditanya:

```
  Watermark tengah ('-' = tanpa) [isanovski Studio]:
```

- Enter = pakai `isanovski Studio`
- `-` = tanpa watermark
- Teks lain = watermark sesuai yang kamu ketik

---

## 9. Motion / Video Animasi (Menu 2)

Kalau mau bikin video dari nol berdasarkan topik (bukan potong video existing):

```bash
# Lewat menu:
./mulai → 2 · Topik jadi video animasi

# Manual:
cd motion && node naskah.mjs "topik kamu" --ai=gemini && cd ..
node motion/buat.mjs naskah/contoh.json --gaya=neon
```

Butuh Node.js + Remotion (pasang lewat `pasang-cloud.sh` tanpa `TANPA_NODE=1`).

---

## 10. Codespace — Perintah dari Nol

Repo sudah otomatis ada di `/workspaces/studio-clipper`. **Tidak perlu `git clone`.**

```bash
# Masuk ke folder (biasanya sudah ada di sini otomatis):
cd /workspaces/studio-clipper

# Update ke versi terbaru:
git pull

# Pasang dependensi (CLI saja, tanpa web UI):
TANPA_WEB=1 bash pasang-cloud.sh

# Jalankan menu:
./mulai
```

### Memasukkan video ke Codespace:

1. Seret file `.mp4` ke panel Explorer kiri (folder mana saja di dalam repo).
2. Jalankan `./mulai` → pilih **1** → videonya sudah muncul di daftar.

Atau dari laptop (butuh `gh auth refresh -h github.com -s codespace` sekali saja):

```bash
gh codespace cp ./video.mp4 remote:/workspaces/studio-clipper/
gh codespace cp remote:/workspaces/studio-clipper/hasil/klip-01.mp4 .
```

### Catatan penting Codespace:

| Hal | Keterangan |
|-----|------------|
| YouTube link | Hampir pasti gagal dari IP GitHub. Unduh di laptop, baru seret ke Codespace. |
| Codespace tidur | ±30 menit idle → render ikut mati. Pakai `tmux`: `tmux new -s klip`, lalu `tmux attach -t klip` |
| File hilang | Semua hilang kalau codespace dihapus. Unduh hasilnya dulu. |
| Disk | Terbatas ~32 GB. Hapus `hasil` dan video sumber yang nggak dipakai. Cek: `df -h .` |
| RAM | 3 GB. `whisper small` ±790 MB + Remotion ±1,5–2 GB → jangan jalan bareng-bareng. |

---

## 11. Troubleshooting

| Masalah | Solusi |
|---------|--------|
| `permission denied: ./mulai` | `chmod +x mulai` atau `python3 mulai` |
| `kunci AI: belum ada` | Isi lewat menu `./mulai` → 3, atau cek `uv run klip/klip.py --uji-ai gemini` |
| YouTube unduhan gagal | Unduh manual di laptop, seret file ke Codespace |
| Render macet / RAM habis | Pakai `--model tiny` atau `--model base`; jangan jalankan Remotion bareng |
| `Sign in to confirm you're not a bot` | YouTube blok IP. Pakai file lokal, bukan link YouTube |
| Hasil tidak muncul | Cek folder `hasil/`, atau `./mulai --hasil hasil/<nama>` |
| `uv` tidak ditemukan | Jalankan `TANPA_WEB=1 bash pasang-cloud.sh` dulu |

---

## 12. Struktur Repo

| File / Folder | Fungsi |
|---------------|--------|
| `./mulai` | Menu CLI interaktif (pintu masuk utama) |
| `klip/klip.py` | Pipeline potong video → klip 9:16 |
| `klip/README.md` | Detail klip.py (gaya JSON, B-roll, dll.) |
| `studio/` | Server web + UI (opsional, untuk laptop) |
| `motion/` | Video animasi dari topik (Remotion) |
| `suara/` | TTS VoxCPM2 (opsional) |
| `pasang-cloud.sh` | Pemasang dependensi untuk Linux / Codespace |
| `PANDUAN.md` | Panduan ini |
| `LISENSI.md` | Syarat pemakaian |

---

## 13. Lisensi

Template oleh **Isanovski Saputra** ([@isanovskisaputra](https://github.com/isanovskisaputra)) — https://isanovskisaputra.biz.id.

**Lisensi Nonkomersial Isanovski Studio 1.0**: boleh dipakai untuk belajar, pribadi, atau usaha sendiri; boleh diubah dan dibagikan gratis **dengan kredit utuh**; **dilarang dijual, dijual ulang, disewakan, atau dipakai untuk jasa berbayar ke pihak lain**. Teks lengkap: [`LISENSI.md`](LISENSI.md).

Pustaka pihak ketiga (Remotion, faster-whisper, yt-dlp, font OFL, dll.) tetap mengikuti lisensinya masing-masing.

---

> Rebrand sebagai turunan dari studio-isanovski. Kredit Isanovski Saputra tetap di sidebar footer, mobile footer, dan header HTML/commen — sesuai lisensi §2d / §3.
