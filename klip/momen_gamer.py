"""Pemilihan momen khusus gaming (layout gamer).

Bedanya dari `pilih_momen` generik di klip.py:
  - bukan cuma rata-rata energi suara, tapi PUNCAK energi (teriakan / kaget)
  - ditambah sinyal reaksi wajah dari file facecam (frame-to-frame motion)
  - ditambah sinyal aksi gameplay (frame motion gameplay vs garis dasar)
  - kamus kata/interjeksi khas gaming (kill, clutch, gg, anjir, wkwk, …)

Semua sinyal dikembalikan sebagai array per detik, lalu `skor_momen()` menggabungkannya.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import numpy as np

# ── 1. Kamus kata gaming ────────────────────────────────────────────────────
HOOK_GAME = re.compile(
    r"^(kill|killing|killed|death|die|died|dead|respawn|first\s?blood|ace|clutch|combo|"
    r"multi\s?kill|killstreak|headshot|frag|fragged|rage|rekt|rekted|slaughtered|"
    r"gg|wp|well\s?played|nice|no\s?way|insane|goated|clean|easy|clutched|"
    r"bunuh|mati|mampus|menang|kalah|menangin|round|ronde|skor|score|poin|"
    r"rank|mvp|boost|carry|carry\s?the|carry\s?team|throw|feeds|feeder|"
    r"gila|anjir|parah|mantap|sip|keren|babak|brutal|ng stabilisation|wtf|omg)", re.I)

INTERJEKSI = re.compile(r"\b(anjir|gila|parah|wtf|omg|wkwk+w|haha+|lol|nah|ah|sip|mantap|"
                        r"anjirrrr+|gilaaaa|parahhhh|no\s?way|insane|goated|gg)\b", re.I)

# kata yang menandai momen emosional (bukan cuma info)
EMOSI = re.compile(r"\b(gila|anjir|parah|wtf|omg|no\s?way|insane|goated|brutal|"
                   r"mantap|keren|mampus|nice|clutch|gg|kill|bunuh|mati)\b", re.I)


def _ffmpeg() -> str:
    return subprocess.run(["which", "ffmpeg"], capture_output=True, text=True).stdout.strip() or "ffmpeg"


def _wajah_aktif(path: Path) -> bool:
    """Cek cepat apakah ada audio di file (facecam biasanya tanpa suara gameplay)."""
    r = subprocess.run([_ffmpeg(), "-v", "error", "-i", str(path), "-t", "1", "-f", "null", "-"],
                       capture_output=True)
    return r.returncode == 0


def motion_per_detik(path: Path, fps: float = 4.0, sisi: int = 64) -> np.ndarray:
    """Motion per detik (mean absolute difference antar frame) dari video.

    Dipakai untuk: reaksi wajah (facecam) dan aksi gameplay.
    Frame di-downscale ke sisi x sisi abu-abu supaya murah.
    """
    cmd = [_ffmpeg(), "-v", "error", "-i", str(path),
           "-vf", f"fps={fps},scale={sisi}:{sisi}:flags=fast_bilinear,format=gray",
           "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    try:
        raw = subprocess.run(cmd, capture_output=True, timeout=1800).stdout
    except subprocess.TimeoutExpired:
        return np.zeros(1)
    n = len(raw) // (sisi * sisi)
    if n < 2:
        return np.zeros(1)
    arr = np.frombuffer(raw[: n * sisi * sisi], dtype=np.uint8).reshape(n, sisi, sisi).astype(np.float32)
    diff = np.abs(np.diff(arr, axis=0)).mean(axis=(1, 2))  # motion tiap frame
    # kelompokkan ke per detik
    per_detik = max(int(round(fps)), 1)
    pad = (-len(diff)) % per_detik
    if pad:
        diff = np.append(diff, np.zeros(pad, dtype=np.float32))
    return diff.reshape(-1, per_detik).max(axis=1)


def lonjakan(energi: np.ndarray) -> np.ndarray:
    """Deteksi lonjakan: nilai lebih besar dari baseline sekitar (rata-rata 5 detik)."""
    if len(energi) < 3:
        return np.zeros_like(energi)
    k = np.ones(5, dtype=np.float32) / 5
    baseline = np.convolve(energi, k, mode="same")
    return np.maximum(energi - baseline, 0)


def normalisasi(x: np.ndarray) -> np.ndarray:
    """Skala ke 0..1 (kalau datanya konstan → nol)."""
    if len(x) == 0:
        return x
    lo, hi = float(x.min()), float(x.max())
    if hi - lo < 1e-9:
        return np.zeros_like(x)
    return (x - lo) / (hi - lo)


def skor_momen(kal: list, energi: np.ndarray, lonjak: np.ndarray,
               reaksi: np.ndarray, aksi: np.ndarray,
               durasi: float, arahan: str = "") -> list[dict]:
    """Skor tiap rentang kalimat. Semua array sinyal ber-unit per detik."""
    kata_arahan = {w for w in re.findall(r"\w+", arahan.lower()) if len(w) > 3}

    def ambil(sig: np.ndarray, a: float, b: float, mode: str = "max") -> float:
        if len(sig) == 0:
            return 0.0
        i0, i1 = int(max(a, 0)), int(max(b, a + 1))
        i0 = min(i0, len(sig) - 1)
        i1 = min(i1, len(sig))
        if i1 <= i0:
            return float(sig[i0])
        bagian = sig[i0:i1]
        return float(bagian.max() if mode == "max" else bagian.mean())

    hasil = []
    for i, k in enumerate(kal):
        for j in range(i, len(kal)):
            a, b = k.mulai, kal[j].selesai
            pj = b - a
            if pj > durasi * 1.2:
                break
            if pj < durasi * 0.6:
                continue
            isi = kal[i:j + 1]
            kata = [x for s in isi for x in s.kata]
            teks = " ".join(s.teks for s in isi)
            semua_kata = re.findall(r"\w+", teks.lower())

            hooks = [bersih(x.teks) for x in kata if HOOK_GAME.match(bersih(x.teks))]
            hooks = list(dict.fromkeys(hooks))
            inter = INTERJEKSI.findall(teks.lower())
            emosi = EMOSI.findall(teks.lower())
            padat = len(semua_kata) / max(pj, 1)

            e_peak = ambil(energi, a, b, "max")
            e_lonjak = ambil(lonjak, a, b, "max")
            r_reaksi = ambil(reaksi, a, b, "max")
            r_aksi = ambil(aksi, a, b, "max")
            pembuka = bool(HOOK_GAME.match(bersih(k.kata[0].teks))) if k.kata else False

            skor = (e_peak * 16          # teriakan / kaget
                    + e_lonjak * 20       # lonjakan suara mendadak (reaksi)
                    + r_reaksi * 22       # facecam beriak → ekspresi kuat
                    + r_aksi * 10        # gameplay sedang rame
                    + len(hooks) * 9      # kata khas gaming
                    + len(set(inter)) * 6  # interjeksi: anjir, gila, wkwk
                    + len(set(emosi)) * 4  # kata emosi
                    + (12 if pembuka else 0)
                    - abs(pj - durasi) / durasi * 10)  # durasi jauh dari target
            if kata_arahan and kata_arahan & set(semua_kata):
                skor += 20

            alasan = []
            if e_lonjak > 0.35:
                alasan.append("teriakan")
            if r_reaksi > 0.4:
                alasan.append("reaksi wajah")
            if r_aksi > 0.5:
                alasan.append("aksi game")
            if hooks:
                alasan.append(f"kata gaming: {', '.join(hooks[:3])}")
            if inter:
                alasan.append("teriak/tertawa")
            if pembuka:
                alasan.append("pembuka kuat")
            if padat >= 2.6:
                alasan.append("bicara padat")
            if kata_arahan and kata_arahan & set(semua_kata):
                alasan.append("sesuai arahan")

            hasil.append({
                "mulai": round(a, 2), "selesai": round(b, 2),
                "teks": k.teks[:70], "skor": skor,
                "alasan": " · ".join(alasan) or "momen naturalistis",
                "sinyal": {
                    "energi": round(e_peak, 3), "lonjakan": round(e_lonjak, 3),
                    "reaksi": round(r_reaksi, 3), "aksi": round(r_aksi, 3),
                    "hooks": hooks[:6], "interjeksi": list(dict.fromkeys(inter))[:6],
                },
            })
    return hasil


def bersih(w: str) -> str:
    return w.strip().strip("\"'(),.?!:;…").lower()
