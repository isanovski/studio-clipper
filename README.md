# isanovski Studio

Potong video panjang jadi klip 9:16 (subtitle karaoke, bingkai ikut wajah), dan bikin motion graphic 9:16
dari satu topik. Semua diproses di mesin sendiri: tanpa watermark, tanpa kuota, tidak ada yang diunggah ke
server orang lain.

Fork pribadi dari [studio-maliki](https://github.com/malikisaputra-source/studio-maliki).
Kredit + lisensi di bagian paling bawah — wajib dibaca sebelum dibagikan.

---

## Cara kerja

```
browser / HP
     │  http://…:8787
     ▼
studio/studio.py ──── server lokal + seluruh UI (HTML/CSS/JS dalam satu file)
     │
     ├──► klip/klip.py ───── yt-dlp ─► faster-whisper ─► ffmpeg
     │                        (unduh)   (transkrip)      (potong 9:16 + subtitle + bingkai wajah)
     │
     └──► motion/buat.mjs ── naskah JSON ─► suara (TTS) ─► Remotion/Chromium ─► MP4

hasil kerja ──► ~/Studio Maliki/
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

## Jalan di GitHub Codespaces

Cocok kalau mau akses dari HP tanpa menyalakan laptop. Mesinnya milik GitHub, jadi **render tetap berat**
(tidak lebih cepat dari laptop) — ini soal "bisa diakses dari mana saja", bukan soal kecepatan.

1. Buka repo ini di GitHub → tombol **Code** → tab **Codespaces** → **Create codespace on main**.
2. Tunggu sampai terminal muncul di bawah (container siap).
3. Jalankan pemasang:

   ```bash
   bash pasang-cloud.sh
   ```

   Butuh **5–10 menit** dan sekitar **2 GB** (whisper, opencv, Remotion). Kalau hanya mau UI-nya dulu:

   ```bash
   LEWATI_KLIP=1 bash pasang-cloud.sh   # hemat ~1,5 GB, menu Klip belum bisa render
   TANPA_NODE=1 bash pasang-cloud.sh    # tanpa Node, menu Motion tidak bisa render
   ```

4. Buka tab **PORTS** (di panel bawah) → cari baris port **8787** → klik **Open in Browser**.
   Kalau perlu dari HP, klik kanan baris port itu → **Port Visibility** → **Public**, lalu buka URL
   `https://…-8787.app.github.dev` di HP.
5. Selesai. Hasil kerja ada di `~/Studio Maliki/` **di dalam codespace**.

Kalau codespace dihentikan atau di-restart, jalankan lagi:

```bash
bash pasang-cloud.sh
```

`studio.py` sudah menangani header `Origin` dari domain proxy Codespaces, jadi tombol-tombol di UI tidak
kena 403 (sudah diuji: Origin sama dengan Host → lolos, Origin situs lain → 403).

> Alur pemasangan di atas diuji di Linux lokal — bukan di Codespace sungguhan. Kalau ada langkah yang gagal,
> tempel 20 baris terakhir `~/Studio Maliki/studio.log` supaya kelihatan penyebabnya.

Cek cepat setelah start:

```bash
curl -s http://127.0.0.1:8787/ | grep -o "<title>[^<]*</title>"   # → <title>isanovski Studio</title>
```

### Yang perlu diingat soal Codespaces

- **Link YouTube hampir pasti gagal** dari IP GitHub (YouTube menolak IP datacenter). Untuk video YouTube,
  unduh di laptop lalu **unggah filenya** ke UI.
- Codespace **tidur sendiri** setelah ±30 menit tanpa aktivitas → server mati. Nyalakan lagi seperti di atas.
- Semua file **hilang** kalau codespace dihapus. Unduh hasil render sebelum menghapus.
- Kuota gratis akun pribadi ±120 core-hour/bulan. Render panjang memakai CPU penuh, jadi hitung-hitung.

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
