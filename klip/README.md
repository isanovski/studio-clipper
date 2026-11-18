# Klip — potong video panjang jadi klip pendek 9:16

Alat ini mengambil video panjang (file atau link YouTube), mencari momen terbaik, lalu memotongnya jadi klip **1080×1920**.
Setiap klip diberi subtitle karaoke dan bingkainya mengikuti wajah. Semua jalan di Mac sendiri, **tanpa watermark, tanpa kuota, dan tanpa API key**.
Kode ditulis dari nol oleh Maliki Motion. Riset dan pembandingnya ada di `dokumentasi/21-riset-alat-clipper.md`.

## Langkah 1 — Pasang uv (sekali saja)
Buka Terminal, lalu tempel:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
Tutup Terminal lalu buka lagi. uv akan memasang Python 3.12, ffmpeg, yt-dlp, dan Whisper secara otomatis. **Homebrew tidak diperlukan.**

## Langkah 2 — Masuk ke folder alat
```bash
cd alat/klip
```

## Opsi A — Gratis total (AI lokal memilih momen)
```bash
uv run klip.py video-saya.mp4
```
atau langsung dari YouTube:
```bash
uv run klip.py "https://www.youtube.com/watch?v=XXXX" --jumlah 3 --durasi 30
```
Saat pertama kali jalan, alat ini mengunduh paket dan model Whisper `medium` (±1,5 GB). Jalan berikutnya jauh lebih cepat.
Hasilnya ada di folder `hasil-klip/`: `klip-01.mp4`, `klip-02.mp4`, … dan `klip.json` (berisi skor dan alasan tiap klip).

Cara alat memilih momen: heatmap "Most replayed" YouTube (kalau ada), energi suara, kepadatan kata, kata hook
("ternyata", "rahasia", "jangan", …), dan kalimat tanya. Klip selalu mulai dan selesai di batas kalimat.

## Opsi B — Claude memilih momen (Claude gratis untuk video pendek, Claude Pro untuk video panjang)
```bash
uv run klip.py video-saya.mp4 --hanya-prompt
```
1. Buka `hasil-klip/prompt-claude.md`, salin semua isinya, lalu tempel ke Claude.
2. Simpan balasan JSON dari Claude sebagai `pilihan.json` di folder ini.
3. Render:
```bash
uv run klip.py video-saya.mp4 --pilihan pilihan.json
```
Pengguna Claude Pro + Claude Code cukup mengetik: *"jalankan klip.py untuk video ini, pilih 3 momen terbaik, lalu render"*.

## Pilihan lain
| Opsi | Arti |
|---|---|
| `--jumlah 5` | jumlah klip |
| `--durasi 45` | target detik per klip |
| `--model medium` | transkrip lebih akurat tapi lebih lambat (`tiny`, `base`, `small`, `medium`, `large-v3`) |
| `--bahasa id` | paksa bahasa transkrip |
| `--warna "#00E5FF"` | warna sorotan subtitle |
| `--tanpa-wajah` | bingkai di tengah, tidak mengikuti wajah |
| `--layout gamer` | game di atas + kamera wajah di bawah (mode 2 kamera gamer) |
| `--facecam FILE` | file video kamera untuk layout gamer (pakai bersama `--layout gamer`) |
| `--tanpa-subtitle` | klip tanpa subtitle |
| `--keluar folderku` | folder hasil |

## Kalau ada masalah
- **"Sign in to confirm you're not a bot"**: YouTube membatasi unduhan. Unduh videonya manual, lalu pakai file lokal.
- Peringatan `AVFAudioReceiver … implemented in both` aman diabaikan.
- Hanya potong video milik sendiri atau video yang sudah diberi izin.

## Pakai AI milikmu sendiri (opsional)
Alat ini tidak menyediakan AI. Kamu bisa menyambungkan AI yang sudah kamu punya:
```bash
cp .env.contoh .env
```
Buka `.env`, isi salah satu baris di bawah, lalu jalankan dengan `--ai`:

