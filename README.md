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

## Jalan di GitHub Codespaces (CLI, tanpa web UI)

Codespaces di sini dipakai sebagai **mesin render tanpa layar**. Tidak perlu web UI, tidak perlu port
forwarding, tidak perlu buka browser di dalam codespace — semuanya lewat terminal.

### 1. Buat codespace

Repo di GitHub → **Code** → tab **Codespaces** → **Create codespace on main**. Tunggu terminal muncul.

### 2. Pasang dependensi saja

```bash
TANPA_WEB=1 bash pasang-cloud.sh
```

±5–10 menit, ±2 GB (whisper, opencv, Remotion). `TANPA_WEB=1` artinya **jangan nyalakan server web**;
setelah selesai skrip cuma mencetak contoh perintah lalu keluar.

Kalau Motion tidak dipakai: `TANPA_WEB=1 TANPA_NODE=1 bash pasang-cloud.sh` (hemat ~400 MB).
Kalau Klip tidak dipakai: tambahkan `LEWATI_KLIP=1` (hemat ~1,5 GB).

### 3. Masukkan video

- **Seret file** ke panel Explorer di kiri (folder mana saja, misal root repo).
- Atau dari laptopmu (butuh `gh auth refresh -h github.com -s codespace` sekali saja):
  `gh codespace cp ./video.mp4 remote:/workspaces/studio-clipper/`

### 4. Render klip

```bash
uv run klip/klip.py "video.mp4" --jumlah 3 --durasi 30 --keluar hasil-klip
```

Yang terjadi (semuanya tercetak di terminal, ini contoh):

```
• Video: video — 43 menit, 1920x1080
• Transkripsi dengan faster-whisper model 'small' …
• Bahasa terdeteksi: id, 812 kalimat.
• Mencari momen terbaik …
• Analisis selesai: 3 momen.
• Render 1/3 klip-01.mp4: 12:04–12:34  "…"
• Selesai. 3 klip di hasil-klip
```

Isi `hasil-klip/`:

| File | Isi |
|---|---|
| `klip-01.mp4`, `klip-02.mp4`, … | klip 9:16 siap unggah |
| `klip.json` | skor, judul, hook, kutipan, caption — bisa diedit lalu render ulang |
| `transkrip.json` | transkrip lengkap |
| `info.json`, `gambar.jpg`, `gaya.json` | metadata, thumbnail, gaya subtitle |

Dua tahap (hemat waktu kalau cuma mau lihat momen dulu):

```bash
uv run klip/klip.py "video.mp4" --hanya-analisis --keluar hasil-klip   # analisis saja
uv run klip/klip.py --keluar hasil-klip --render --pilih 1,3           # render pilihan
```

Opsi yang sering dipakai:

| Opsi | Arti |
|---|---|
| `--jumlah 5 --durasi 45` | 5 klip, target 45 detik |
| `--arahan "momen lucu"` | fokus pencarian momen |
| `--rentang 10:00-25:30` | hanya analisis bagian itu |
| `--tanpa-wajah` | bingkai tengah, tidak mengikuti wajah |
| `--tanpa-subtitle` | tanpa subtitle |
| `--pilih 1,3` | render klip nomor 1 dan 3 saja |
| `--ai gemini` | pemilih momen pakai Gemini (butuh `GEMINI_API_KEY`) |

Kunci AI untuk CLI ditaruh di environment atau `klip/.env`:

```bash
export GEMINI_API_KEY="..."          # atau tulis di klip/.env
```

Tanpa kunci, pemilih momen memakai heuristik **lokal** (gratis, kualitas lebih sederhana).

### 5. Motion (kalau perlu)

```bash
node motion/buat.mjs naskah/contoh.json --gaya=neon --suara=tanpa
```

Hasil: `motion/hasil/<nama>-<gaya>.mp4`. Naskah JSON bisa ditulis tangan atau dibuat AI lewat
`node motion/naskah.mjs "topik video" --ai=gemini`.

### 6. Ambil hasilnya

Klik kanan file `.mp4` di Explorer → **Download**.
Atau dari laptopmu: `gh codespace cp remote:/workspaces/studio-clipper/hasil-klip/klip-01.mp4 .`

### Yang harus diingat

- **Codespace tidur setelah ±30 menit tanpa aktivitas** → render yang sedang jalan ikut mati. Biarkan tab
  VS Code terbuka, atau jalankan di `tmux` supaya bisa disambung lagi: `tmux new -s klip`.
- **Link YouTube hampir pasti gagal** dari IP GitHub (YouTube menolak IP datacenter). Unduh videonya di
  laptop, lalu seret filenya ke codespace.
- **File hilang** kalau codespace dihapus. Unduh hasil sebelum menghapus.
- Kuota gratis akun pribadi ±120 core-hour/bulan. Transkripsi video 1 jam memakai CPU penuh selama
  **±2,5–5 jam** di mesin 2 core — hitung pemakaianmu.
- `TANPA_WEB=1` hanya soal tidak menyalakan web. Kalau nanti mau UI-nya, jalankan `bash pasang-cloud.sh`
  tanpa variabel itu, lalu buka lewat tab PORTS seperti biasa.

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
