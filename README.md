# Isanovski Studio

Potong video panjang jadi klip 9:16. Semua diproses di mesin sendiri: tanpa kuota, tidak ada yang diunggah ke server orang lain.

## Install (satu kali)

```bash
git clone https://github.com/isanovskisaputra-source/studio-clipper.git
cd studio-clipper/klip

# Android/Termux:
pkg install python git ffmpeg
pip install uv
uv sync

# Linux/VPS:
sudo apt install python3 git ffmpeg
pip install uv
uv sync
```

## Pakai

```bash
./mulai
```

Ketik path video (contoh `/sdcard/Download/raditya.mp4` atau link YouTube), lalu Enter terus sampai selesai.

Hasil ada di folder `hasil-klip/`.

## Pilihan yang ditanya

| Pertanyaan | Pilihan | Default |
|---|---|---|
| Layout | tunggal / split / gamer | gamer |
| AI | lokal / deepseek / openrouter / gemini | lokal |
| Model Whisper | small / medium | small |

Semua bisa dikosongkan (pakai default).

## Kunci AI (opsional)

Tanpa kunci, pakai heuristik lokal. Mau lebih bagus? Isi di `klip/.env`:
```
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AIza...
OPENROUTER_API_KEY=sk-or-v1-...
```

## Batasan

- Model `small` ≈ 790 MB RAM, `medium` ≈ 1,6 GB
- Video 60 menit ≈ 2,5–5 jam transkripsi di 2 core
- Satu render dalam satu waktu

---

Lisensi Nonkomersial Isanovski Studio 1.0 — bebas untuk pribadi, dilarang jual.