| `--ai` | Yang dibutuhkan | Biaya |
|---|---|---|
| `lokal` (default) | tidak ada | gratis, tanpa internet untuk AI |
| `gemini` | `GEMINI_API_KEY` dari aistudio.google.com/apikey | ada kuota gratis |
| `openai` | Ollama di laptop (`OPENAI_BASE_URL=http://localhost:11434/v1`), atau kunci OpenAI/OpenRouter/Groq | Ollama gratis; lainnya sesuai penyedia |

```bash
uv run klip.py video-saya.mp4 --ai gemini
```
**Catatan Claude Pro:** langganan Claude Pro **tidak** termasuk akses API (dibayar terpisah). Pengguna Pro cukup pakai
`--hanya-prompt` (tempel ke claude.ai) atau minta Claude Code menjalankan alat ini.
File `.env` berisi kuncimu. Jangan dibagikan ke orang lain.

## Dua tahap: analisis lalu render (dipakai Studio)
```bash
uv run klip.py video.mp4 --hanya-analisis --jumlah 10 --rentang 10:00-25:30
```
```bash
uv run klip.py --render --keluar hasil-klip --pilih 1,3 --gaya '{"rasio":"1:1","latar":"blur","banner":true,"awalan":"PART 1: ","gaya_sub":"kotak","musik":"musik.mp3","volume_musik":15,"suara":125}'
```
Kunci `--gaya`: `rasio` (9:16, 1:1, 4:3, 16:9) · `latar` (hitam, blur) · `fokus` (auto, kiri, tengah, kanan) · `layout` (tunggal, facecam, pip, gamer) ·
`banner`, `awalan`, `akhiran` · `subtitle`, `gaya_sub` (sorot, kotak, garis), `font`, `ukuran` (kecil, sedang, besar), `huruf` (kapital, judul, kecil),
`posisi_y` (persen dari atas), `warna` · `musik`, `volume_musik`, `sfx`, `suara` (persen). Subtitle sendiri: `--subtitle-file video.srt`.
Emoji di banner/subtitle dibuang otomatis (libass tidak bisa menggambar emoji berwarna).

## Lisensi
Template oleh Maliki Saputra (@malikisaputra) — https://malikisaputra.biz.id.
Gratis dengan **Lisensi Nonkomersial Maliki Studio 1.0**: boleh dipakai untuk belajar, keperluan pribadi, atau usaha/organisasimu sendiri,
boleh diubah dan dibagikan gratis dengan kredit utuh; **dilarang dijual, dijual ulang, disewakan, diunggah ke marketplace, atau dipakai
untuk jasa berbayar ke pihak lain**. Teks lengkap: [`LISENSI.md`](../LISENSI.md). Pustaka pihak ketiga (Remotion, faster-whisper, VoxCPM2,
font OFL, dll.) tetap mengikuti lisensinya masing-masing.

## Baru di versi 0.9 (sama dengan aplikasi Klip HP)
- **Momen dari kalimat utuh**: tiap momen punya skor (60–99), judul, dan alasan, mis. "pembuka kuat · ada pertanyaan".
- **Bingkai ikut pembicara**: alat mencari wajah yang gerak mulutnya paling seirama dengan suara, jadi pendengar yang tertawa tidak diikuti.
  Saat kamera di video asli berpindah, bingkai ikut pindah seketika. Kamera tidak bergeser lewat ruang kosong dan tidak kembali ke tengah.
  Deteksi wajah memakai YuNet (`model/`).
- **Subtitle**: kata kunci berwarna hijau, emoji otomatis (`emoji/`, Twemoji CC-BY 4.0), judul pembuka 3 detik, zoom halus di kata pemikat,
  progress bar, dan watermark opsional (`--watermark @akunmu`).
- **B-roll**: `--broll file --broll-file a.mp4 b.jpg` memakai file milikmu. `--broll pixabay` memakai API key Pixabay milikmu
  (`PIXABAY_API_KEY` di `.env`; gratis di pixabay.com/api/docs). Pixabay hanya mengambil video film (bukan animasi), dengan kueri dari kamus kata benda,
  cache 24 jam, dan "Video dari Pixabay" ditambahkan ke caption. Sisipan diberi zoom pelan dan sedikit digelapkan.
