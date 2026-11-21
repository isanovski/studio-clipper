#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Klippy — wrapper sederhana untuk klip.py (alur seperti web UI).
Pertanyaanya cuma yang penting, sisanya di-otomatisasi."""

import os
import sys
from pathlib import Path

KLIP_PY = Path(__file__).resolve().parent / "klip.py"


def tanya(prompt, default=None):
    if default:
        return input(f"{prompt} [{default}]: ").strip() or default
    while True:
        v = input(f"{prompt}: ").strip()
        if v:
            return v
        print("Wajib diisi.")


def pilih(prompt, opsi, default=0) -> str:
    print(f"\n{prompt}")
    for i, o in enumerate(opsi, 1):
        tandai = " <== default" if i - 1 == default else ""
        print(f"  {i}. {o}{tandai}")
    while True:
        v = input(f"Pilih 1-{len(opsi)} [{default + 1}]: ").strip()
        if not v:
            return opsi[default]
        try:
            n = int(v)
            if 1 <= n <= len(opsi):
                return n - 1
        except ValueError:
            pass
        print("Pilihan tidak valid.")


def main():
    print("=== KLIPPY — Potong video jadi klip pendek ===\n")

    # 1. Sumber video
    sumber = tanya("Path file video (atau link YouTube)")
    if not Path(sumber).exists() and not sumber.startswith(("http://", "https://")):
        print(f"\nPeringatan: file '{sumber}' belum ditemukan di komputer ini.")
        input("Tekan Enter untuk tetap mencoba, atau Ctrl+C untuk batal.")

    # 2. Jumlah klip
    jumlah = tanya("Berapa klip yang diinginkan", "3")
    try:
        int(jumlah)
    except ValueError:
        jumlah = "3"

    # 3. Durasi per klip
    durasi = tanya("Durasi per klip (detik)", "30")
    try:
        int(durasi)
    except ValueError:
        durasi = "30"

    # 4. Layout
    layout = pilih("Pilih layout", ["tunggal", "split", "gamer"], default=0)
    layout = ["tunggal", "split", "gamer"][int(layout)]

    # 5. AI
    ai = pilih("Pilih AI untuk mencari momen", ["lokal", "deepseek", "openrouter", "gemini"], default=0)
    ai_map = {"lokal": "lokal", "deepseek": "openai", "openrouter": "openrouter", "gemini": "gemini"}
    ai = ai_map[ai]

    # 6. Model Whisper
    model = pilih("Pilih model Whisper", ["small", "medium"], default=0)
    model = ["small", "medium"][int(model)]

    # 7. Konfirmasi
    print("\n=== Ringkasan ===")
    print(f"  Sumber     : {sumber}")
    print(f"  Jumlah     : {jumlah} klip")
    print(f"  Durasi     : {durasi} detik")
    print(f"  Layout     : {layout}")
    print(f"  AI         : {ai}")
    print(f"  Model Whisper: {model}")
    konf = input("\nMulai proses? (Enter=y, n=batal): ").strip().lower()
    if konf in ("n", "no", "tidak"):
        print("Dibatalkan.")
        return

    # 8. Jalankan klip.py
    cmd = [
        sys.executable, str(KLIP_PY), sumber,
        "--keluar", "hasil-klip",
        "--jumlah", jumlah,
        "--durasi", durasi,
        "--layout", layout,
        "--ai", ai,
        "--model", model,
        "--momen", "umum",
        "--render",
    ]
    print("\nMenjalankan:\n  " + " ".join(cmd) + "\n")
    os.execv(sys.executable, cmd)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nDibatalkan oleh pengguna.")
        sys.exit(1)
