# isanovski Studio — Klip + Motion

Fork pribadi dari [studio-maliki](https://github.com/malikisaputra-source/studio-maliki), dipakai untuk
memotong video panjang jadi klip 9:16 dan bikin motion graphic dari satu topik. Semua diproses di
laptop sendiri: tanpa watermark, tanpa kuota, video tidak diunggah ke mana pun.

Repo ini **bukan** proyek publik — ini catatan pemakaian untuk mesin ini, biar nggak perlu ngulik ulang
dari nol tiap kali buka.

---

## Status mesin ini

| | |
|---|---|
| Repo | `/home/kage/studio-clipper` (branch `main`) |
| Remote | `origin` → `git@github.com:isanovski/studio-clipper` (via https) |
| OS | Ubuntu 24.04 |
| Python | 3.12.3 (wajib ≥3.10,<3.13) — dijalankan lewat `uv` 0.13.9 |
| Node | v26.13.1 (khusus Motion/Remotion) |
| Data + kunci AI | `~/Studio Maliki/` |
| Folder ini di GitHub | publik (fork) — **ada kredit pembuat asli, jangan dihapus** |

---

## Mulai cepat

```bash
isanovski-studio            # nyalakan + buka tab browser (lokal saja)
isanovski-studio mobile     # nyalakan, bisa dibuka dari HP di Wi-Fi yang sama
isanovski-studio status     # cek jalan atau tidak
isanovski-studio stop       # matikan
```

Alamat:

- di laptop → `http://127.0.0.1:8787`
- di HP → `http://192.168.0.107:8787` (IP bisa berubah kalau pindah jaringan; script mencetak ulang)

Kalau `isanovski-studio` tidak ketemu: `export PATH="$HOME/.local/bin:$PATH"` (biasanya sudah ada di
`~/.bashrc`). File aslinya di `~/.local/bin/studio-maliki-kontrol`; `isanovski-studio` dan
`studio-maliki` cuma pintasan ke situ.

Bisa juga dari menu aplikasi: cari **isanovski Studio**.

Tanpa launcher:

```bash
cd ~/studio-clipper
uv run studio/studio.py            # jendela aplikasi sendiri (WebKit/GTK)
uv run studio/studio.py --browser  # buka di browser
```

---

## Yang beda dari versi asli

1. **Merek** → `isanovski Studio`, ikon monogram "is" (`studio/aset/ikon-is.svg` + `.png`).
2. **Tema Ink/Ember** → gelap hangat + amber, terang krem; judul Instrument Serif, teks DM Sans.
3. **Responsif** → di ≤760px sidebar jadi tab bar bawah, konten 1 kolom, wizard layar penuh,
   input 16px, target sentuh ≥44px, aman dari notch (`env(safe-area-inset-*)`).
4. **Anti-cache** → server mengirim `Cache-Control: no-store` untuk html/css/js/gambar.
5. **Mode LAN** → `STUDIO_HOST=0.0.0.0` (opt-in, bawaan tetap `127.0.0.1`).
6. **`pasang-cloud.sh`** → pemasang untuk VM tanpa layar (Codespaces / Cloud Shell).

Kredit pembuat asli tetap ada di tiga tempat: footer sidebar, footer versi HP, dan komentar header
`studio/index.html` + `studio/studio.py`. Itu syarat lisensi, bukan hiasan.

---

## Kalau mau ubah tampilan

Semua di `studio/index.html` (satu file, CSS + JS inline):

| Mau ubah | Cari |
|---|---|
| Warna aksen | `--aksen` di blok `:root` (gelap) dan `:root[data-tema="terang"]` |
| Font judul | `--serif` (default Instrument Serif) |
| Nama/merek | `class="merek"`, `<title>`, dan teks di `.wiz-kepala` |
| Aturan HP | blok `@media (max-width:760px)` di akhir `<style>` |
| Ikon | `studio/aset/ikon-is.svg`, `.png`, plus favicon di `<head>` |

Setelah edit, tidak perlu restart server — cukup **Ctrl+Shift+R** di browser. Kalau tetap terlihat lama,
berarti browser-nya masih pegang cache: tutup tab, buka lagi.

Untuk cek tampilan tanpa browser manual (Playwright sudah terpasang di `~/.cache/ms-playwright`):

```bash
cd /tmp/opencode && uv run --with playwright --python 3.12 python cek-mobile.py
```

---

## Pakai di HP

```bash
isanovski-studio mobile
```

Lalu buka `http://<IP-laptop>:8787` di HP, Wi-Fi yang sama. Bisa **Add to Home Screen** — sudah ada
`theme-color` + `apple-mobile-web-app-capable`, jadi tampil tanpa address bar.

Yang perlu diingat:

- Video tetap diproses **di laptop**; HP cuma jadi layar dan remot. Laptop harus nyala.
- Mode `mobile` membuka port ke seluruh jaringan lokal. Siapa pun di Wi-Fi yang sama bisa mengendalikan
  app selama jalan → **matikan kalau di Wi-Fi kafe/kantor/kampus**.
- Upload video besar dari HP lewat Wi-Fi lambat; untuk video panjang mending dari laptop.

---

## Di mana hasil kerja

| Isi | Lokasi |
|---|---|
| Proyek, hasil render, riwayat | `~/Studio Maliki/` |
| Kunci AI & pengaturan | `~/Studio Maliki/pengaturan.env` (chmod 600) |
| Log server | `~/Studio Maliki/studio.log` |
| Model TTS lokal (kalau dipasang) | `~/Studio Maliki/.mesin/` |

Nama foldernya sengaja tetap "Studio Maliki" supaya proyek dan kunci lama tidak hilang. Jangan pernah
commit isi folder ini — `.gitignore` sudah menutup `hasil*/`, `out_*/`, `*.mp4`, `transkrip.json`, dst.

---

## AI

Kunci disimpan lokal, tidak dikirim ke mana pun selain penyedianya. Pilihan di **Pengaturan AI**:

- **Lokal** — tanpa kunci, gratis, kualitas paling sederhana.
- **Gemini** — kunci gratis dari [aistudio.google.com/apikey](https://aistudio.google.com/apikey).
- **Ollama** — gratis, offline, jalan di laptop (butuh RAM).
- **Langganan** — Claude Code (`claude -p`), Codex (`codex exec`), atau OpenCode (`opencode run`).
  Langganan chat **bukan** API key; ini memanggil CLI resminya, jadi butuh CLI-nya sudah login.

Suara narator Motion: suara bawaan OS, atau **VoxCPM2** (lokal, ±5 GB, 30 bahasa). Kalau belum perlu,
pakai suara bawaan dulu — VoxCPM2 tanpa GPU NVIDIA di Linux akan lambat.

---

## Kalau YouTube gagal diunduh

Dari IP datacenter (Codespaces, Cloud Shell, VPS) YouTube sering menolak. Itu batasan YouTube, bukan bug
app. `klip/klip.py` **belum** punya opsi `--cookies`; solusinya jalankan di laptop (IP rumahan) atau
serahkan file video langsung ke app (tombol pilih file).

---

## Sinkron dengan versi asli

```bash
cd ~/studio-clipper
git remote add upstream https://github.com/malikisaputra-source/studio-maliki.git   # sekali saja
git fetch upstream
git merge upstream/main
```

Konflik hampir pasti muncul di `studio/index.html` (kita mengubah merek + tema) dan `studio/studio.py`.
Aturan aman: **ambil fitur barunya, pertahankan merek dan tema kita**. Kalau ragu, `git checkout --theirs`
lalu tempel ulang blok tema; jangan sekadar "resolve" sampai kredit Maliki hilang.

Push perubahan sendiri:

```bash
git add -A && git commit -m "..." && git push origin main
```

Repo ini publik, jadi jangan pernah commit `pengaturan.env`, kunci API, atau hasil render berisi data
pribadi.

---

## Perintah CLI tanpa UI

```bash
# Klip: link/file → klip 9:16 (analisis lalu render)
uv run klip/klip.py -h
uv run klip/klip.py "link-atau-file.mp4" --jumlah 3 --durasi 30 --keluar hasil-klip

# Motion: naskah JSON → video (gaya bisa ditimpa)
node motion/buat.mjs naskah/contoh.json --gaya=neon

# Suara saja
uv run suara/suara.py --teks "Halo" --keluar halo.wav
```

Detail: [`klip/README.md`](klip/README.md), [`motion/README.md`](motion/README.md).

---

## Masalah yang sudah pernah kena

| Gejala | Sebab & solusi |
|---|---|
| UI tidak berubah setelah edit | Cache browser → sekarang server kirim `no-store`; tutup tab / Ctrl+Shift+R |
| `isanovski-studio` diam saja | Dulu: server sudah jalan, script cuma diam. Sekarang selalu buka tab baru |
| HP tidak bisa buka | Laptop mode lokal (`127.0.0.1`) → pakai `isanovski-studio mobile`, dan cek firewall |
| `uv run` minta Python beda | `studio.py` pakai PEP 723, butuh ≥3.10,<3.13. Jangan paksa Python 3.13 |
| Motion gagal render | Node belum ada / versi terlalu tua. Cek `node -v`, lalu `cd motion && npm install` |
| Port 8787 dipakai | `STUDIO_PORT=8788 isanovski-studio` |

---

## Lisensi (wajib dibaca kalau mau dibagikan)

Template oleh **Maliki Saputra** ([@malikisaputra](https://github.com/malikisaputra)) — https://malikisaputra.biz.id.

**Lisensi Nonkomersial Maliki Studio 1.0**: boleh dipakai untuk belajar, keperluan pribadi, atau usaha
sendiri; boleh diubah dan dibagikan gratis **dengan kredit utuh**; **dilarang dijual, dijual ulang,
disewakan, diunggah ke marketplace, atau dipakai untuk jasa berbayar ke pihak lain**.

Teks lengkap: [`LISENSI.md`](LISENSI.md). Pustaka pihak ketiga (Remotion, faster-whisper, VoxCPM2, font
OFL, dll.) tetap ikut lisensinya masing-masing.

Mau versi yang benar-benar bebas merek? Hubungi pembuat aslinya: [@malikisaputra](https://github.com/malikisaputra).

---

## Belum dikerjakan

- PWA beneran (manifest + service worker → install & shell offline).
- Rombak tata letak desktop: top bar, beranda ala editor, mode fokus, atau split view ala CapCut.
- `--cookies` untuk `klip/klip.py` (biar YouTube jalan dari IP datacenter).
