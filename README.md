# isanovski Studio

Potong video panjang jadi klip 9:16 (subtitle karaoke, bingkai ikut wajah), dan bikin motion graphic 9:16
dari satu topik. Semua diproses di mesin sendiri: tanpa kuota, tidak ada yang diunggah ke server orang
lain, dan watermark-nya milikmu sendiri (bisa dihapus sekali isi).

Fork pribadi dari [studio-maliki](https://github.com/malikisaputra-source/studio-maliki).
Kredit + lisensi di bagian paling bawah.

---

## Mulai cepat

Dua perintah. Sisanya cuma menu.

```bash
TANPA_WEB=1 bash pasang-cloud.sh     # sekali saja (±5–10 menit, ±2 GB)
./mulai                              # setiap kali mau kerja
```

Yang muncul:

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

Pilih **1**. Video yang sudah ada di folder repo (atau di folder unggahan web UI) langsung didaftar,
urut dari yang terbaru — tinggal ketik nomornya:

```
  Video yang ketemu (urut dari yang terbaru):

    1 video.mp4                                    62.3 MB
    2 unggahan/podcast-ep12.mp4                    71.5 MB
    3 tempel jalur lain / link YouTube
    4 batal

  Pilih video [1]:
```

Kalau videonya belum ada di daftar: pilih **tempel jalur lain**, lalu seret file ke terminal (jalurnya
otomatis ditempel) atau tempel link YouTube. Berikutnya ditanya jumlah klip, durasi, dan pemilih momen —
semua ada nilai bawaan, jadi **Enter terus saja** kalau tidak mau mikir. Progres berjalan di layar,
hasilnya langsung ditampilkan:

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

Kalau mau buka lagi hasil lama: `./mulai --hasil hasil/podcast-20261118-1411`

## Cara kerja

```
                 ┌── browser / HP ──┐        (opsional, di laptop)
                 │  http://…:8787   │
                 ▼                  │
          studio/studio.py ─────────┘   server lokal + seluruh UI (HTML/CSS/JS satu file)
                 │
   ./mulai ──────┤                      menu terminal (tanpa browser)
                 │
     ┌───────────┴────────────┐
     ▼                        ▼
klip/klip.py               motion/buat.mjs
yt-dlp ► faster-whisper    naskah JSON ► suara (TTS)
 ► ffmpeg                    ► Remotion/Chromium ► MP4
(potong 9:16, subtitle,
 bingkai ikut wajah)

hasil kerja ──► hasil/     ·   motion/hasil/
```

- **`./mulai` cuma menu.** Ia menyusun perintah, menjalankannya, lalu menampilkan progres. Tidak butuh
  dependensi tambahan — Python 3 bawaan sudah cukup.
- **`klip.py` dan `buat.mjs` bisa dipakai langsung** tanpa menu (lihat [Perintah manual](#perintah-manual)).
- **Tidak ada database, tidak ada cloud.** Hasil ada di folder `hasil/`, kunci AI di `klip/.env`.

### Yang ditempel di klip

| Elemen | Bawaannya | Cara mengubah |
|---|---|---|
| Subtitle karaoke | aktif, kata yang diucapkan menyala | menu → jumlah/durasi, atau `--gaya '{"subtitle":false}'` |
| Judul di atas | aktif, **tampil dari awal sampai klip habis** lalu memudar | `--gaya '{"judul_buka":false}'` untuk mematikan |
| Watermark tengah | `isanovski Studio`, putih transparan ±50%, pas di tengah | `--watermark "namamu"`, atau `--watermark ""` untuk tanpa watermark |
| Progress bar | aktif di dasar frame | `--gaya '{"progres":false}'` |

Di `./mulai` ada satu pertanyaan tambahan:

```
  Watermark tengah ('-' = tanpa) [isanovski Studio]:
```

Enter = pakai bawaan, ketik `-` = tanpa watermark, atau ketik teks lain. Di web UI, kolom **Watermark
tengah** ada di panel gaya (kosongkan kalau tidak mau).

> Kalau banner atas aktif, judul di atas digantikan banner — jadi teks judul tidak dobel.

## Isi repo

| Folder / file | Isi |
|---|---|
| `mulai` | menu CLI interaktif — pintu masuk yang disarankan |
| `studio/` | `studio.py` (server + API) dan `index.html` (seluruh UI web) |
| `klip/` | `klip.py` — video panjang → klip pendek. Detail: `klip/README.md` |
| `motion/` | `buat.mjs` — naskah → video animasi (Remotion). Detail: `motion/README.md` |
| `suara/` | `suara.py` — teks → WAV (VoxCPM2, opsional) |
| `pasang-cloud.sh` | pemasang dependensi untuk Linux / Codespaces / Cloud Shell |
| `LISENSI.md` | syarat pemakaian |

## Isi `.env` (kunci AI)

**Opsional.** Tanpa kunci, pemilih momen memakai heuristik lokal (gratis, kualitas lebih sederhana).
Kunci hanya perlu kalau mau `--ai gemini` atau bikin naskah Motion dengan AI.

Paling gampang lewat menu: **`./mulai` → 3 · Kunci AI**. Kuncinya disembunyikan saat ditempel, disimpan di
`klip/.env` dengan izin 600, lalu langsung diuji.

Manual:

```bash
cp klip/.env.contoh klip/.env
chmod 600 klip/.env
# lalu isi satu baris:  GEMINI_API_KEY=AIza...
```

Kunci gratis: https://aistudio.google.com/apikey

Kalau tidak mau menyimpan di file (dan tetap ada setelah codespace di-rebuild), simpan sebagai
**Codespace secret**: GitHub → repo **Settings** → **Secrets and variables** → **Codespaces** →
**New repository secret**, nama `GEMINI_API_KEY`.

Cek kunci:

```bash
uv run klip/klip.py --uji-ai gemini
```

`klip/.gitignore` sudah menutup `.env`, jadi kunci tidak ikut ter-commit. Tetap jangan tempel isinya ke
chat, issue, atau screenshot.

### Kalau menu bilang "kunci belum ada"

Kunci bisa berada di tiga tempat, dan `./mulai` membaca ketiganya:

| Tempat | Diisi kapan |
|---|---|
| variabel lingkungan `GEMINI_API_KEY` | `export …` di terminal, atau Codespace secret |
| `klip/.env` | lewat `./mulai` → **3 · Kunci AI** |
| `~/Studio Maliki/pengaturan.env` | lewat **web UI** → Pengaturan AI (kunci yang sama, tidak perlu diisi ulang) |

Cek cepat tanpa menu:

```bash
uv run klip/klip.py --uji-ai gemini     # → SIAP
```

Kalau tetap belum terbaca:

- Kunci ditempel di prompt yang salah. Tempel **hanya saat muncul `Kunci:`** di menu 3 (input disembunyikan,
  jadi layar tampak kosong saat kamu tempel — itu normal).
- Kunci masih berawalan `GEMINI_API_KEY=` atau terbungkus kutip — sekarang otomatis dibersihkan.
- Kunci format baru Gemini berawalan `AQ.` (bukan `AIza…`) — diterima; yang penting tanpa spasi/baris baru.
- Codespace secret baru terbaca setelah codespace **stop → start** (restart saja tidak cukup).

## Jalan di laptop (web UI)

Menu CLI di atas sudah cukup, tapi kalau mau tampilan web:

```bash
isanovski-studio              # nyalakan + buka browser (lokal saja)
isanovski-studio mobile       # bisa dibuka dari HP di Wi-Fi yang sama
isanovski-studio stop         # matikan
```

Alamat `http://127.0.0.1:8787`. Tanpa launcher:

```bash
uv run studio/studio.py --browser
```

## Codespace: perintah dari nol

Repo sudah otomatis ada di `/workspaces/studio-clipper` — **tidak perlu `git clone`**.

Buka repo → **Code** → **Codespaces** → **Create codespace on main**, tunggu terminal, lalu:

```bash
TANPA_WEB=1 bash pasang-cloud.sh
./mulai
```

`TANPA_WEB=1` = pasang dependensi saja, jangan nyalakan server web.

Masukkan video dengan **seret file ke panel Explorer** (folder mana saja). Setelah itu `./mulai` → **1**,
dan videonya sudah muncul di daftar — tidak perlu mengetik nama file. Ambil hasilnya: klik kanan `.mp4`
di Explorer → **Download**.

Atau dari laptopmu (butuh `gh auth refresh -h github.com -s codespace` sekali saja):

```bash
gh codespace cp ./video.mp4 remote:/workspaces/studio-clipper/
gh codespace cp remote:/workspaces/studio-clipper/hasil/klip-01.mp4 .
```

### Yang perlu diingat di Codespace

- **Link YouTube hampir pasti gagal** dari IP GitHub. Unduh di laptop, seret filenya ke codespace.
- **Codespace tidur ±30 menit idle** → render ikut mati. Jalankan di `tmux`: `tmux new -s klip`, lalu
  `tmux attach -t klip` untuk menyambung lagi.
- **Semua file hilang** kalau codespace dihapus. Unduh hasilnya dulu.
- Kuota gratis ±120 core-hour/bulan. Transkripsi video 1 jam memakan CPU penuh **±2,5–5 jam** di 2 core.

## Batasan yang sudah terbukti

| Hal | Kenyataan |
|---|---|
| Berat render | whisper `small` ≈ **0,2–0,4× realtime** di 2 vCPU; encode 1080×1920 ≈ **0,5× realtime** |
| RAM | whisper `small` puncak **±790 MB**; Remotion ±1,5–2 GB → **jangan bersamaan** |
| Run pertama | unduh model whisper `small` ±464 MB |
| Satu pekerjaan | satu render dalam satu waktu (`studio.py` menolak job kedua) |
| Video 60 menit | transkripsi bisa **2,5–5 jam** di mesin 2 core |

## Perintah manual

Kalau tidak mau pakai menu:

| Tujuan | Perintah |
|---|---|
| analisis + render | `uv run klip/klip.py "v.mp4" --jumlah 3 --durasi 30 --keluar hasil-x` |
| mode gamer (2 kamera) | `... --layout gamer --facecam kamera.mp4` |
| ganti watermark | `... --watermark "@akunmu"` (kosongkan `""` = tanpa watermark) |
| pakai Gemini | `... --ai gemini` |
| analisis saja | `uv run klip/klip.py "v.mp4" --hanya-analisis --keluar hasil-x` |
| render ulang pilihan | `uv run klip/klip.py --keluar hasil-x --render --pilih 1,3` |
| semua opsi | `uv run klip/klip.py -h` |
| naskah Motion | `cd motion && node naskah.mjs "topik" --ai=gemini && cd ..` |
| render Motion | `node motion/buat.mjs naskah/contoh.json --gaya=neon` |
| pasang dependensi | `TANPA_WEB=1 bash pasang-cloud.sh` |
| pasang + web UI | `bash pasang-cloud.sh` |

## Lisensi

Template oleh **Maliki Saputra** ([@malikisaputra](https://github.com/malikisaputra)) — https://malikisaputra.biz.id.

**Lisensi Nonkomersial Maliki Studio 1.0**: boleh dipakai untuk belajar, pribadi, atau usaha sendiri; boleh
diubah dan dibagikan gratis **dengan kredit utuh**; **dilarang dijual, dijual ulang, disewakan, atau dipakai
untuk jasa berbayar ke pihak lain**. Teks lengkap: [`LISENSI.md`](LISENSI.md).
