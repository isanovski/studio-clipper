# Installer Isanovski Studio (tanpa Terminal)

Installer ini membawa Python 3.12, ffmpeg (lewat imageio-ffmpeg), dan semua paket Klip. Pengguna cukup klik, tidak perlu Terminal.
Versi ada di `alat/VERSI`. Naikkan angkanya sebelum membuat installer baru.

## Mac (.dmg)
```bash
bash alat/pemasang/bangun-mac.sh                       # Apple Silicon (arm64)
ARSITEKTUR=x86_64 bash alat/pemasang/bangun-mac.sh     # Mac Intel
```
Hasilnya ada di `alat/pemasang/hasil/Studio-Isanovski-<versi>-mac-<arsitektur>.dmg` (±190 MB).
- Cara pasang: buka .dmg, lalu seret ke Applications. Saat pertama dibuka: klik kanan → Buka.
  Aplikasi hanya ditandatangani **ad-hoc**, belum memakai akun Apple Developer, jadi Gatekeeper tetap bertanya sekali.
- Cara memperbarui: seret .dmg versi baru ke Applications, lalu pilih "Ganti". Data di `~/Isanovski Studio` tetap aman.
- Build Intel (`x86_64`) belum dicoba.

## Windows (Setup .exe)
Harus dibangun **di Windows 10/11 64-bit**, karena Inno Setup dan paket Windows tidak bisa dirakit dari Mac ini:
1. Pasang uv: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`
2. Pasang Inno Setup 6: https://jrsoftware.org/isdl.php (atau `winget install JRSoftware.InnoSetup`)
3. Di folder repo: `powershell -ExecutionPolicy Bypass -File alat\pemasang\bangun-windows.ps1`

Hasilnya `alat\pemasang\hasil\Pasang-Studio-Isanovski-<versi>-windows.exe`.
- Memasang ke `%LOCALAPPDATA%\Programs\Isanovski Studio`, tanpa hak admin, dengan pintasan di Start Menu dan Desktop.
- **Pembaruan**: `AppId` di `studio-isanovski.iss` tetap sama, jadi menjalankan installer baru langsung masuk wizard pembaruan
  (folder sama, versi lama diganti, hasil kerja di `%USERPROFILE%\Isanovski Studio` tidak disentuh). Jangan ubah `AppId`.
- Jendela memakai WebView2, yang sudah ada di Windows 10/11 yang diperbarui.
- **Belum diuji**, karena perlu mesin Windows. Yang perlu dicek di sana: build selesai, instal, Studio terbuka, satu klip berhasil dirender,
  lalu instal versi lebih baru di atasnya (wizard pembaruan).
- Windows SmartScreen akan memperingatkan karena installer belum ditandatangani sertifikat code-signing
  (pilih "Info selengkapnya" → "Tetap jalankan").

## Yang masih diunduh saat dipakai
- Model Whisper (±500 MB, sekali saja) saat pertama membuat klip.
- Motion butuh Node.js (nodejs.org). Suara VoxCPM memasang paketnya sendiri lewat uv yang ikut dibundel.

Template oleh Isanovski Saputra (@isanovskisaputra) — https://isanovskisaputra.biz.id · Lisensi Nonkomersial Isanovski Studio 1.0
