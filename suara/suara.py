# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = [
#   "voxcpm>=2.0",
#   "soundfile>=0.12",
# ]
# ///
# kredit-isanovski: Template oleh Isanovski Saputra (@isanovskisaputra) — https://isanovskisaputra.biz.id · Lisensi Nonkomersial Isanovski Studio 1.0 (alat/LISENSI.md): dilarang dijual ulang.
"""Suara AI lokal untuk Isanovski Studio memakai VoxCPM2 (OpenBMB, Apache-2.0).

Satu kali muat model untuk semua adegan. Tiga mode:
  - bawaan          : suara netral VoxCPM2
  - desain          : suara dari deskripsi, mis. "pria muda, hangat, bersemangat"
  - clone           : meniru suara dari rekaman referensi 10–20 detik (HANYA suara sendiri / yang sudah memberi izin)

Pakai:
  uv run suara.py --cek                         # unduh/cek model saja
  uv run suara.py --teks "Halo semuanya" --keluar halo.wav [--referensi suaraku.wav] [--desain "..."]
  uv run suara.py --daftar adegan.json --folder hasil/   # adegan.json = ["kalimat 1", "kalimat 2", ...]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

MODEL = "openbmb/VoxCPM2"


def log(m: str) -> None:
    print(f"• {m}", flush=True)


def muat():
    from voxcpm import VoxCPM
    log(f"Memuat {MODEL} (pertama kali mengunduh ±5 GB)…")
    t = time.time()
    m = VoxCPM.from_pretrained(MODEL, load_denoiser=False)
    log(f"Model siap ({time.time() - t:.0f} dtk).")
    return m


def buat(model, teks: str, keluar: Path, referensi: str | None, desain: str | None, seed: int) -> float:
    import soundfile as sf
    isi = f"({desain}){teks}" if desain else teks
    import torch
    torch.manual_seed(seed)  # versi voxcpm terpasang belum menerima argumen seed (README terbaru menyebutnya)
    arg = dict(text=isi, cfg_value=2.0, inference_timesteps=10)
    if referensi:
        arg["reference_wav_path"] = referensi
    t = time.time()
    wav = model.generate(**arg)
    sr = model.tts_model.sample_rate
    keluar.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(keluar), wav, sr, subtype="PCM_16")
    durasi = len(wav) / sr
    log(f"{keluar.name}: {durasi:.1f} dtk audio dalam {time.time() - t:.1f} dtk")
    return durasi


def main():
    p = argparse.ArgumentParser(description="Suara AI lokal (VoxCPM2)")
    p.add_argument("--cek", action="store_true", help="unduh & muat model lalu keluar")
    p.add_argument("--teks")
    p.add_argument("--keluar", default="suara.wav")
    p.add_argument("--daftar", help="JSON berisi daftar kalimat")
    p.add_argument("--folder", default="suara-hasil")
    p.add_argument("--referensi", help="rekaman WAV untuk clone (suara sendiri / berizin)")
    p.add_argument("--desain", help="deskripsi suara, mis. 'pria muda, hangat'")
    p.add_argument("--seed", type=int, default=42)
    a = p.parse_args()
    if a.referensi and not Path(a.referensi).exists():
        sys.exit(f"Rekaman referensi tidak ditemukan: {a.referensi}")
    model = muat()
    if a.cek:
        return
    if a.daftar:
        kalimat = json.loads(Path(a.daftar).read_text(encoding="utf-8"))
        for i, k in enumerate(kalimat, 1):
            if not k:  # adegan video/klip: tidak perlu suara
                continue
            buat(model, k, Path(a.folder) / f"{i:02d}.wav", a.referensi, a.desain, a.seed)
    elif a.teks:
        buat(model, a.teks, Path(a.keluar), a.referensi, a.desain, a.seed)
    else:
        sys.exit("Isi --teks atau --daftar.")


if __name__ == "__main__":
    main()
