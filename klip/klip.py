# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = [
#   "yt-dlp>=2025.1.1",
#   "imageio-ffmpeg>=0.6.0",
#   "faster-whisper>=1.1.0",
#   "opencv-python-headless>=4.9,<5",
#   "numpy>=1.26",
#   "google-genai>=1.0",
# ]
# ///
# kredit-isanovski: Template oleh Isanovski Saputra (@isanovskisaputra) — https://isanovskisaputra.biz.id · Lisensi Nonkomersial Isanovski Studio 1.0 (alat/LISENSI.md): dilarang dijual ulang.
"""Klip — potong video panjang jadi klip pendek 9:16 (TikTok/Reels/Shorts).

Ditulis dari nol oleh Isanovski Motion. Jalan lokal di Mac, tanpa API berbayar.

Contoh:
  uv run klip.py video.mp4
  uv run klip.py "https://www.youtube.com/watch?v=..." --jumlah 3 --durasi 30
  uv run klip.py video.mp4 --hanya-prompt          # Opsi B: siapkan prompt untuk Claude
  uv run klip.py video.mp4 --pilihan pilihan.json  # Opsi B: render pilihan Claude
  uv run klip.py video.mp4 --ai gemini              # pakai AI milik pengguna (kunci di file .env)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path

import numpy as np

try:
    from pytrends.request import TrendReq
    _HAS_PYTRENDS = True
except Exception:
    _HAS_PYTRENDS = False

from framing import frame_shot, layout_filter, load_model, is_installed  # type: ignore

KATA_HOOK = {
    # kata yang sering membuka momen menarik (ID + EN)
    "rahasia", "ternyata", "jangan", "kenapa", "gimana", "bagaimana", "penting", "masalahnya",
    "kesalahan", "cara", "tips", "gila", "serius", "pertama", "akhirnya", "intinya", "wow",
    "secret", "never", "why", "how", "mistake", "actually", "important", "crazy",
}


def ffmpeg() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def log(msg: str) -> None:
    print(f"• {msg}", flush=True)


# ── 1. Sumber video ─────────────────────────────────────────────────────────
def ambil_sumber(sumber: str, kerja: Path) -> tuple[Path, list[dict], str]:
    """Kembalikan (file video, heatmap YouTube atau [], judul)."""
    if re.match(r"^https?://", sumber):
        import yt_dlp
        log("Mengunduh video (maks 1080p) dengan yt-dlp…")
        opsi = {
            "outtmpl": str(kerja / "sumber.%(ext)s"),
            "format": "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080][ext=mp4]/b",
            "merge_output_format": "mp4",
            "ffmpeg_location": ffmpeg(),
            "quiet": True, "no_warnings": True, "noprogress": True,
            "js_runtimes": {"node": {}, "deno": {}},  # yt-dlp butuh runtime JS untuk YouTube
        }
        with yt_dlp.YoutubeDL(opsi) as ydl:
            info = ydl.extract_info(sumber, download=True)
        file = next(kerja.glob("sumber.*"))
        return file, info.get("heatmap") or [], info.get("title") or "video"
    p = Path(sumber).expanduser().resolve()
    if not p.exists():
        sys.exit(f"File tidak ditemukan: {p}")
    return p, [], p.stem


def info_video(file: Path) -> tuple[float, int, int]:
    import cv2
    cap = cv2.VideoCapture(str(file))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    n = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    return (n / fps if n else 0.0), w, h


def ada_audio(file: Path) -> bool:
    """True kalau video sumber punya setidaknya satu stream audio."""
    try:
        r = subprocess.run(
            [ffmpeg(), "-v", "error", "-i", str(file), "-map", "0:a", "-f", "null", "-"],
            capture_output=True, text=True, timeout=30)
        return r.returncode == 0
    except Exception:
        return False


# ── 2. Energi audio per detik ───────────────────────────────────────────────
def energi_audio(file: Path) -> np.ndarray:
    sr = 16000
    raw = subprocess.run(
        [ffmpeg(), "-v", "error", "-i", str(file), "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"],
        capture_output=True, check=True).stdout
    a = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
    n = len(a) // sr
    if n == 0:
        return np.zeros(1)
    rms = np.sqrt((a[: n * sr].reshape(n, sr) ** 2).mean(axis=1))
    return (rms - rms.min()) / (np.ptp(rms) + 1e-9)


# ── 3. Transkrip ────────────────────────────────────────────────────────────
@dataclass
class Kata:
    mulai: float
    selesai: float
    teks: str


@dataclass
class Kalimat:
    mulai: float
    selesai: float
    teks: str
    kata: list[Kata]


def transkrip(file: Path, model: str, bahasa: str | None, beam: int = 5, potong: int = 0) -> list[Kalimat]:
    """Transkripsi dengan faster-whisper.

    potong > 0 → audio dipecah jadi chunk detik itu (default 120) dan diproses satu per satu.
    Gunanya: model besar (medium/large) di RAM kecil tidak swap-thrash, karena peak memory per chunk kecil.
    Timestamp kata digeser balik ke waktu asli video.
    """
    from faster_whisper import WhisperModel
    log(f"Transkripsi dengan faster-whisper model '{model}' (pertama kali akan mengunduh model)…")
    log("   Memuat model Whisper (tunggu download pertama kali bisa lama)…")
    m = WhisperModel(model, device="cpu", compute_type="int8", cpu_threads=max(1, (os.cpu_count() or 2)))
    log(f"   Model {model} siap. Mulai transkripsi…")
    sr = 16000  # decode sendiri dengan ffmpeg bawaan → tidak bergantung versi PyAV
    raw = subprocess.run([ffmpeg(), "-v", "error", "-i", str(file), "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
    # Akurasi bahasa Indonesia lisan: beam search, tanpa "condition_on_previous_text" (mencegah salah dengar yang
    # menular ke kalimat berikutnya / pengulangan), dan prompt awal berisi gaya bahasa sehari-hari sebagai petunjuk ejaan.
    petunjuk = ("Percakapan santai bahasa Indonesia: nggak, enggak, gimana, kayak, banget, sih, dong, kok, gue, lo, "
                "YouTube, podcast, konten, viral.") if (bahasa or "id") == "id" else None
    hasil: list[Kalimat] = []
    bahasa_deteksi = ""
    if potong > 0:
        n = max(1, (len(audio) + sr * potong - 1) // (sr * potong))
        for i in range(n):
            a0 = i * potong * sr
            a1 = min(len(audio), (i + 1) * potong * sr)
            if a1 <= a0:
                break
            off = a0 / sr
            segs, info = m.transcribe(audio[a0:a1], language=bahasa, word_timestamps=True, vad_filter=True,
                                      beam_size=beam, condition_on_previous_text=False, initial_prompt=petunjuk)
            for s in segs:
                kata = [Kata(w.start + off, w.end + off, w.word.strip()) for w in (s.words or []) if w.word.strip()]
                hasil.append(Kalimat(s.start + off, s.end + off, s.text.strip(), kata))
            bahasa_deteksi = info.language
            log(f"   Chunk {i + 1}/{n} selesai ({off:.0f}s–{a1 / sr:.0f}s), total {len(hasil)} kalimat.")
    else:
        segs, info = m.transcribe(audio, language=bahasa, word_timestamps=True, vad_filter=True, beam_size=beam,
                              condition_on_previous_text=False, initial_prompt=petunjuk, log_progress=True)
        for s in segs:
            kata = [Kata(w.start, w.end, w.word.strip()) for w in (s.words or []) if w.word.strip()]
            hasil.append(Kalimat(s.start, s.end, s.text.strip(), kata))
        bahasa_deteksi = info.language
    log(f"Bahasa terdeteksi: {bahasa_deteksi}, {len(hasil)} kalimat.")
    return hasil


# ── 4. Pilih momen (Opsi A, gratis) ─────────────────────────────────────────
@dataclass
class Klip:
    mulai: float
    selesai: float
    judul: str
    skor: float = 0.0
    alasan: str = ""
    caption: str = ""
    kutipan: str = ""
    kata_kunci: list = field(default_factory=list)


def nilai_heatmap(heatmap: list[dict], a: float, b: float) -> float:
    vals = [p.get("value", 0) for p in heatmap if p.get("end_time", 0) > a and p.get("start_time", 0) < b]
    return float(np.mean(vals)) if vals else 0.0


HOOK_AWAL = re.compile(r"^(rahasia|ternyata|kenapa|mengapa|gimana|bagaimana|cara|jangan|penting|gratis|pertama|intinya|tips|salah|"
                       r"wajib|harus|bayangkan|sebenarnya|fakta|stop|bahaya|jarang|kebanyakan|kunci|terbukti|nyangka|serius|asli|"
                       r"parah|gila|secret|never|why|how|mistake|actually|important|crazy)")


def bersih_kata(w: str) -> str:
    return w.strip().strip("\"'(),.?!:;…").lower()


def is_hook(w: str) -> bool:
    return bool(HOOK_AWAL.match(bersih_kata(w)))




# Pembuka yang butuh konteks: pronoun, filler, atau jawaban dari pertanyaan sebelumnya.
# Viewer baru nggak punya konteks itu → klip langsung lose ("kok nggak masuk").
KONTEKS_PEMBUKA = re.compile(r"^(ini|itu|oi|eh|ya|nah|oke|duh|situ|disini|gitu|begini|kayaknya|emang|terus|lalu|abis|habis|ntar|soalnya|yaa|yaaa|iya|iyaa|betul|ih|nah|aduh|wah|hai|hallo|hello)\b", re.I)


def snap_batas_kalimat(kal: list[Kalimat], mulai: float, selesai: float) -> tuple[float, float]:
    """Geser batas klip ke batas kalimat terdekat supaya tidak ada kalimat kepotong.

    Mulai -> awal kalimat yang memuat `mulai` (atau kalimat pertama sesudahnya).
    Selesai -> akhir kalimat yang memuat `selesai` (atau kalimat terakhir sebelumnya).
    """
    if not kal:
        return mulai, selesai
    a = mulai
    for k in kal:
        if k.mulai <= mulai <= k.selesai:
            a = k.mulai
            break
    else:
        for k in kal:
            if k.mulai > mulai:
                a = k.mulai
                break
        else:
            a = kal[-1].mulai
    b = selesai
    for k in kal:
        if k.mulai <= selesai <= k.selesai:
            b = k.selesai
            break
    else:
        for k in reversed(kal):
            if k.selesai < selesai:
                b = k.selesai
                break
        else:
            b = kal[0].selesai
    if b <= a:
        return mulai, selesai
    return a, b


def perbaiki_pembuka(kal_utuh: list[Kalimat], i: int, j: int, a: float, b: float) -> tuple[float, float, str]:
    """Kalau klip buka dengan kata konteks-dependent, geser start ke kalimat yang berdiri sendiri.

    Aturan (mengikuti openshorts "STANDS ALONE"): geser ke kalimat BERIKUTNYA dulu (isi yang
    masih nyambung), kalau tidak cukup durasi baru geser mundur ke kalimat sebelumnya.
    """
    try:
        if not (0 <= i < len(kal_utuh)):
            return a, b, ""
        s = kal_utuh[i]
        awal = (s.kata[0].teks if s.kata else ((s.teks.split() or [""])[0]))
        if not KONTEKS_PEMBUKA.match(bersih_kata(awal)):
            return a, b, ""
        # geser ke kalimat berikutnya sampai pembukanya berdiri sendiri (maks 3 langkah, maks +4 dtk)
        for langkah in range(1, 4):
            if i + langkah > j or i + langkah >= len(kal_utuh):
                break
            nxt = kal_utuh[i + langkah]
            if nxt.mulai - a > 4.0 or (b - nxt.mulai) < 10:
                break
            awal_nxt = (nxt.kata[0].teks if nxt.kata else ((nxt.teks.split() or [""])[0]))
            if KONTEKS_PEMBUKA.match(bersih_kata(awal_nxt)):
                continue  # masih butuh konteks → geser lagi
            return round(nxt.mulai, 2), b, f"start digeser ke kalimat berikutnya ('{nxt.teks[:26]}')"
        if i > 0:
            prev = kal_utuh[i - 1]
            if a - prev.mulai <= 3.0 and (b - prev.mulai) >= 10:
                return round(prev.mulai, 2), b, "start digeser mundur ke kalimat sebelumnya"
    except (IndexError, TypeError, ValueError):
        return a, b, ""
    return a, b, ""

# ── 4a-2. Mode momen GAMER ──────────────────────────────────────────────────
# Bedanya dari mode umum: bukan cuma rata-rata energi suara, tapi PUNCAK energi
# (teriakan/kaget), ditambah reaksi wajah dari file facecam, aksi gameplay, dan
# kamus kata/interjeksi khas gaming.
HOOK_GAME = re.compile(
    r"^(kill|killing|killed|death|die|died|dead|respawn|first\s?blood|ace|clutch|combo|"
    r"multi\s?kill|killstreak|headshot|frag|fragged|rage|rekt|rekted|slaughtered|"
    r"gg|wp|well\s?played|nice|no\s?way|insane|goated|clean|easy|clutched|"
    r"bunuh|mati|mampus|menang|kalah|menangin|round|ronde|skor|score|poin|"
    r"rank|mvp|boost|carry|carry\s?the|carry\s?team|throw|feeds|feeder|"
    r"gila|anjir|parah|mantap|sip|keren|babak|brutal|wtf|omg)", re.I)

INTERJEKSI = re.compile(r"\b(anjir|gila|parah|wtf|omg|wkwk+w|haha+|lol|nah|ah|sip|mantap|"
                        r"anjirrrr+|gilaaaa|parahhhh|no\s?way|insane|goated|gg)\b", re.I)

# kata yang menandai momen emosional (bukan cuma info)
EMOSI = re.compile(r"\b(gila|anjir|parah|wtf|omg|no\s?way|insane|goated|brutal|"
                   r"mantap|keren|mampus|nice|clutch|gg|kill|bunuh|mati)\b", re.I)

# ── Kamus gamer berbobot per kategori ──────────────────────────────────────
# EVENT (kejadian gameplay) bobot tertinggi; NOISE (filler) & META_NARASI
# (omongan soal bikin video) negatif. Semua pola memakai \b…\b + finditer,
# jadi kata di tengah kalimat ikut terdeteksi, bukan cuma di awal.
KAMUS_GAMER: dict[str, tuple[int, "re.Pattern"]] = {
    "event": (25, re.compile(
        r"\b(kill|killing|killed|ace|clutch|clutched|penta\s?kill|triple\s?kill|"
        r"multi\s?kill|team\s?wipe|first\s?blood|killstreak|headshot|1v[1-5]|"
        r"chicken\s?dinner|knock\s?down|revive|resurrect|menang|winrate|mvp|"
        r"round|ronde|otw|winning|won|bunuh|mati|mampus|respawn|frag|frags|"
        r"win|lose|kalah|booyah|savage|rampage|dominating|unstoppable|godlike)\b", re.I)),
    "reaksi": (14, re.compile(
        r"\b(gila|anjir|parah|wtf|no\s?way|insane|goated|brutal|gokil|astaga|"
        r"ampun|mantap|nyesek|serius|seriously|what\s?the|are\s?you\s?serious|"
        r"how\s?did\s?you|oh\s?my\s?god|omg|holy|jesus|anjay|anjing|bangsat|"
        r"brengsek|kampret|sial|sialan|woah|whoa|wow|gila\s?bener|gila\s?banget)\b", re.I)),
    "banter": (12, re.compile(
        r"\b(gblk|mabar|bocil|meta\s?ciki|jebakan|bait|camping|camper|ez|ezz|ezzz|"
        r"feed|feeder|feeding|throw|throwing|noob|nob|skill\s?issue|outplay|"
        r"outplayed|mikro|by\s?one|adu\s?mekanik|kill\s?sampah|imba|diff|nc|tebe|"
        r"retry|wkwk+|ngakak|lol|troll|trolling|cheese|cheesy|scripted|kidding)\b", re.I)),
    "strategi": (8, re.compile(
        r"\b(build|meta|counter|rotation|rotasi|item|skill|cd|cooldown|ult|ulti|"
        r"buff|nerf|farming|push|tower|base|objective|rotate|all\s?in|setup|"
        r"loadout|pick|ban|draft|lurk|flank|rush|turtling|combo|trade|positioning|"
        r"posisi|timing|angle|crosshair|sens|sensitivity|dpi|aim|aiming|recoil|"
        r"spread|scope)\b", re.I)),
    "noise": (-8, re.compile(
        r"\b(eh|ya|iya|oke|ok|jadi|terus|lalu|begini|gitu|nah|sih|dong|deh|kok|"
        r"aja|doang|cuma|hmm|uhm|um|uh)\b", re.I)),
    "meta_narasi": (-15, re.compile(
        r"\b(kita\s?akan|akan\s?buat|bikin\s?video|subscribe|like\s?dulu|intro|"
        r"konsep\s?video|next\s?video|nanti\s?di|sampai\s?jumpa|"
        r"jangan\s?lupa\s?subscribe|follow|komen|comment)\b", re.I)),
}



def motion_per_detik(path: Path, fps: float = 1.0, sisi: int = 32) -> np.ndarray:
    """Motion per detik (mean absolute difference antar frame) dari video.

    Dipakai untuk: reaksi wajah (facecam) dan aksi gameplay.
    Frame di-downscale ke sisi x sisi abu-abu supaya murah.
    fps rendah (1) biar cepat di VPS 2-core; deteksi gerakan besar tetap tercapai.
    """
    import time as _time

    cmd = [ffmpeg(), "-v", "error", "-i", str(path),
           "-vf", f"fps={fps},scale={sisi}:{sisi}:flags=fast_bilinear,format=gray",
           "-f", "rawvideo", "-pix_fmt", "gray", "-"]

    log("   Memulai deteksi gerakan video (bisa lama pada video panjang)…")
    t0 = _time.time()

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        chunks = []
        while True:
            chunk = proc.stdout.read(sisi * sisi)
            if not chunk:
                break
            chunks.append(chunk)
            now = _time.time()
            if now - t0 > 10:
                log(f"   …masih proses video ({int(now - t0)} detik)")
                t0 = now
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        log("   Deteksi gerakan melebihi batas waktu, menggunakan data yang sudah terkumpul.")
        raw = b"".join(chunks)
    else:
        raw = b"".join(chunks)

    n = len(raw) // (sisi * sisi)
    if n < 2:
        return np.zeros(1)
    arr = np.frombuffer(raw[: n * sisi * sisi], dtype=np.uint8).reshape(n, sisi, sisi).astype(np.float32)
    diff = np.abs(np.diff(arr, axis=0)).mean(axis=(1, 2))  # motion tiap frame
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


def skor_momen_gamer(kal: list[Kalimat], energi: np.ndarray, lonjak: np.ndarray,
                     reaksi: np.ndarray, aksi: np.ndarray,
                     durasi: float, arahan: str = "", durasi_bebas: bool = False,
                topik_trending: list[str] | None = None) -> list[dict]:
    """Skor tiap rentang kalimat untuk mode gamer.

    Tiga lapis penilaian:
    1. KATA — kamus berkategori (event/reaksi/banter/strategi) dikurangi noise
       dan meta-narasi ("kita akan membuat video").
    2. SINYAL FISIK — teriakan, reaksi wajah, aksi gameplay (bukan dari teks).
    3. ALIGNMENT BONUS — kejadian gameplay + sinyal fisik di waktu yang sama.
       Inilah yang membedakan highlight asli dari narasi yang kebetulan keras.
    Semua array sinyal ber-unit per detik.
    """
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
            if durasi_bebas:
                # Panjang bebas: hanya batas bawah (terlalu pendek tak masuk akal)
                # dan batas atas (jangan jadi cuplikan 10 menit).
                if pj > 180.0:
                    break
                if pj < 12.0:
                    continue
            else:
                if pj > durasi * 1.2:
                    break
                if pj < durasi * 0.6:
                    continue
            isi = kal[i:j + 1]
            teks = " ".join(s.teks for s in isi)
            low = teks.lower()
            semua_kata = re.findall(r"\w+", low)
            padat = len(semua_kata) / max(pj, 1)

            # Skor per kategori: jumlah kecocokan UNIK x bobot kategori
            kategori: dict[str, set[str]] = {}
            for nama, (_bobot, pola) in KAMUS_GAMER.items():
                kategori[nama] = {m.group(0).lower() for m in pola.finditer(low)}

            positif = sum(len(kategori[n]) * KAMUS_GAMER[n][0]
                          for n in ("event", "reaksi", "banter", "strategi"))
            # Penalti dibatasi supaya tidak menenggelamkan sinyal positif
            penalti_noise = min(len(kategori["noise"]) * 8, 30)
            penalti_meta = min(len(kategori["meta_narasi"]) * 15, 60)
            skor_kata = positif - penalti_noise - penalti_meta

            e_peak = ambil(energi, a, b, "max")
            e_lonjak = ambil(lonjak, a, b, "max")
            r_reaksi = ambil(reaksi, a, b, "max")
            r_aksi = ambil(aksi, a, b, "max")
            pembuka = bool(HOOK_GAME.match(bersih_kata(k.kata[0].teks))) if k.kata else False

            # ALIGNMENT BONUS: kejadian gameplay + sinyal fisik di waktu yang sama
            alignment = 0
            if kategori["event"]:
                if e_lonjak > 0.30 or r_reaksi > 0.35:
                    alignment += 20
                if r_aksi > 0.50:
                    alignment += 10

            skor = (skor_kata
                    + e_peak * 16          # teriakan / kaget
                    + e_lonjak * 20        # lonjakan suara mendadak
                    + r_reaksi * 22        # facecam beriak -> ekspresi kuat
                    + r_aksi * 10          # gameplay sedang rame
                    + alignment
                    + (12 if pembuka else 0)
                    + (0.0 if durasi_bebas else -abs(pj - durasi) / durasi * 10))
            if kata_arahan and kata_arahan & set(semua_kata):
                skor += 20
            # Bonus topik trending (riset internet)
            if topik_trending:
                for t in topik_trending:
                    if t.lower() in low:
                        skor += 15
                        break

            alasan = []
            if kategori["event"]:
                alasan.append("event: " + ", ".join(sorted(kategori["event"])[:3]))
            if alignment:
                alasan.append("event+sinyal sejalan")
            if e_lonjak > 0.35:
                alasan.append("teriakan")
            if r_reaksi > 0.4:
                alasan.append("reaksi wajah")
            if r_aksi > 0.5:
                alasan.append("aksi game")
            if kategori["banter"]:
                alasan.append("banter")
            if pembuka:
                alasan.append("pembuka kuat")
            if padat >= 2.6:
                alasan.append("bicara padat")
            if kategori["meta_narasi"]:
                alasan.append("ada narasi meta")
            if kata_arahan and kata_arahan & set(semua_kata):
                alasan.append("sesuai arahan")

            hasil.append({
                "mulai": round(a, 2), "selesai": round(b, 2),
                "teks": k.teks[:70], "skor": skor,
                "alasan": " · ".join(alasan) or "momen naturalistis",
                "sinyal": {
                    "energi": round(e_peak, 3), "lonjakan": round(e_lonjak, 3),
                    "reaksi": round(r_reaksi, 3), "aksi": round(r_aksi, 3),
                    "alignment": alignment,
                    "kategori": {n: sorted(v)[:6] for n, v in kategori.items() if v},
                },
            })
    return hasil



def kalimat_utuh(kal: list[Kalimat]) -> list[Kalimat]:
    """Pecah ulang per KALIMAT dari kata-kata: titik/tanya/seru, atau jeda > 1,2 dtk = batas kalimat."""
    kata = [k for s in kal for k in s.kata]
    if not kata:
        return kal
    hasil, mulai = [], 0
    for i, k in enumerate(kata):
        akhir = k.teks.rstrip("\"')").endswith((".", "?", "!", "…"))
        jeda = i + 1 < len(kata) and kata[i + 1].mulai - k.selesai > 1.2
        if akhir or jeda or i == len(kata) - 1:
            isi = kata[mulai:i + 1]
            hasil.append(Kalimat(isi[0].mulai, isi[-1].selesai, " ".join(x.teks for x in isi), isi))
            mulai = i + 1
    return hasil


def skor_google_trends(topik_list: list[str]) -> dict[str, float]:
    """Cek topik di Google Trends (Indonesia, 7 hari terakhir).

    Return dict {topik: skor 0-100}. Jika pytrends tidak ada atau gagal,
    return {} (caller tetap pakai skor lokal).
    """
    if not _HAS_PYTRENDS or not topik_list:
        return {}
    try:
        pytrends = TrendReq(hl='id-ID', tz=420, timeout=20)
        hasil: dict[str, float] = {}
        for topik in topik_list[:5]:  # batasi 5 topik biar cepat
            try:
                pytrends.build_payload([topik], cat=0, timeframe='now 7-d', geo='ID')
                data = pytrends.interest_over_time()
                if not data.empty and topik in data.columns:
                    nilai = data[topik].mean()
                    hasil[topik] = float(nilai)  # 0-100
            except Exception:
                continue
        return hasil
    except Exception:
        return {}


def ekstrak_topik(kal: list[Kalimat], arahan: str = "") -> list[str]:
    """Ambil kata kunci potensial dari kalimat untuk dicek ke Google Trends."""
    from collections import Counter
    kata_counter: Counter[str] = Counter()
    for k in kal:
        for w in re.findall(r"\w+", k.teks.lower()):
            if len(w) > 4 and w not in KATA_STOP:
                kata_counter[w] += 1
    topik = [w for w, _ in kata_counter.most_common(8)]
    if arahan:
        topik.extend(w for w in re.findall(r"\w+", arahan.lower()) if len(w) > 3)
    return topik[:10]


def ambil_trending_topik() -> list[str]:
    """Ambil topik lagi viral di Indonesia dari Google Trends (trending searches now).

    Digunakan sebagai konsep tambahan buat AI supaya pemilihan momen
    tidak cuma lihat transkrip, tapi juga tahu apa yang lagi viral di internet.
    Return list topik (maks 10). Kalau semua sumber gagal, return []
    (AI tetap jalan dari transkrip Whisper + sinyal fisik).
    """
    # Sumber 1: Google Trends trending searches
    if _HAS_PYTRENDS:
        try:
            pytrends = TrendReq(hl='id-ID', tz=420, timeout=20)
            trending = pytrends.trending_searches(pn='indonesia')
            if trending is not None and len(trending) > 0:
                topik = [str(row[0]) for row in trending.values[:10]]
                if topik:
                    return topik
        except Exception:
            pass
    # Sumber 2: DuckDuckGo HTML search (fallback kalau Google Trends diblokir)
    try:
        import requests
        from bs4 import BeautifulSoup
        r = requests.get(
            'https://duckduckgo.com/html/?q=topik+viral+Indonesia+hari+ini',
            timeout=12,
            headers={'User-Agent': 'Mozilla/5.0'},
        )
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            results = soup.select('.result__a')[:10]
            if results:
                return [res.get_text(strip=True) for res in results]
    except Exception:
        pass
    return []


KATA_STOP = {
    "yang", "dan", "atau", "dari", "dengan", "untuk", "pada", "di", "ke", "di",
    "ini", "itu", "saya", "kamu", "dia", "mereka", "ada", "tidak", "bisa",
    "sudah", "belum", "masih", "juga", "lah", "kah", "tah", "nah", "yaitu",
    "seperti", "pada", "oleh", "jika", "maka", "karena", "supaya", "agar",
    "namun", "tetapi", "tapi", "jadi", "kalau", "kalo", "saat", "waktu",
    "waktu", "hari", "bulan", "tahun", "jam", "detik", "menit",
}


def ringkas_sinyal_untuk_ai(sinyal: dict | None, durasi_video: float,
                            window: int = 30, top: int = 12) -> str:
    """Ringkas sinyal fisik per window untuk prompt AI.

    LLM hanya melihat teks, jadi teriakan/reaksi wajah/aksi gameplay tidak
    pernah diketahui kalau tidak dikirim. Fungsi ini mengambil 12 window
    dengan sinyal terkuat supaya AI bisa memilih momen di sekitar puncaknya,
    bukan hanya dari kata-kata.
    """
    if not sinyal:
        return ""
    lonjak = sinyal.get("lonjak")
    if lonjak is None or len(lonjak) == 0:
        return ""
    reaksi = sinyal.get("reaksi")
    aksi = sinyal.get("aksi")

    def mx(sig, a, b):
        if sig is None or len(sig) == 0:
            return 0.0
        i0, i1 = min(a, len(sig) - 1), min(b, len(sig))
        if i1 <= i0:
            return 0.0
        return float(sig[i0:i1].max())

    rows = []
    n = int(durasi_video)
    for a in range(0, max(n, 1), window):
        b = min(a + window, n)
        l, r, ak = mx(lonjak, a, b), mx(reaksi, a, b), mx(aksi, a, b)
        rows.append((l + r * 1.2 + ak * 0.6, a, b, l, r, ak))
    rows.sort(reverse=True)
    # Buang window tanpa sinyal: deretan nol di prompt hanya menambah noise
    # dan membuat AI menganggap bagian akhir video penting padahal datar.
    rows = [row for row in rows if row[0] > 0.05]
    terpilih = sorted(rows[:top], key=lambda x: x[1])
    return "\n".join(f"  {a}-{b}s: lonjak={l:.2f} reaksi={r:.2f} aksi={ak:.2f}"
                     for _s, a, b, l, r, ak in terpilih)


def ai_pilih_momen_utama(kal: list[Kalimat], durasi: float, jumlah: int,
                         arahan: str = "", penyedia: str = "",
                         cache: Path | None = None, mode: str = "umum",
                         sinyal: dict | None = None,
                         durasi_bebas: bool = False,
                         topik_trending: list[str] | None = None) -> list[Klip] | None:
    """AI utama pilih momen terbaik dari semua teks Whisper.

    Kirim semua kalimat dengan timestamp ke AI. AI memilih jumlah momen
    yang paling menarik, tidak tumpang tindih, dan bisa berdiri sendiri.
    mode="gamer" menambahkan prompt khusus gaming + ringkasan sinyal fisik
    (teriakan/reaksi wajah/aksi gameplay) yang tidak terlihat dari teks.
    Return None jika AI gagal (caller pakai fallback lokal).
    """
    if not kal or not penyedia:
        return None

    # Siapkan teks dengan timestamp untuk AI
    segment = []
    for k in kal:
        segment.append(f"[{k.mulai:.0f}s - {k.selesai:.0f}s] {k.teks}")

    # Kirim seluruh transkrip (bukan cuma 300 segmen) — model free/berbayar
    # modern punya context >= 128K, sedangkan 300 segmen cuma menutup ~60%
    # video 31 menit sehingga momen bagus di paruh akhir tidak pernah dilihat AI.
    # Batas tetap ada supaya video 2 jam tidak meledakkan prompt.
    teks_gabungan = "\n".join(segment[:1200])

    arahan_str = f"\nArahan pengguna: {arahan}" if arahan else ""

    # Topik lagi viral di Indonesia (riset internet via Google Trends)
    trending_str = ""
    if topik_trending:
        trending_str = (
            f"\nTOPIK LAGI VIRAL DI INDONESIA (Google Trends, 7 hari terakhir):\n"
            + "\n".join(f"  - {t}" for t in topik_trending[:10])
            + "\nPrioritaskan momen yang berkaitan dengan topik-trending ini."
        )

    if durasi_bebas:
        batas_durasi = (
            f"Pilih {jumlah} momen terbaik untuk klip pendek. TIDAK ada target durasi tetap —\n"
            "panjang tiap klip bebas mengikuti isi yang sedang dibahas (bisa 15 detik, bisa 90 detik).\n"
            "Mulai di awal/topik yang dibahas, selesai di kalimat yang mengakhiri pembahasan itu.\n"
            "Jangan memotong di tengah kalimat atau tengah gracefully; pilih batas yang natural.\n"
            "Setiap klip boleh punya durasi yang BERBEDA-BEDA."
        )
    else:
        batas_durasi = f"Pilih {jumlah} momen terbaik untuk klip pendek, masing-masing sekitar {durasi} detik."

    sinyal_txt = ringkas_sinyal_untuk_ai(sinyal, kal[-1].selesai if kal else 0)

    if mode == "gamer":
        prompt = f"""Anda adalah editor video GAMING untuk TikTok/Reels/Shorts.

Berikut transkrip lengkap video gameplay dengan timestamp (detik):
{teks_gabungan}

SINYAL FISIK (dari audio & video, BUKAN teks — bukti gaming yang tidak terlihat dari kata-kata):
- lonjak: lonjakan volume suara vs baseline (teriakan/kaget)
- reaksi: intensitas gerakan wajah di facecam (ekspresi kuat)
- aksi: intensitas gerakan di gameplay (sedang rame)
WAKTU DENGAN SINYAL TERKUAT:
{sinyal_txt}

{batas_durasi}

Kriteria wajib:
1. ADALAH MOMEN GAMING: ada kejadian gameplay (kill, clutch, ace, win, round, mati, menang)
   ATAU reaksi emosi/kaget/banter yang genuine menarik.
2. SKOR RENDAH untuk transkrip yang berisi narasi/meta tentang membuat video
   ("kita akan membuat video", "subscribe", "intro", "konsep video", "next video").
3. ALIGNMENT: prioritaskan momen di mana ADA KEJADIAN (kata event gameplay)
   DAN sinyal fisik kuat (lonjak>0.3 ATAU reaksi>0.35 ATAU aksi>0.5) di waktu yang sama.
4. 2-DETIK TEST: 2 detik pertama harus membuat penonton baru ingin terus nonton.
5. STANDS ALONE: hindari awalan "ini", "itu", "ya", "nah".
6. Tidak tumpang tindih waktu.
7. Bawa judul singkat dan alasan singkat ({instruksi_bahasa()}).{arahan_str}{trending_str}

Output HANYA JSON valid, tanpa prose, tanpa markdown fence:
[
  {{"mulai": 120.5, "selesai": 180.5, "judul": "...", "alasan": "..."}},
  ...
]
"""
        hasil = ai_json(penyedia, prompt, cache)
        if not hasil:
            return None
        data = hasil if isinstance(hasil, list) else hasil.get("momen", [])
        if not isinstance(data, list) or not data:
            return None
        klips: list[Klip] = []
        for item in data[:jumlah]:
            try:
                klips.append(Klip(
                    round(float(item["mulai"]), 2),
                    round(float(item["selesai"]), 2),
                    str(item.get("judul", f"Klip {item['mulai']:.0f}s")).strip(),
                    80,
                    str(item.get("alasan", "pilihan AI"))
                ))
            except (KeyError, TypeError, ValueError):
                continue
        return klips or None

    prompt = f"""Anda adalah editor video pendek (TikTok/Reels/Shorts) senior.

Berikut adalah transkrip lengkap video dengan timestamp (detik):
{teks_gabungan}

SINYAL FISIK (dari audio & video, BUKAN teks — bukti momen menarik yang tidak selalu terlihat dari kata-kata):
- lonjak: lonjakan volume suara vs baseline (teriakan/kaget)
- reaksi: intensitas gerakan wajah di facecam (ekspresi kuat)
- aksi: intensitas gerakan di layar (sedang rame)
WAKTU DENGAN SINYAL TERKUAT:
{sinyal_txt}

Pilih {jumlah} momen terbaik untuk dibuat klip pendek, masing-masing sekitar {durasi} detik.

Kriteria wajib:
1. 2-DETIK TEST: 2 detik pertama harus membuat penonton baru (tanpa konteks) ingin terus nonton.
2. STANDS ALONE: klip harus bisa dipahami tanpa konteks sebelumnya. Hindari awalan dengan "ini", "itu", "ya", "nah".
3. Tidak tumpang tindih waktu satu sama lain.
4. Prioritaskan momen yang memiliki sinyal fisik kuat (lonjakan suara, reaksi wajah, atau aksi layar), meski teksnya sepi.
5. SKOR RENDAH untuk transkrip yang berisi narasi/meta tentang membuat video ("kita akan membuat video", "subscribe", "intro"), kecuali jika didukung sinyal fisik kuat.
6. Bawa judul singkat dan alasan singkat (Bahasa Indonesia).{arahan_str}{trending_str}

Output HANYA JSON valid, tanpa prose, tanpa markdown fence:
[
  {{"mulai": 120.5, "selesai": 180.5, "judul": "...", "alasan": "..."}},
  ...
]
"""

    hasil = ai_json(penyedia, prompt, cache)
    if not hasil:
        return None

    data = hasil if isinstance(hasil, list) else hasil.get("momen", [])
    if not isinstance(data, list) or not data:
        return None

    klips: list[Klip] = []
    for item in data[:jumlah]:
        try:
            klips.append(Klip(
                round(float(item["mulai"]), 2),
                round(float(item["selesai"]), 2),
                str(item.get("judul", f"Klip {item['mulai']:.0f}s")).strip(),
                80,  # skor default AI utama
                str(item.get("alasan", "pilihan AI"))
            ))
        except (KeyError, TypeError, ValueError):
            continue

    if not klips:
        return None

    # Urutkan berdasarkan waktu mulai
    klips.sort(key=lambda k: k.mulai)
    log(f"   AI utama memilih {len(klips)} momen dari teks Whisper.")
    return klips


def pilih_momen(kal: list[Kalimat], energi: np.ndarray, heatmap: list[dict],
                durasi: float, jumlah: int, panjang_video: float, arahan: str = "",
                mode: str = "umum", sinyal: dict | None = None,
                durasi_bebas: bool = False,
                topik_trending: list[str] | None = None) -> list[Klip]:
    """Momen = rangkaian kalimat utuh, diberi skor, judul, dan alasan (sama dengan aplikasi Klip HP).

    mode "gamer" → pakai preset momen gamer: teriakan (lonjakan energi), reaksi facecam,
    aksi gameplay, dan kamus kata gaming. Sinyal ekstra dikirim lewat `sinyal`.

    durasi_bebas=True → TIDAK ada target panjang. Panjang klip mengikuti isi yang
    dibicarakan: dari pembuka hook sampai kalimat selesai, dibatasi hanya oleh
    batas bawah (terlalu pendek tidak masuk akal) dan batas atas (jangan jadi
    cuplikan 10 menit). Durasi tiap klip boleh berbeda-beda.
    """
    if mode == "gamer":
        semua = skor_momen_gamer(kalimat_utuh(kal), energi,
                                 (sinyal or {}).get("lonjak", np.zeros(1)),
                                 (sinyal or {}).get("reaksi", np.zeros(1)),
                                 (sinyal or {}).get("aksi", np.zeros(1)),
                                 durasi, arahan, durasi_bebas=durasi_bebas,
                                 topik_trending=topik_trending)
        if not semua:
            return []
        semua.sort(key=lambda c: c["skor"], reverse=True)
        terpilih: list[Klip] = []
        for c in semua:
            if all(c["selesai"] <= t.mulai or c["mulai"] >= t.selesai for t in terpilih):
                terpilih.append(Klip(c["mulai"], c["selesai"], c["teks"], c["skor"], c["alasan"]))
            if len(terpilih) == jumlah:
                break
        if terpilih:
            top, bawah = terpilih[0].skor, terpilih[-1].skor
            for c in terpilih:
                c.skor = int(min(max(60 + 39 * (c.skor - bawah) / max(top - bawah, 1), 1), 99))
        return sorted(terpilih, key=lambda c: c.mulai)

    kata_arahan = {w for w in re.findall(r"\w+", arahan.lower()) if len(w) > 3}
    if not kal:
        # tanpa ucapan: pakai energi audio saja
        kal = [Kalimat(float(t), float(t + 1), "", []) for t in range(int(panjang_video))]
    kal = kalimat_utuh(kal)
    # Google Trends: cek topik yang lagi viral di Indonesia (fallback ke {} jika gagal)
    topik_google = ekstrak_topik(kal, arahan)
    trends = skor_google_trends(topik_google)
    kandidat: list[Klip] = []
    for i, k in enumerate(kal):
        for j in range(i, len(kal)):
            a, b = k.mulai, kal[j].selesai
            pj = b - a
            if durasi_bebas:
                if pj > 180.0:
                    break
                if pj < 12.0:
                    continue
            else:
                if pj > durasi * 1.2:
                    break
                if pj < durasi * 0.6:
                    continue
            isi = kal[i:j + 1]
            kata = [x for s in isi for x in s.kata]
            teks = " ".join(s.teks for s in isi)
            semua_kata = re.findall(r"\w+", teks.lower())
            hooks = list(dict.fromkeys(bersih_kata(x.teks) for x in kata if is_hook(x.teks)))
            padat = len(semua_kata) / max(pj, 1)  # kata per detik
            tanya = sum(1 for s in isi if s.teks.rstrip().endswith("?"))
            pembuka = any(is_hook(x.teks) for x in k.kata[:6]) or ("?" in k.teks)
            e = float(energi[int(a):max(int(b), int(a) + 1)].mean()) if len(energi) > 1 else 0
            hm = nilai_heatmap(heatmap, a, b)
            skor = (padat * 14 + len(hooks) * 7 + tanya * 5 + (14 if pembuka else 0)
                    + (0.0 if durasi_bebas else -abs(pj - durasi) / durasi * 10) + e * 10 + hm * 30)
            if kata_arahan and kata_arahan & set(semua_kata):
                skor += 20
            # Bonus topik trending (riset internet, Google Trends)
            if topik_trending:
                low = teks.lower()
                for t in topik_trending:
                    if t.lower() in low:
                        skor += 15
                        break
            # Bonus Google Trends: kalau klip mengandung topik yang lagi viral
            bonus_trends = max((trends.get(w, 0) for w in semua_kata if w in trends), default=0)
            if bonus_trends > 40:
                skor += int(bonus_trends / 10)  # max +10 skor
            alasan = [x for x in ("pembuka kuat" if pembuka else "", "ada pertanyaan" if tanya else "",
                                  f"{len(hooks)} kata pemikat" if hooks else "", "bicara padat" if padat >= 2.6 else "",
                                  "sering diputar ulang" if hm > 0.5 else "", "sesuai arahan" if kata_arahan & set(semua_kata) else "") if x]
            judul = (k.teks[:70] or f"Klip {a:.0f}s").strip()
            # STANDS ALONE: pembuka konteks-dependent → geser start
            a2, b2, _ket = perbaiki_pembuka(kal, i, j, a, b)
            kandidat.append(Klip(round(a2, 2), round(b2, 2), judul, skor, " · ".join(alasan) or "kalimat utuh"))
    if not kandidat and kal:
        b = min(kal[-1].selesai, kal[0].mulai + durasi)
        kandidat = [Klip(round(kal[0].mulai, 2), round(b, 2), (kal[0].teks[:70] or "Klip").strip(), 50, "kalimat utuh")]
    kandidat.sort(key=lambda c: c.skor, reverse=True)
    terpilih: list[Klip] = []
    for c in kandidat:
        if all(c.selesai <= t.mulai or c.mulai >= t.selesai for t in terpilih):
            terpilih.append(c)
        if len(terpilih) == jumlah:
            break
    # Jika masih kurang, tambahkan yang sedikit tumpang-tindih (overlap < 30%)
    if len(terpilih) < jumlah:
        for c in kandidat:
            if any(c in t for t in terpilih):
                continue
            overlap = max(0, min(c.selesai, t.selesai) - max(c.mulai, t.mulai))
            dur_c = c.selesai - c.mulai
            if dur_c > 0 and overlap / dur_c < 0.30:
                terpilih.append(c)
            if len(terpilih) == jumlah:
                break
    # Jika masih kurang, ambil yang tersisa berdasarkan skor tertinggi
    if len(terpilih) < jumlah:
        for c in kandidat:
            if any(c is t for t in terpilih):
                continue
            terpilih.append(c)
            if len(terpilih) == jumlah:
                break
    if terpilih:  # skor tampilan 0–99 relatif terhadap momen terbaik
        top, bawah = terpilih[0].skor, terpilih[-1].skor
        for c in terpilih:
            c.skor = int(min(max(60 + 39 * (c.skor - bawah) / max(top - bawah, 1), 1), 99))
    return sorted(terpilih, key=lambda c: c.mulai)


# ── 4b. Opsi B: prompt untuk Claude ─────────────────────────────────────────
def tulis_prompt(kal: list[Kalimat], durasi: int, jumlah: int, out: Path, arahan: str = "") -> None:
    baris = "\n".join(f"[{k.mulai:.1f}-{k.selesai:.1f}] {k.teks}" for k in kal)
    out.write_text(f"""Kamu editor video pendek. Di bawah ini transkrip video dengan waktu (detik).
Pilih {jumlah} momen paling menarik untuk TikTok/Reels, masing-masing sekitar {durasi} detik.{(chr(10) + "Fokus pengguna: " + arahan) if arahan else ""}
Syarat: mulai di awal kalimat, selesai di akhir kalimat, ada hook di 3 detik pertama, tidak saling tumpang tindih.
Judul, caption, dan ringkasan HANYA boleh memakai fakta & angka yang ada di transkrip — jangan mengarang angka, waktu, atau klaim.
"hook" = detik kalimat paling memancing perhatian di dalam klip. Bahasa judul & caption mengikuti bahasa transkrip.
"kata_kunci" = 3-6 KATA TUNGGAL (bukan frasa) persis seperti di transkrip klip itu yang paling penting (angka, nama, kata emosi), untuk diberi warna di subtitle.
Balas HANYA JSON seperti ini, tanpa teks lain:
{{"ringkasan": "2 kalimat ringkasan isi video", "hashtag": ["#tagsatu", "#tagdua", "#tagtiga"],
 "klip": [{{"mulai": 12.3, "selesai": 41.0, "hook": 14.0, "judul": "judul singkat", "alasan": "kenapa menarik", "skor": 0.9, "caption": "caption siap posting + 3 hashtag", "kata_kunci": ["kata", "penting"]}}]}}

TRANSKRIP:
{baris}
""", encoding="utf-8")


# ── 4c. AI milik pengguna (Gemini / Claude / OpenAI-compatible seperti Ollama) ─
def baca_env() -> dict:
    """Baca pengaturan Studio lalu .env di folder skrip, timpa dengan variabel lingkungan.

    Kunci yang diisi lewat web UI tersimpan di ~/Isanovski Studio/pengaturan.env,
    sedangkan yang diisi lewat CLI tersimpan di klip/.env. Keduanya dibaca
    supaya tidak perlu mengisi dua kali.
    """
    import os
    env = {}
    data = Path(os.environ.get("STUDIO_DATA") or (Path.home() / "Isanovski Studio"))
    for f in (data / "pengaturan.env", Path(__file__).with_name(".env")):
        if not f.exists():
            continue
        for baris in f.read_text(encoding="utf-8").splitlines():
            if "=" in baris and not baris.strip().startswith("#"):
                k, v = baris.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    env.update({k: v for k, v in os.environ.items() if k in env or k.endswith(("_API_KEY", "_MODEL", "_BASE_URL"))})
    return env


def tanya_ai(penyedia: str, prompt: str) -> str:
    env = baca_env()
    if penyedia == "gemini":
        from google import genai
        kunci = env.get("GEMINI_API_KEY") or sys.exit("Isi GEMINI_API_KEY di .env (gratis: aistudio.google.com/apikey)")
        from google.genai import errors as gerr
        # model utama dulu, lalu cadangan bertier gratis (aistudio.google.com/docs/pricing, 13 Nov 2026)
        urutan = [env.get("GEMINI_MODEL", "gemini-3.8-flash"), "gemini-3.8-flash", "gemini-3.6-flash",
                  "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]
        urutan = list(dict.fromkeys(urutan))
        pesan = ""
        # simpan client di variabel: kalau tidak, client ditutup sebelum permintaan dikirim
        from google.genai import types as gtypes
        # batas waktu 90 dtk per percobaan (milidetik) supaya tidak menggantung saat server Gemini penuh
        with genai.Client(api_key=kunci, http_options=gtypes.HttpOptions(timeout=90_000)) as klien:
            for model in urutan:
                for coba in range(2):
                    try:
                        r = klien.models.generate_content(model=model, contents=prompt)
                        if model != urutan[0]:
                            log(f"Memakai model cadangan {model}.")
                        return r.text or ""
                    except gerr.APIError as e:
                        pesan = f"{model}: {e.code} {getattr(e, 'message', '') or e}"
                        if e.code in (400, 401, 403):
                            sys.exit(f"Kunci Gemini ditolak ({e.code}). Cek kuncinya di Pengaturan AI.")
                        log(f"Gemini {model} sibuk/limit ({e.code}), mencoba lagi…")
                        time.sleep(3 * (coba + 1))
                    except Exception as e:  # noqa: BLE001 — batas waktu / jaringan
                        pesan = f"{model}: {type(e).__name__}"
                        log(f"Gemini {model} tidak menjawab ({type(e).__name__}), mencoba model lain…")
                        break
        sys.exit(f"Semua model Gemini sedang sibuk atau kuota habis. Coba lagi nanti, atau pakai AI Lokal.\n{pesan}")
    if penyedia in ("claude-code", "codex", "opencode"):
        return tanya_langganan(penyedia, prompt)
    if penyedia == "openai":
        import urllib.request
        url = env.get("OPENAI_BASE_URL", "http://localhost:11434/v1").rstrip("/") + "/chat/completions"
        muatan = {"model": env.get("OPENAI_MODEL", "gemma3:4b"),
                  "messages": [{"role": "user", "content": prompt}]}
        # Thinking mode: DeepSeek reasoning-mode membakar seluruh max_tokens untuk
        # chain-of-thought sehingga content jadi kosong. Matikan lewat
        # OPENAI_THINKING=disabled (resmi: {"thinking":{"type":"disabled"}}).
        ift = (env.get("OPENAI_THINKING") or "").strip().lower()
        if ift in ("disabled", "enabled"):
            muatan["thinking"] = {"type": ift}
        # Parameter tambahan opsional (JSON) untuk provider OpenAI-compatible lain
        extra = (env.get("OPENAI_EXTRA") or "").strip()
        if extra:
            try:
                muatan.update(json.loads(extra))
            except json.JSONDecodeError:
                log("   OPENAI_EXTRA bukan JSON valid → diabaikan.")
        data = json.dumps(muatan).encode()
        req = urllib.request.Request(url, data=data, headers={
            "Content-Type": "application/json", "Authorization": f"Bearer {env.get('OPENAI_API_KEY', 'ollama')}"})
        with urllib.request.urlopen(req, timeout=600) as resp:
            return json.loads(resp.read())["choices"][0]["message"]["content"]
    sys.exit(f"Penyedia AI tidak dikenal: {penyedia} (pilih lokal, gemini, openai, claude-code, codex, opencode)")


def cari_cli(nama: str) -> str | None:
    import os
    import shutil
    studio_cli = Path.home() / ".studio-isanovski" / "cli"
    for c in (shutil.which(nama), str(studio_cli / "bin" / nama), str(studio_cli / f"{nama}.cmd"),
              str(Path.home() / ".local/bin" / nama), f"/opt/homebrew/bin/{nama}",
              f"/usr/local/bin/{nama}", str(Path.home() / ".npm-global/bin" / nama)):
        if c and Path(c).exists():
            return c
    if os.name == "nt":
        return shutil.which(nama + ".cmd") or shutil.which(nama + ".exe")
    return None


def tanya_langganan(penyedia: str, prompt: str) -> str:
    """Pakai langganan pengguna lewat CLI resmi yang sudah login di laptopnya (tanpa kunci API).

    claude-code: Claude Code (Claude Pro/Max)  → `claude -p` tanpa alat, tanpa menyimpan sesi
    codex:       Codex CLI (ChatGPT Plus/Pro)  → `codex exec -` sandbox read-only bawaan
    opencode:    OpenCode (model/langganan apa pun yang sudah login di OpenCode) → `opencode run --agent plan`
    """
    import os
    import tempfile
    nama = {"claude-code": "claude", "codex": "codex", "opencode": "opencode"}[penyedia]
    label = {"claude": "Claude Code", "codex": "Codex", "opencode": "OpenCode"}[nama]
    cli = cari_cli(nama)
    if not cli:
        sys.exit(f"CLI '{nama}' belum terpasang. Pasang lalu login sekali di Terminal "
                 f"({ {'claude': 'claude', 'codex': 'codex login', 'opencode': 'opencode auth login'}[nama] }), "
                 "kemudian coba lagi.")
    env = os.environ.copy()
    # kunci API di lingkungan akan membuat CLI menagih API, bukan langganan → buang
    for kunci in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "OPENAI_API_KEY", "CODEX_API_KEY"):
        env.pop(kunci, None)
    if nama == "opencode" and env.get("GEMINI_API_KEY") and not env.get("GOOGLE_GENERATIVE_AI_API_KEY"):
        # OpenCode membaca kunci Google dari nama variabel ini; pakai kunci Gemini yang sudah disimpan pengguna
        env["GOOGLE_GENERATIVE_AI_API_KEY"] = env["GEMINI_API_KEY"]
    with tempfile.TemporaryDirectory() as tmp:
        if nama == "claude":
            cmd = [cli, "-p", "--tools", "", "--output-format", "text", "--no-session-persistence"]
            if os.environ.get("CLAUDE_CODE_MODEL"):
                cmd += ["--model", os.environ["CLAUDE_CODE_MODEL"]]
        elif nama == "codex":
            cmd = [cli, "exec", "--skip-git-repo-check", "-o", str(Path(tmp) / "jawab.txt")]
            if os.environ.get("CODEX_MODEL"):
                cmd += ["--model", os.environ["CODEX_MODEL"]]
            cmd.append("-")
        else:
            # agent "plan" = hanya membaca/menjawab, tidak mengubah berkas
            cmd = [cli, "run", "--agent", "plan"]
            if os.environ.get("OPENCODE_MODEL"):
                cmd += ["--model", os.environ["OPENCODE_MODEL"]]
        log(f"Meminta {label} (langganan) memilih/menulis…")
        try:
            r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8",
                               cwd=tmp, env=env, timeout=600)
        except subprocess.TimeoutExpired:
            sys.exit(f"{nama} tidak menjawab dalam 10 menit.")
        if r.returncode != 0:
            alasan = re.sub(r"\x1b\[[0-9;]*m", "", (r.stderr or r.stdout)).strip()[-600:]
            sys.exit(f"{nama} gagal (kode {r.returncode}). Pastikan sudah login dan kuota langganan masih ada.\n{alasan}")
        f = Path(tmp) / "jawab.txt"
        return f.read_text(encoding="utf-8") if f.exists() else r.stdout


def ambil_json(teks: str):
    m = re.search(r"\[.*\]|\{.*\}", teks, re.S)
    if not m:
        sys.exit("Balasan AI tidak berisi JSON:\n" + teks[:500])
    return json.loads(m.group(0))


# ── 4d. AI produksi multi-tahap ─────────────────────────────────────────────
# Tahap: transkrip → skor → pilih → hook → layout → qc
# Semua opsional: kalau AI gagal/tidak ada kunci, pipeline lanjut pakai heuristik lokal.
# Provider "openrouter" memakai rantai model FREE (OpenRouter free tier), fallback otomatis
# saat 429 (rate limit free) / 503 (upstream sibuk).
TAHAP_AI = ("transkrip", "skor", "hook", "layout", "qc")

MODEL_OR_FREE = (
    "nvidia/nemotron-3-ultra-550b-a55b:free",     # reasoning terbaik
    "recursive/flint-v1.0:free",                  # cepat +-ranked bagus
    "cohere/north-mini-code:free",                # paling cepat
    "nvidia/nemotron-3.5-lightning:free",         # cadangan
    "dots-studio/dots-3-note-preview:free",
    "particle-ai/particle-1:free",
    "liquid/lfm-3-1.7b:free",
    "baidu/ernie-5.5-flash-preview:free",
)


def ai_tahap_aktif(tahap: str, g: dict) -> bool:
    """Tahap AI aktif? Default: semua aktif kalau penyedia AI bukan 'lokal'.
    Atur per tahap dengan --ai-tahap "skor,hook" atau matikan total dengan "off"."""
    daftar = str(g.get("ai_tahap") or "").strip()
    if daftar.lower() in ("off", "0", "none"):
        return False
    if daftar:
        return tahap in [x.strip() for x in daftar.split(",") if x.strip()]
    return True


def ai_siap(penyedia: str, g: dict) -> bool:
    """Apakah ada penyedia AI yang bisa dipakai sekarang."""
    if not penyedia or penyedia == "lokal":
        return False
    env = baca_env()
    if penyedia == "openrouter":
        return bool(env.get("OPENROUTER_API_KEY") or env.get("OPENAI_API_KEY"))
    if penyedia == "gemini":
        return bool(env.get("GEMINI_API_KEY"))
    if penyedia == "openai":
        return bool(env.get("OPENAI_API_KEY"))
    return True


def tanya_openrouter(prompt: str, env: dict) -> str:
    """Rantai model free OpenRouter. 429/503 → coba model berikutnya (free tier rate-limited)."""
    import urllib.error
    import urllib.request
    base = (env.get("OPENROUTER_BASE_URL") or "https://openrouter.ai/api/v1").rstrip("/")
    key = env.get("OPENROUTER_API_KEY") or env.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY belum diisi")
    rantai = [m.strip() for m in (env.get("OPENROUTER_MODELS") or ",".join(MODEL_OR_FREE)).split(",") if m.strip()]
    galat = ""
    for model in rantai:
        for _ in range(2):
            try:
                data = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                                   "temperature": 0, "stream": False}).encode()
                req = urllib.request.Request(base + "/chat/completions", data=data, headers={
                    "Content-Type": "application/json", "Authorization": f"Bearer {key}",
                    "HTTP-Referer": "https://studio.onegate.biz.id", "X-Title": "studio-clipper"})
                with urllib.request.urlopen(req, timeout=240) as resp:
                    d = json.loads(resp.read())
                return d["choices"][0]["message"]["content"]
            except urllib.error.HTTPError as e:
                galat = f"{model}: HTTP {e.code}"
                if e.code in (429, 502, 503, 504):
                    time.sleep(2)
                    continue
                break
            except Exception as e:  # noqa: BLE001
                galat = f"{model}: {type(e).__name__} {str(e)[:80]}"
                break
    raise RuntimeError(f"semua model OpenRouter gagal → {galat}")


# Status AI untuk ditampilkan di web UI: apakah AI benar-benar ikut memilih
# momen, atau hasilnya murni heuristik lokal. Diisi oleh ai_json().
AI_STATUS: dict = {"pakai": False, "penyedia": "", "model": "", "alasan": "", "dari_cache": False}


def _ai_catat(pakai: bool, alasan: str, dari_cache: bool = False) -> None:
    AI_STATUS.update({"pakai": pakai, "alasan": alasan, "dari_cache": dari_cache})


def ai_json(penyedia: str, prompt: str, cache: Path | None = None) -> dict | None:
    """Panggil AI → JSON. Gagal = None (pipeline lanjut dengan fallback lokal), tidak fatal."""
    AI_STATUS["penyedia"] = penyedia
    try:
        env = baca_env()
        AI_STATUS["model"] = (env.get("OPENROUTER_MODELS", "").split(",")[0] if penyedia == "openrouter"
                              else env.get("OPENAI_MODEL", "") if penyedia == "openai"
                              else env.get("GEMINI_MODEL", "") if penyedia == "gemini" else penyedia)
    except Exception:  # noqa: BLE001
        AI_STATUS["model"] = ""
    if cache and cache.exists():
        try:
            _ai_catat(True, "Jawaban AI diambil dari cache analisis sebelumnya (tidak memanggil API lagi).", True)
            return json.loads(cache.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    try:
        if penyedia == "openrouter":
            teks = tanya_openrouter(prompt, baca_env())
        else:
            teks = tanya_ai(penyedia, prompt)
    except SystemExit as e:
        log(f"   AI berhenti: {str(e)[:140]}")
        _ai_catat(False, f"AI tidak bisa dipakai: {str(e)[:180]}")
        return None
    except Exception as e:  # noqa: BLE001
        log(f"   AI gagal: {type(e).__name__}: {str(e)[:140]}")
        _ai_catat(False, f"Panggilan AI gagal ({type(e).__name__}): {str(e)[:180]}")
        return None
    # Bersihkan markdown code fences dan teks di sekitar JSON
    bersih_teks = teks.strip()
    # Hapus ```json ... ``` atau ``` ... ```
    if "```" in bersih_teks:
        parts = bersih_teks.split("```")
        for i, p in enumerate(parts):
            if p.strip().startswith("json"):
                p = p[4:].strip()
            p = p.strip()
            if p.startswith("[") or p.startswith("{"):
                bersih_teks = p
                break
    # Cari JSON array atau objek terluar yang valid
    hasil = None
    for start_char, end_char in (("[", "]"), ("{", "}")):
        idx = bersih_teks.find(start_char)
        if idx < 0:
            continue
        depth = 0
        end_idx = -1
        for j in range(idx, len(bersih_teks)):
            if bersih_teks[j] == start_char:
                depth += 1
            elif bersih_teks[j] == end_char:
                depth -= 1
                if depth == 0:
                    end_idx = j
                    break
        if end_idx > idx:
            candidate = bersih_teks[idx:end_idx + 1]
            try:
                hasil = json.loads(candidate)
                break
            except json.JSONDecodeError:
                continue
    if hasil is None:
        log("   AI tidak mengembalikan JSON → pakai fallback lokal.")
        _ai_catat(False, "AI menjawab tetapi bukan JSON, jadi momen dipilih heuristik lokal.")
        return None
    _ai_catat(True, "AI membaca transkrip Whisper dan memilih momen (jawaban JSON valid).")
    _ai_catat(True, "AI membaca transkrip Whisper dan memilih momen (jawaban JSON valid).")
    if cache:
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(hasil, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass
    return hasil


def hitung_sinyal(file: Path, facecam: str = "") -> dict:
    """Sinyal per detik untuk allem: lonjakan suara, reaksi facecam, aksi gameplay."""
    en = energi_audio(file)
    sinyal = {"energi": en, "lonjak": normalisasi(lonjakan(en)),
              "reaksi": np.zeros(1), "aksi": np.zeros(1)}
    fc = facecam or ""
    if fc and Path(fc).exists():
        log("   Menganalisis reaksi facecam (motion frame)…")
        sinyal["reaksi"] = normalisasi(motion_per_detik(Path(fc)))
    log("   Menganalisis aksi gameplay (motion frame)…")
    sinyal["aksi"] = normalisasi(motion_per_detik(file))
    return sinyal


def window_kandidat(kal: list[Kalimat], durasi: float, sinyal: dict, overlap: int = 20) -> list[dict]:
    """Kandidat window untuk AI: potong transkrip per ~durasi detik, batasnya di kalimat utuh."""
    if not kal:
        return []
    target = max(float(durasi), 20.0)
    stride = max(target - overlap, target / 2)

    def ambil(sig: np.ndarray, a: float, b: float) -> float:
        if len(sig) == 0:
            return 0.0
        i0 = min(int(max(a, 0)), len(sig) - 1)
        i1 = min(int(max(b, a + 1)), len(sig))
        return float(sig[i0:i1].max()) if i1 > i0 else float(sig[i0])

    kandidat: list[dict] = []
    mulai = kal[0].mulai
    idx = 1
    while mulai < kal[-1].selesai:
        akhir = mulai + target
        isi = [k for k in kal if k.selesai > mulai and k.mulai < akhir]
        if not isi:
            break
        teks = " ".join(k.teks for k in isi)
        if len(teks.strip()) < 20:
            mulai = akhir
            continue
        kata = [w for k in isi for w in k.kata]
        e = ambil(sinyal.get("energi", np.zeros(1)), mulai, akhir)
        lj = ambil(sinyal.get("lonjak", np.zeros(1)), mulai, akhir)
        rk = ambil(sinyal.get("reaksi", np.zeros(1)), mulai, akhir)
        ak = ambil(sinyal.get("aksi", np.zeros(1)), mulai, akhir)
        kandidat.append({
            "id": f"w{idx}", "mulai": round(mulai, 2), "selesai": round(isi[-1].selesai, 2),
            "teks": teks[:1200],
            "sinyal": {"energi": round(e, 3), "lonjak": round(lj, 3),
                       "reaksi": round(rk, 3), "aksi": round(ak, 3)},
            "kata_gaming": sorted({bersih_kata(w.teks) for w in kata if HOOK_GAME.match(bersih_kata(w.teks))})[:8],
            "interjeksi": sorted({m.group(0).lower() for m in INTERJEKSI.finditer(teks)})[:8],
        })
        idx += 1
        mulai += stride
    return kandidat


def snap_ke_kata(a: float, b: float, kata: list[Kata], jeda: float = 1.5) -> tuple[float, float]:
    """Geser batas potong ke timestamp kata terdekat supaya tidak potong di tengah kata."""
    if not kata:
        return a, b
    dekat_a = min(kata, key=lambda w: abs(w.mulai - a))
    dekat_b = min(kata, key=lambda w: abs(w.selesai - b))
    baru_a = a if abs(dekat_a.mulai - a) > jeda else dekat_a.mulai
    baru_b = b if abs(dekat_b.selesai - b) > jeda else dekat_b.selesai
    if baru_b - baru_a < 3:
        baru_b = baru_a + 3
    return round(baru_a, 2), round(baru_b, 2)


def ai_skor_window(kandidat: list[dict], penyedia: str, cache: Path | None = None) -> dict:
    """Minta AI menilai tiap window (rubrik 2-second test + bukti sinyal gaming)."""
    if not kandidat:
        return {}
    isi = [{"id": k["id"], "start": k["mulai"], "end": k["selesai"], "text": k["teks"][:700],
            "signals": k["sinyal"], "gaming_words": k["kata_gaming"], "interjections": k["interjeksi"]}
           for k in kandidat]
    prompt = f"""You are a senior short-form video strategist for GAMING content. RANK these candidate windows by how well each would work as a standalone short for TikTok/IG Reels/YouTube Shorts.

Rules:
- Return only valid JSON, no prose, no markdown fence.
- Score EVERY window: exactly one entry per input window.
- `score` must be an integer 0-100.
- THE 2-SECOND TEST is the main criterion: would the first 2 seconds force a cold viewer (no context) to keep watching? Windows that only work with prior context score low.
- STANDS ALONE: the clip must make sense to someone who has seen nothing else. If a window OPENS on a pronoun ("ini", "itu", "gitu"), a filler ("ya", "nah", "oke"), or an answer to a question asked earlier ("kenapa?", "nggak?"), score it lower than a window that opens on the payoff itself — a window whose strong moment starts a few seconds in is still a good window.
- Prefer windows with strong hooks, conflict, surprise, outrage, emotion, novelty, or a clear payoff.
- Gaming signal: screaming/excitement, reactions, clutch plays, banter with friends. A window of pure gameplay with NO voice reaction is weaker than a window where the player reacts.
- These windows carry extra signals measured from audio/facecam/gameplay: REACTION (facecam motion 0-1), ENERGY (audio peak 0-1), SURGE (sudden loudness jump 0-1). Use them as evidence, but the transcript still decides.
- If the transcript shows narration of something else (a TV show, a news story, a documentary) rather than the player's own reaction, score it LOW.

TRANSCRIPT_LANGUAGE: id
WINDOWS_JSON:
{json.dumps(isi, ensure_ascii=False)}

Return only:
{{"windows":[{{"id":"...","score":<0-100>,"reason":"<short, in Indonesian>"}}]}}"""
    hasil = ai_json(penyedia, prompt, cache)
    if not hasil:
        return {}
    out: dict = {}
    for w in hasil.get("windows", []) or []:
        try:
            out[str(w["id"])] = {"score": int(w.get("score", 0)), "reason": str(w.get("reason", ""))[:200]}
        except (KeyError, TypeError, ValueError):
            continue
    return out


def ai_pilih_klip(kandidat: list[dict], skor: dict, kal: list[Kalimat], jumlah: int) -> list[Klip]:
    """Ubah window + skor AI jadi daftar Klip (tanpa tumpang tindih, batas snap ke kata, pembuka diverifikasi)."""
    semua_kata = [w for k in kal for w in k.kata]
    utuh = kalimat_utuh(kal)
    urut = sorted(kandidat, key=lambda k: skor.get(k["id"], {}).get("score", 0), reverse=True)
    terpilih: list[Klip] = []
    for k in urut:
        s = skor.get(k["id"], {})
        if not s:
            continue
        a, b = snap_ke_kata(k["mulai"], k["selesai"], semua_kata)
        # STANDS ALONE: pembuka yang butuh konteks digeser ke kalimat yang berdiri sendiri
        ket = ""
        idx = [i for i, x in enumerate(utuh) if x.selesai > a and x.mulai < b]
        if idx:
            a2, b2, ket = perbaiki_pembuka(utuh, idx[0], idx[-1], a, b)
            if ket:
                a, b = a2, b2
        if all(b <= t.mulai or a >= t.selesai for t in terpilih):
            judul = (k["teks"][:70] or f"Klip {a:.0f}s").strip()
            alasan = " · ".join(x for x in [s.get("reason", "").strip(), "AI 2-second test", ket] if x)
            terpilih.append(Klip(a, b, judul, float(s.get("score", 0)), alasan or "picked by AI"))
        if len(terpilih) >= jumlah:
            break
    return sorted(terpilih, key=lambda c: c.mulai)


def ai_polih_transkrip(kal: list[Kalimat], penyedia: str, cache: Path | None = None) -> list[Kalimat]:
    """Koreksi salah dengar ASR (khusus Indonesia lisan) — timing kata tidak diubah."""
    if not kal:
        return kal
    hasil = ai_json(penyedia, """Perbaiki salah dengar hasil transkripsi otomatis (ASR) bahasa Indonesia lisan.
Aturan:
- Return only valid JSON, no prose, no markdown fence.
- Hanya tulis kalimat yang benar-benar salah dengar (tyo, nama yang kacau, kata slang yang keliru). Kalimat yang sudah benar TIDAK perlu ditulis.
- Jangan menambah atau menghapus fakta; hanya perbaiki ejaan/kosakata.
- Batas: 12 kata per kalimat.

Return only:
{"perbaikan":[{"index":<nomor urut kalimat, mulai dari 1>,"teks":"<kalimat yang diperbaiki>"}]}""", cache)
    if not hasil:
        return kal
    baru = list(kal)
    for p in hasil.get("perbaikan", []) or []:
        try:
            i = int(p["index"]) - 1
        except (KeyError, TypeError, ValueError):
            continue
        if 0 <= i < len(baru) and p.get("teks"):
            baru[i] = Kalimat(baru[i].mulai, baru[i].selesai, str(p["teks"]).strip(), baru[i].kata)
    return baru


def ai_metadata(klips: list[Klip], penyedia: str, cache: Path | None = None) -> list[dict]:
    """Buat hook text, judul YouTube, caption IG/TikTok + hashtag, dan alasan Publish-ready."""
    if not klips:
        return []
    ringkas = [{"no": i + 1, "start": k.mulai, "end": k.selesai, "teks": k.judul[:400]}
               for i, k in enumerate(klips)]
    prompt = f"""Kamu editor short-form video. Untuk tiap klip di bawah, tulis metadata siap posting.

Aturan:
- Return only valid JSON, no prose, no markdown fence.
- SEMUA teks (hook, judul, caption) HARUS dalam {instruksi_bahasa()}.
- `hook`: maksimal 10 kata, punchy, TENTANG MOMEN INI (bukan tentang video secara umum). Contoh pola: pertanyaan, hot take, fakta/angka, loop cerita, POV. Boleh 1-2 emoji.
- `judul_yt`: maksimal 100 karakter, bikin penasaran, jangan klaim palsu.
- `caption_ig` / `caption_tiktok`: 1-2 kalimat tease tanpa spoiler + 3-5 hashtag yang relevan (jangan spam hashtag generik).
- `why`: 1 kalimat maksimal 20 kata, menyebut hook/claim/payoff spesifik di klip ini.

KLIPS:
{json.dumps(ringkas, ensure_ascii=False)}

Return only:
{{"metadata":[{{"no":1,"hook":"...","judul_yt":"...","caption_ig":"...","caption_tiktok":"...","why":"..."}}]}}"""
    hasil = ai_json(penyedia, prompt, cache)
    if not hasil:
        return []
    # AI kadang balas list langsung, kadang objek {"metadata": [...]}
    if isinstance(hasil, dict):
        metadata_list = hasil.get("metadata", []) or []
    elif isinstance(hasil, list):
        metadata_list = hasil
    else:
        return []
    out = []
    for m in metadata_list:
        try:
            no = int(m["no"])
        except (KeyError, TypeError, ValueError):
            continue
        out.append({"no": no, "hook": str(m.get("hook", ""))[:120],
                    "judul_yt": str(m.get("judul_yt", ""))[:140],
                    "caption_ig": str(m.get("caption_ig", ""))[:400],
                    "caption_tiktok": str(m.get("caption_tiktok", ""))[:400],
                    "why": str(m.get("why", ""))[:200]})
    return out


def ai_pilih_layout(transkrip_ringkas: str, sinyal: dict, penyedia: str, cache: Path | None = None) -> str:
    """Saran layout dari isi + sinyal (bukan facecam 2-kamera; itu khusus gaming)."""
    hasil = ai_json(penyedia, f"""Pilih satu layout untukklip video ini.
Pilihan: "tunggal" (satu pembicara, crop 9:16 mengikuti wajah) · "gamer" (wajah atas + gameplay bawah + branding).
Return only valid JSON, no prose: {{"layout":"tunggal","reason":"<short>"}}

RINGKASAN TRANSKRIP:
{transkrip_ringkas[:1500]}

SINYAL: reaksi_wajah={float((sinyal.get('reaksi') or [0])[0]):.2f} aksi_game={float((sinyal.get('aksi') or [0])[0]):.2f}""", cache)
    if not hasil:
        return ""
    if isinstance(hasil, dict):
        return str(hasil.get("layout", ""))[:20]
    elif isinstance(hasil, list) and hasil:
        return str(hasil[0].get("layout", ""))[:20] if isinstance(hasil[0], dict) else ""
    return ""


def qc_klip(path: Path, target_durasi: float, layout: str = "") -> dict:
    """Cek hasil render: durasi, resolusi, audio, band kosong, teks di tengah."""
    hasil = {"file": path.name, "ok": True, "catatan": []}
    if not path.exists():
        return {"file": path.name, "ok": False, "catatan": ["file tidak ada"], "durasi": 0}
    import subprocess as sp
    try:
        info = json.loads(sp.run(["ffprobe", "-v", "error", "-show_entries",
                                  "format=duration:stream=codec_type,width,height",
                                  "-of", "json", str(path)], capture_output=True, text=True).stdout or "{}")
    except json.JSONDecodeError:
        info = {}
    dur = float((info.get("format") or {}).get("duration") or 0)
    hasil["durasi"] = round(dur, 2)
    vids = [s for s in info.get("streams", []) if s.get("codec_type") == "video"]
    auds = [s for s in info.get("streams", []) if s.get("codec_type") == "audio"]
    if not vids:
        hasil["ok"] = False
        hasil["catatan"].append("tidak ada stream video")
        return hasil
    w, h = vids[0].get("width", 0), vids[0].get("height", 0)
    hasil["resolusi"] = f"{w}x{h}"
    if layout != "lebar" and (w, h) != (1080, 1920):
        hasil["catatan"].append(f"resolusi {w}x{h} (harus 1080x1920)")
    if not auds:
        hasil["catatan"].append("tidak ada audio")
    if target_durasi and dur and not (target_durasi * 0.7 <= dur <= target_durasi * 1.4):
        hasil["catatan"].append(f"durasi {dur:.1f}s jauh dari target {target_durasi:.0f}s")
    # cek band kosong (hitam total) +igr
    try:
        import cv2
        cap = cv2.VideoCapture(str(path))
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        sample = [int(total * f) for f in (0.15, 0.45, 0.8)] if total else [5]
        hitam = 0
        for n in sample:
            cap.set(cv2.CAP_PROP_POS_FRAMES, max(n, 0))
            ok, fr = cap.read()
            if ok and fr is not None and float(fr.std()) < 2.0:
                hitam += 1
        cap.release()
        if sample and hitam == len(sample):
            hasil["catatan"].append("semua frame sampel hitam")
    except Exception:  # noqa: BLE001
        pass
    if hasil["catatan"]:
        hasil["ok"] = False
    return hasil


# ── 5. Bingkai: deteksi wajah ───────────────────────────────────────────────
_YUNET: dict = {}


def wajah_di(fr, w: int, h: int) -> list[tuple[float, float, float]]:
    """Semua wajah di satu frame: (x tengah, y tengah, lebar) dalam 0..1. YuNet bila modelnya ada, Haar sebagai cadangan."""
    import cv2
    lb = 640
    tb = int(h * lb / w)
    kecil = cv2.resize(fr, (lb, tb))
    model = Path(__file__).resolve().parent / "model" / "face_detection_yunet_2023mar.onnx"
    if model.exists() and hasattr(cv2, "FaceDetectorYN"):
        det = _YUNET.get((lb, tb))
        if det is None:
            det = _YUNET[(lb, tb)] = cv2.FaceDetectorYN.create(str(model), "", (lb, tb), 0.6, 0.3, 50)
        _, f = det.detect(kecil)
        return [((x + fw / 2) / lb, (y + fh / 2) / tb, fw / lb) for x, y, fw, fh, *_ in (f if f is not None else [])]
    haar = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    g = cv2.cvtColor(kecil, cv2.COLOR_BGR2GRAY)
    return [((x + fw / 2) / lb, (y + fh / 2) / tb, fw / lb) for x, y, fw, fh in haar.detectMultiScale(g, 1.1, 5, minSize=(24, 24))]


def info_wajah(file: Path, a: float, b: float, w: int, h: int) -> dict:
    """Median posisi & ukuran wajah terbesar (0..1) di rentang klip. Tanpa wajah → tengah."""
    import cv2
    cap = cv2.VideoCapture(str(file))
    xs, ys, ss = [], [], []
    t = a
    langkah = max((b - a) / 12, 0.8)
    while t < b:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, fr = cap.read()
        if not ok:
            break
        f = wajah_di(fr, w, h)
        if f:
            x, y, s_ = max(f, key=lambda r: r[2])
            xs.append(x); ys.append(y); ss.append(s_)
        t += langkah
    cap.release()
    if not xs:
        return {"ada": False, "x": 0.5, "y": 0.35, "s": 0.18}
    return {"ada": True, "x": float(np.median(xs)), "y": float(np.median(ys)), "s": float(np.median(ss))}


def dua_wajah(file: Path, a: float, b: float, w: int, h: int) -> list[dict] | None:
    """Dua orang (kiri & kanan) untuk layout Split Podcast.

    Konsensus per-frame: tiap frame dengan >=2 wajah menghasilkan satu pasangan
    (kiri, kanan). Posisi akhir = median pasangan, jadi satu frame outlier tidak
    menggeser bingkai.

    Versi lama mengumpulkan SEMUA wajah dari semua frame lalu membelah di celah-x
    terbesar dengan syarat celah >= 0.12. Pada podcast 2 orang yang posisinya
    berdekatan (mis. 0.36 vs 0.68 -> celah 0.11) itu selalu gagal, sehingga
    layout diam-diam jatuh ke tunggal padahal dua orangnya jelas terlihat.
    Cara baru tidak memakai ambang celah: cukup dua wajah terlihat BERSAMAAN di
    frame yang sama, lalu posisinya harus konsisten antar-frame.

    None bila tidak ada dua orang yang konsisten -> layout jatuh ke tunggal.
    """
    import cv2
    cap = cv2.VideoCapture(str(file))
    pasangan: list[tuple[tuple[float, float, float], tuple[float, float, float]]] = []
    t, langkah = a, max((b - a) / 16, 0.6)
    while t < b:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, fr = cap.read()
        if not ok:
            break
        f = sorted(wajah_di(fr, w, h), key=lambda r: r[0])
        if len(f) >= 2:
            kiri, kanan = f[0], f[-1]
            if float(kanan[0]) - float(kiri[0]) >= 0.15:
                pasangan.append((kiri, kanan))
        t += langkah
    cap.release()
    if len(pasangan) < 2:
        return None

    def robust(sisi: list[tuple[float, float, float]]) -> dict:
        """Median + buang outlier jauh dari median (posisi orang tidak lompat-lompat)."""
        xs = np.array([float(p[0]) for p in sisi])
        mx = float(np.median(xs))
        dekat = [p for p, x in zip(sisi, xs) if abs(float(x) - mx) <= 0.12]
        if len(dekat) < 2:
            dekat = sisi
        return {"x": float(np.median([float(p[0]) for p in dekat])),
                "y": float(np.median([float(p[1]) for p in dekat])),
                "s": float(np.median([float(p[2]) for p in dekat]))}

    k = robust([p[0] for p in pasangan])
    n = robust([p[1] for p in pasangan])
    if n["x"] - k["x"] < 0.18:
        return None
    return [k, n]


_JEJAK_SIAP: dict[tuple[float, float], list] = {}  # jejak tersimpan di klip.json (dipakai pratinjau Studio & render)


def amplop_suara(file: Path, a: float, b: float, fps: float) -> np.ndarray:
    """Kekerasan suara (RMS) per 1/fps detik di rentang [a, b]."""
    sr = 16000
    raw = subprocess.run([ffmpeg(), "-v", "error", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", str(file),
                          "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
    n = int((b - a) * fps) + 1
    per = int(sr / fps)
    out = np.zeros(n)
    for k in range(n):
        bag = x[k * per:(k + 1) * per]
        if len(bag):
            out[k] = float(np.sqrt((bag ** 2).mean()))
    return out


def _korelasi(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 4 or x.std() < 1e-9 or y.std() < 1e-9:
        return 0.0
    return float(np.corrcoef(x, y)[0, 1])


def jejak_wajah(file: Path, a: float, b: float, w: int, h: int) -> list[tuple[float, float]]:
    """Titik kunci (detik relatif klip, posisi-x 0..1) yang mengikuti PEMBICARA AKTIF.

    1) sampel 6 frame/dtk; sidik 12×12 abu-abu → pindah kamera di video sumber;
    2) tiap wajah diukur gerak mulutnya (perubahan sepertiga bawah wajah, dikurangi gerak kepala);
    3) pembicara = wajah yang gerak mulutnya paling SEIRAMA dengan suara di jendela ±1,5 dtk,
       jadi pendengar yang tertawa/mengangguk tidak dipilih;
    4) kamera diam (tidak menggeser lewat ruang kosong), pindah seketika di potongan kamera
       atau saat pembicara berganti ≥ 0,8 dtk; celah tanpa wajah memakai posisi terakhir, bukan tengah.
    """
    siap = _JEJAK_SIAP.get((round(a, 2), round(b, 2)))
    if siap:
        return [tuple(x) for x in siap]
    import cv2
    fps = 6.0
    depan = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml") if hasattr(cv2, "CascadeClassifier") else None
    profil = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml") if hasattr(cv2, "CascadeClassifier") else None
    try:
        suara = amplop_suara(file, a, b, fps)
    except Exception:  # noqa: BLE001 — video tanpa audio
        suara = np.zeros(int((b - a) * fps) + 1)
    LB = 640
    sk = LB / w
    TB = int(h * sk)
    yunet = None
    model = Path(__file__).resolve().parent / "model" / "face_detection_yunet_2023mar.onnx"
    if model.exists() and hasattr(cv2, "FaceDetectorYN"):
        yunet = cv2.FaceDetectorYN.create(str(model), "", (LB, TB), 0.6, 0.3, 50)
    n = int((b - a) * fps) + 1
    cap = cv2.VideoCapture(str(file))
    cap.set(cv2.CAP_PROP_POS_MSEC, a * 1000)
    sumber_fps = cap.get(cv2.CAP_PROP_FPS) or 30
    sampel: list[list[dict]] = []
    potong = [False] * n
    sidik_lalu = None
    k, fr_i = 0, 0
    while k < n:
        ok, fr = cap.read()
        if not ok:
            break
        t_fr = a + fr_i / sumber_fps
        fr_i += 1
        if t_fr + 1e-6 < a + k / fps:
            continue
        kecil = cv2.resize(fr, (LB, TB))
        abu = cv2.cvtColor(kecil, cv2.COLOR_BGR2GRAY)
        sd = cv2.resize(abu, (12, 12), interpolation=cv2.INTER_AREA).astype(np.float32)
        if sidik_lalu is not None:
            potong[k] = float(np.abs(sd - sidik_lalu).mean()) > 28
        sidik_lalu = sd
        kotak = []
        if yunet is not None:  # YuNet: tahan wajah miring, tertawa, berhijab
            _, hasil = yunet.detect(kecil)
            for r in (hasil if hasil is not None else []):
                x, y, fw, fh = (int(max(v, 0)) for v in r[:4])
                if fw > 8 and fh > 8:
                    kotak.append((x, y, min(fw, LB - x), min(fh, TB - y), 1.0))
        else:
            kotak = [(x, y, fw, fh, 1.0) for (x, y, fw, fh) in depan.detectMultiScale(abu, 1.1, 5, minSize=(24, 24))] if depan else []
        if not kotak and profil is not None:  # profil hanya bila tidak ada wajah depan (hemat waktu)
            kotak += [(x, y, fw, fh, 0.8) for (x, y, fw, fh) in profil.detectMultiScale(abu, 1.1, 5, minSize=(24, 24))]
            kotak += [(LB - x - fw, y, fw, fh, 0.8) for (x, y, fw, fh) in
                      profil.detectMultiScale(cv2.flip(abu, 1), 1.1, 5, minSize=(24, 24))]
        wajah = []
        for (x, y, fw, fh, bobot) in kotak:
            mulut = cv2.resize(abu[y + int(fh * 0.62):y + fh, x + int(fw * 0.2):x + int(fw * 0.8)], (24, 12)).astype(np.float32)
            atas = cv2.resize(abu[y:y + int(fh * 0.5), x:x + fw], (24, 12)).astype(np.float32)
            wajah.append({"cx": (x + fw / 2) / LB, "luas": fw * fh / (LB * TB) * bobot, "mulut": mulut, "atas": atas})
        # buang wajah dobel (depan & profil di tempat sama)
        unik: list[dict] = []
        for f in sorted(wajah, key=lambda f: -f["luas"]):
            if all(abs(f["cx"] - u["cx"]) > 0.06 for u in unik):
                unik.append(f)
        sampel.append(unik)
        k += 1
    cap.release()
    n = len(sampel)
    if n == 0 or all(not s for s in sampel):
        return [(0.0, 0.5)]
    suara = np.pad(suara, (0, max(0, n - len(suara))))[:n]
    potong = potong[:n]
    DEKAT = 0.09

    def cari(j: int, c: float):
        if 0 <= j < n:
            f = min(sampel[j], key=lambda f: abs(f["cx"] - c), default=None)
            if f is not None and abs(f["cx"] - c) < DEKAT:
                return f
        return None

    # gerak mulut per wajah per sampel (dibandingkan sampel sebelumnya pada wajah yang sama)
    for j in range(n):
        for f in sampel[j]:
            g = cari(j - 1, f["cx"]) if not potong[j] else None
            if g is None:
                f["gerak"] = 0.0
            else:
                gm = float(np.abs(f["mulut"] - g["mulut"]).mean())
                ga = float(np.abs(f["atas"] - g["atas"]).mean())
                f["gerak"] = max(gm - 0.6 * ga, 0.0)  # kurangi gerak kepala/kamera

    awal_shot = [j for j in range(n) if j == 0 or potong[j]]
    target = [float("nan")] * n
    jendela = int(1.5 * fps)
    for si, s0 in enumerate(awal_shot):
        s1 = (awal_shot[si + 1] if si + 1 < len(awal_shot) else n) - 1
        pusat: list[float] = []
        for j in range(s0, s1 + 1):
            for f in sampel[j]:
                if all(abs(c - f["cx"]) >= DEKAT for c in pusat):
                    pusat.append(f["cx"])
        if not pusat:
            continue
        if len(pusat) == 1:
            for j in range(s0, s1 + 1):
                target[j] = pusat[0]
            continue
        for j in range(s0, s1 + 1):
            lo, hi = max(s0, j - jendela), min(s1, j + jendela)
            terbaik, skor_terbaik = pusat[0], -9.0
            for c in pusat:
                gerak, ada, luas = [], 0, 0.0
                for q in range(lo, hi + 1):
                    f = cari(q, c)
                    if f is not None:
                        ada += 1
                        luas += f["luas"]
                    gerak.append(f["gerak"] if f is not None else 0.0)
                if not ada:
                    continue
                skor = (_korelasi(np.array(gerak), suara[lo:hi + 1]) + 0.15 * ada / len(gerak)
                        + 0.5 * luas / ada)
                if skor > skor_terbaik:
                    terbaik, skor_terbaik = c, skor
            target[j] = terbaik
    # celah tanpa wajah → posisi terdekat sebelumnya (jangan kembali ke tengah)
    akhir = next((x for x in target if x == x), 0.5)
    for j in range(n):
        if target[j] != target[j]:
            target[j] = akhir
        else:
            akhir = target[j]
    # kamera menahan posisi; pindah seketika di potongan kamera, atau bila pembicara baru bertahan ≥ 0,8 dtk
    kam, calon, lama = target[0], target[0], 0
    kunci: list[tuple[float, float]] = [(0.0, kam)]
    for j in range(1, n):
        baru = None
        if potong[j]:
            baru = target[j]
            calon, lama = baru, 0
        elif abs(target[j] - kam) > DEKAT:
            if abs(target[j] - calon) < DEKAT:
                lama += 1
            else:
                calon, lama = target[j], 1
            if lama >= int(0.8 * fps):
                baru, lama = calon, 0
        else:
            lama = 0
        if baru is not None and abs(baru - kam) > 0.01:
            t = j / fps
            kunci.append((max(t - 0.02, kunci[-1][0] + 0.01), kam))  # tahan sampai detik pindah …
            kunci.append((t, baru))                                   # … lalu lompat tegas
            kam = baru
    kunci.append(((n - 1) / fps + 1 / fps, kam))
    return kunci


def potong_jejak(w: int, h: int, rasio: float, kunci: list[tuple[float, float]]) -> str:
    """Crop berasio tetap dengan posisi-x yang berubah menurut waktu (interpolasi linear antar titik kunci)."""
    if w / h > rasio:
        ch = h // 2 * 2
        cw = int(ch * rasio) // 2 * 2
    else:
        cw = w // 2 * 2
        ch = int(cw / rasio) // 2 * 2
    if len(kunci) == 1 or cw >= w:
        x0 = int(min(max(kunci[0][1] * w - cw / 2, 0), w - cw))
        return f"crop={cw}:{ch}:{x0}:{(h - ch) // 2}"
    px = [(t, min(max(x * w - cw / 2, 0), w - cw)) for t, x in kunci]
    # bangun ekspresi bertingkat: if(lt(t,t1), lerp, if(lt(t,t2), …))
    expr = f"{px[-1][1]:.1f}"
    for (t0, x0), (t1, x1) in reversed(list(zip(px, px[1:]))):
        if t1 - t0 < 0.05:
            seg = f"{x1:.1f}"
        else:
            seg = f"{x0:.1f}+({x1 - x0:.1f})*(t-{t0:.2f})/{t1 - t0:.2f}"
        expr = f"if(lt(t,{t1:.2f}),{seg},{expr})"
    expr = expr.replace(",", "\\,")
    return f"crop={cw}:{ch}:{expr}:{(h - ch) // 2}"


def potong(w: int, h: int, rasio: float, cx: float, cy: float = 0.5, skala: float = 1.0) -> str:
    """Filter crop ffmpeg berasio `rasio` (lebar/tinggi) di sekitar titik (cx, cy). skala<1 = memperbesar (zoom)."""
    if w / h > rasio:
        ch = int(h * skala) // 2 * 2
        cw = int(ch * rasio) // 2 * 2
    else:
        cw = int(w * skala) // 2 * 2
        ch = int(cw / rasio) // 2 * 2
    cw, ch = min(cw, w // 2 * 2), min(ch, h // 2 * 2)
    x = int(min(max(cx * w - cw / 2, 0), w - cw))
    y = int(min(max(cy * h - ch / 2, 0), h - ch))
    return f"crop={cw}:{ch}:{x}:{y}"


# ── 6. Subtitle & banner (ASS) ──────────────────────────────────────────────
def waktu_ass(t: float) -> str:
    t = max(t, 0)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def warna_ass(hexa: str, alfa: str = "00") -> str:
    hexa = (hexa or "#FFFFFF").lstrip("#")
    return f"&H{alfa}{hexa[4:6]}{hexa[2:4]}{hexa[0:2]}".upper()


def tanpa_emoji(t: str) -> str:
    # libass tidak bisa menggambar emoji berwarna (muncul kotak) → buang
    return re.sub(r"[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u200D]", "", t).strip()


def ubah_huruf(t: str, mode: str) -> str:
    t = tanpa_emoji(t)
    return t.upper() if mode == "kapital" else t.lower() if mode == "kecil" else t


UKURAN = {"kecil": 0.82, "sedang": 1.0, "besar": 1.22}  # pengali ukuran preset
FONT_DIR = Path(__file__).resolve().parent / "font"  # font OFL dibundel → hasil sama di Mac & Windows

# Preset "Gaya klip" — pola dari riset dokumentasi/26 (bukan tiruan tampilan alat/kreator mana pun).
# mode: warna (kata aktif berwarna+membesar) · pop (grup memantul masuk, kata kunci berwarna) · komik (tepi tebal,
# kata kunci berwarna, kata aktif memantul) · tebal (kata aktif tipis→tebal) · karaoke (warna mengisi kata) ·
# terbaca (kotak hitam, teks kuning, kata aktif putih) · polos (tanpa sorot)
PRESET = {
    "sorot":   dict(font="Archivo Black", tebal=0, huruf="kapital", per=3, uk=78, warna="#FFD400", mode="warna", tepi=6, bayang=2),
    "pop":     dict(font="Anton", tebal=0, huruf="kapital", per=2, uk=112, warna="#FFD400", mode="pop", tepi=4, bayang=5),
    "komik":   dict(font="Bangers", tebal=0, huruf="kapital", per=3, uk=104, warna="#3BE477", mode="komik", tepi=10, bayang=0, spasi=2),
    "halus":   dict(font="Montserrat Light", font_aktif="Montserrat", tebal=0, huruf="kecil", per=4, uk=62, warna="#FFFFFF",
                    mode="tebal", tepi=1, bayang=4),
    "karaoke": dict(font="Montserrat ExtraBold", tebal=0, huruf="biasa", per=6, uk=66, warna="#FFD400", mode="karaoke", tepi=5, bayang=0),
    "terbaca": dict(font="Montserrat ExtraBold", tebal=0, huruf="kapital", per=4, uk=66, warna="#FFE600", mode="terbaca",
                    kotak="&H00000000", tepi=14, bayang=0),
    "minimal": dict(font="Montserrat Medium", tebal=0, huruf="biasa", per=6, uk=60, warna="#FFFFFF", mode="polos", tepi=2, bayang=3),
    "podcast": dict(font="Montserrat ExtraBold", tebal=0, huruf="kapital", per=3, uk=74, warna="#FFD400", mode="warna", tepi=5,
                    bayang=0, latar="blur", banner_kotak="&H00000000", progres=True),
    "isanovski":  dict(font="Space Grotesk", tebal=1, huruf="biasa", per=3, uk=72, warna="#22D3EE", mode="warna",
                    kotak="&H38170F0B", tepi=16, bayang=0, banner_kotak="&H38170F0B", banner_warna="#22D3EE", progres=True),
    # 2.1 — kotak sorot mengikuti kata aktif, hook neon + coretan, judul serif elegan, judul kertas sobek
    "lime":    dict(font="Montserrat ExtraBold", tebal=0, huruf="kapital", per=3, uk=76, warna="#C6FF3D", mode="kotak", tepi=4, bayang=0),
    "neon":    dict(font="Bangers", tebal=0, huruf="kapital", per=2, uk=108, warna="#FF4FA3", mode="pop", tepi=8, bayang=0,
                    judul="neon"),
    "elegan":  dict(font="Georgia", tebal=1, huruf="biasa", per=4, uk=68, warna="#FFD400", mode="warna", tepi=3, bayang=3,
                    judul="serif"),
    "sobek":   dict(font="Archivo Black", tebal=0, huruf="kapital", per=3, uk=74, warna="#FF4FA3", mode="warna", tepi=6, bayang=2,
                    judul="sobek"),
}
# ── Gaya banner pembuka (5 detik pertama) ──────────────────────────────────
# Setiap klip mendapat gaya BERBEDA (dipilih acak berdasar waktu mulai klip).
# Semua memakai BorderStyle=3 = kotak opaque di belakang teks, bukan teks polos.
# Bahasa untuk judul/banner yang dihasilkan AI. Diatur lewat --bahasa-judul.
BAHASA_JUDUL = "id"


def instruksi_bahasa() -> str:
    return "Bahasa Indonesia" if BAHASA_JUDUL == "id" else "English"


GAYA_BANNER = [
    dict(nama="kotak-kuning", font="Archivo Black", ukuran=64, warna="#0B0C0F", kotak="#FFD400", bayang=0, kapital=True),
    dict(nama="kotak-cyan", font="Space Grotesk", ukuran=62, warna="#050505", kotak="#22D3EE", bayang=0, kapital=True),
    dict(nama="kotak-hitam", font="Montserrat ExtraBold", ukuran=62, warna="#FFFFFF", kotak="#0B0C0F", bayang=4, kapital=True),
    dict(nama="neon-pink", font="Bangers", ukuran=88, warna="#FF4FA3", kotak="#111111", bayang=6, kapital=True),
    dict(nama="kotak-lime", font="Anton", ukuran=72, warna="#0B0C0F", kotak="#C6FF3D", bayang=0, kapital=True),
    dict(nama="kotak-ungu", font="Space Grotesk", ukuran=64, warna="#FFFFFF", kotak="#7C3AED", bayang=0, kapital=True),
    dict(nama="kotak-oranye", font="Archivo Black", ukuran=66, warna="#0B0C0F", kotak="#FF7A1A", bayang=0, kapital=True),
    dict(nama="kotak-putih", font="Montserrat ExtraBold", ukuran=60, warna="#111111", kotak="#FFFFFF", bayang=0, kapital=True),
    dict(nama="kotak-merah", font="Anton", ukuran=70, warna="#FFFFFF", kotak="#E11D48", bayang=0, kapital=True),
    dict(nama="kotak-biru", font="Space Grotesk", ukuran=64, warna="#FFFFFF", kotak="#1D4ED8", bayang=0, kapital=True),
]


def pilih_gaya_banner(klip) -> dict:
    """Pilih gaya banner secara deterministik per klip (bukan acak global).

    Seeded dari waktu mulai supaya setiap klip dalam satu video mendapat gaya
    berbeda, tetapi hasilnya tetap sama bila klip itu dirender ulang.
    """
    import random
    benih = int(round(float(klip.mulai) * 100)) ^ len(klip.judul or "")
    return random.Random(benih).choice(GAYA_BANNER)


GAYA_JUDUL = ("kuning", "neon", "serif", "kotak", "sobek")  # gaya judul di atas (tahan sampai akhir klip)
ANIM_DIR = Path(__file__).resolve().parent / "anim"  # hiasan animasi transparan (WebP 540×960, 30 fps) dari Remotion
LAMA = {"sorot": "sorot", "kotak": "terbaca", "garis": "minimal"}  # gaya_sub versi lama → preset


def gaya_akhir(g: dict) -> dict:
    """Preset sebagai dasar, lalu pilihan manual pengguna menimpanya."""
    nama = g.get("preset") or LAMA.get(g.get("gaya_sub", "sorot"), "sorot")
    c = {**PRESET.get(nama, PRESET["sorot"]), "preset": nama}
    for k in ("font", "warna", "huruf", "latar"):
        if g.get(k):
            if k == "font" and g[k] != c["font"]:
                c.pop("font_aktif", None)
                c["tebal"] = 1 if g[k] not in ("Archivo Black", "Anton", "Bangers") and "Bold" not in g[k] else 0
            c[k] = g[k]
    c.setdefault("progres", True)
    c.setdefault("zoom", False)
    for k in ("progres", "zoom", "akun", "emoji", "watermark"):
        if k in g:
            c[k] = g[k]
    c.setdefault("emoji", True)
    c.setdefault("judul", "kuning")
    if g.get("gaya_judul") in GAYA_JUDUL:
        c["judul"] = g["gaya_judul"]
    c["uk"] = int(c["uk"] * UKURAN.get(g.get("ukuran", "sedang"), 1.0))
    return c


def baris_judul(teks: str, c: dict, panjang: float) -> str:
    """Satu baris Dialogue ASS untuk judul di atas sesuai gaya.

    Animasi masuk tetap ada, tapi teksnya ditahan sampai klip habis (bukan 3 detik),
    lalu memudar di akhir.
    """
    t = waktu_ass
    j = c.get("judul", "kuning")
    sl = panjang
    if j == "neon":
        uk = max(min(int(5200 / max(len(teks), 1)), 210), 120)  # boleh 2 baris
        return (f"Dialogue: 2,{t(0)},{t(sl)},JudulNeon,,0,0,0,,{{\\an5\\pos(540,840)\\frz-4\\fs{uk}\\fscx30\\fscy30"
                f"\\t(0,180,\\fscx110\\fscy110)\\t(180,320,\\fscx100\\fscy100)\\fad(0,250)}}{teks.upper()}")
    if j == "serif":
        kata = teks.split()
        if len(kata) >= 2:  # kata kedua miring, seperti majalah
            kata[1] = "{\\i1}" + kata[1] + "{\\i0}"
        uk = max(min(int(2600 / max(len(teks), 1)), 104), 58)
        return (f"Dialogue: 2,{t(0)},{t(sl)},JudulSerif,,0,0,0,,{{\\an5\\move(540,890,540,840,0,350)\\fs{uk}\\fad(250,300)}}"
                + " ".join(kata))
    if j == "kotak":
        return (f"Dialogue: 2,{t(0)},{t(sl)},JudulKotak,,0,0,0,,{{\\an5\\pos(540,840)\\fscx80\\fscy80\\t(0,150,\\fscx100\\fscy100)"
                f"\\fad(0,250)}}{teks.upper()}")
    if j == "sobek":  # teks di atas pita kertas (anim/sobek): masuk 0,3 dtk, tahan sampai akhir
        uk = max(min(int(1500 / max(len(teks), 1)), 92), 48)
        return (f"Dialogue: 2,{t(0.3)},{t(sl)},JudulSobek,,0,0,0,,{{\\an5\\pos(540,880)\\frz3\\fs{uk}\\fad(120,250)}}"
                f"{teks.upper()}")
    return f"Dialogue: 2,{t(0)},{t(sl)},Judul,,0,0,0,,{{\\fad(150,250)}}{teks}"


def _norm(t: str) -> str:
    return re.sub(r"[^\w]", "", t.lower())


KATA_UMUM = set("yang dengan untuk karena tetapi kemudian sebenarnya mereka sendiri seperti bagaimana apakah sesuatu memang begitu "
                "akhirnya ternyata pokoknya soalnya makanya sebelumnya sesudahnya biasanya because really actually something".split())


def kunci_klip(kata: list, klip: Klip) -> set:
    """Kata kunci dari AI; kalau tidak ada (mode Lokal), pilih kata panjang/angka ±1 per 6 kata."""
    if klip.kata_kunci:
        return {_norm(w) for x in klip.kata_kunci for w in str(x).split()
                if (len(_norm(w)) >= 3 or _norm(w).isdigit()) and _norm(w) not in KATA_UMUM | {"sih", "dong", "deh", "nih", "kok", "yang"}}
    hasil = set()
    for i in range(0, len(kata), 6):
        calon = [_norm(k.teks) for k in kata[i:i + 6]]
        calon = [c for c in calon if (any(ch.isdigit() for ch in c) or len(c) >= 7) and c not in KATA_UMUM]
        if calon:
            hasil.add(max(calon, key=lambda c: (any(ch.isdigit() for ch in c), len(c))))
    return hasil


HIJAU = warna_ass("#3DFF8A")

EMOJI = [  # kata (awalan) → emoji, sama dengan aplikasi Klip HP; gambar Twemoji di folder emoji/
    ("uang|duit|gaji|kaya|cuan|bisnis|jual|untung", "1f4b0"), ("cinta|sayang|hati|nikah|istri|suami", "2764"),
    ("api|panas|viral|hebat|keren", "1f525"), ("ide|pikir|otak|ilmu|belajar|paham", "1f4a1"),
    ("waktu|jam|cepat|lambat|telat", "23f0"), ("rahasia|diam|bisik", "1f92b"), ("penting|bahaya|awas|hati-hati", "26a0"),
    ("salah|jangan|dilarang|gagal", "274c"), ("benar|betul|berhasil|sukses|bisa", "2705"), ("lucu|ketawa|tertawa|ngakak", "1f602"),
    ("ternyata|kaget|gila|parah|serius", "1f631"), ("allah|tuhan|doa|sholat|salat|ibadah|quran|alquran|nabi|islam", "1f932"),
    ("makan|lapar|masak|kopi", "1f37d"), ("kerja|kantor|karier|karir", "1f4bc"), ("sehat|olahraga|kuat|otot", "1f4aa"),
    ("uji|tes|soal|sekolah|kuliah|buku", "1f4da"), ("rumah|keluarga|anak|ibu|ayah|bapak", "1f3e0"),
    ("hp|handphone|aplikasi|internet|ai", "1f4f1"), ("mati|meninggal|takut|seram|hantu|jin|setan|iblis", "1f47b"),
    ("mahal|murah|harga", "1f3f7"),
]
EMOJI_RE = [(re.compile(f"^({pola})"), kode) for pola, kode in EMOJI]
EMOJI_DIR = Path(__file__).resolve().parent / "emoji"


def emoji_untuk(w: str) -> str | None:
    b = re.sub(r"[^a-z\-]", "", w.lower())
    return next((kode for pola, kode in EMOJI_RE if b and pola.match(b)), None)


def rencana_emoji(kal: list[Kalimat], klip: Klip, per: int) -> list[tuple[float, float, str]]:
    """(mulai, selesai, kode) relatif klip: tiap grup subtitle yang berisi kata ber-emoji."""
    kata = [k for s in kal for k in s.kata if k.selesai > klip.mulai and k.mulai < klip.selesai]
    out = []
    for i in range(0, len(kata), per):
        grup = kata[i:i + per]
        kode = next((e for e in (emoji_untuk(x.teks) for x in grup) if e), None)
        if kode and (EMOJI_DIR / f"{kode}.png").exists():
            out.append((max(grup[0].mulai - klip.mulai, 0), grup[-1].selesai - klip.mulai, kode))
    return out


def tulis_ass(kal: list[Kalimat], klip: Klip, out: Path, g: dict, bar_atas: int) -> None:
    c = gaya_akhir(g)
    font, uk, mode = c["font"], c["uk"], c["mode"]
    sorot = warna_ass(c["warna"])
    putih = "&H00FFFFFF"
    # posisi_y = persen dari atas → MarginV untuk perataan bawah
    marg = int(1920 * (1 - float(g.get("posisi_y", 72)) / 100))
    spasi = c.get("spasi", 0)
    if c.get("kotak"):  # BorderStyle 3: kotak memakai OutlineColour
        utama = (f"Style: Utama,{font},{uk},{sorot if mode == 'terbaca' else putih},{putih},{c['kotak']},{c['kotak']},"
                 f"{c['tebal']},0,0,0,100,100,{spasi},0,3,{c['tepi']},0,2,90,90,{marg},1")
    elif mode == "karaoke":  # Primary = sudah terisi, Secondary = belum
        utama = f"Style: Utama,{font},{uk},{sorot},{putih},&H00000000,&H64000000,{c['tebal']},0,0,0,100,100,0,0,1,{c['tepi']},{c['bayang']},2,90,90,{marg},1"
    else:
        bayang = "&H78000000" if c["bayang"] else "&H64000000"
        utama = (f"Style: Utama,{font},{uk},{putih},{putih},&H00000000,{bayang},{c['tebal']},0,0,0,100,100,{spasi},0,1,"
                 f"{c['tepi']},{c['bayang']},2,90,90,{marg},1")
    banner_v = max(70, bar_atas // 2 - 70) if bar_atas > 160 else 150
    bw = warna_ass(c.get("banner_warna", "#FFFFFF"))
    fb, tb = (c["font_aktif"], 1) if c.get("font_aktif") else (font, c["tebal"])  # banner selalu tebal
    # banner_tengah=True -> ASS alignment 5 (tepat tengah frame), MarginV 0.
    # Default lama: alignment 8 (tengah atas) dengan margin banner_v.
    b_tengah = bool(g.get("banner_tengah"))
    b_align = 5 if b_tengah else 8
    b_margin = 0 if b_tengah else banner_v
    gb = g.get("_gaya_banner_obj")
    if gb:
        # Gaya banner pilihan: teks berwarna di atas KOTAK opaque (BorderStyle=3).
        # PrimaryColour = warna teks, OutlineColour = warna kotak.
        banner = (f"Style: Banner,{gb['font']},{gb['ukuran']},"
                  f"{warna_ass(gb['warna'])},{warna_ass(gb['warna'])},"
                  f"{warna_ass(gb['kotak'])},{warna_ass(gb['kotak'])},"
                  f"0,0,0,0,100,100,0,0,3,18,{gb.get('bayang', 0)},{b_align},80,80,{b_margin},1")
    elif c.get("banner_kotak"):
        banner = f"Style: Banner,{fb},{int(uk * 0.72)},{bw},{bw},{c['banner_kotak']},{c['banner_kotak']},{tb},0,0,0,100,100,0,0,3,18,0,{b_align},80,80,{b_margin},1"
    else:
        banner = f"Style: Banner,{fb},{max(int(uk * 0.85), 54)},{bw},{bw},&H00000000,&H00000000,{tb},0,0,0,100,100,0,0,1,5,0,{b_align},80,80,{b_margin},1"
    judul_style = (f"Style: Judul,{fb},54,&H000D0705,&H000D0705,{warna_ass('#FFD400')},{warna_ass('#FFD400')},1,0,0,0,100,100,0,0,3,"
                   f"20,0,8,110,110,{int(1920 * 0.14)},1")
    judul_style += (
        f"\nStyle: JudulNeon,Bangers,110,{warna_ass('#FF4FA3')},{warna_ass('#FF4FA3')},&H00111111,{warna_ass('#C6FF3D')},0,0,0,0,"
        f"100,100,2,0,1,10,8,5,70,70,0,1"
        f"\nStyle: JudulSerif,Georgia,104,&H00FFFFFF,&H00FFFFFF,&H00000000,&H78000000,1,0,0,0,100,100,0,0,1,0,4,5,90,90,0,1"
        f"\nStyle: JudulKotak,Archivo Black,72,&H00FFFFFF,&H00FFFFFF,&H00111111,&H00111111,0,0,0,0,100,100,0,0,3,22,0,5,100,100,0,1"
        f"\nStyle: JudulSobek,Archivo Black,84,&H00111111,&H00111111,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,120,120,0,1")
    # watermark: di tengah frame, putih transparan ±50% (&H80), tanpa margin
    tanda_style = "Style: Tanda,Montserrat,54,&H80FFFFFF,&H80FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,6,0,1,0,3,5,0,0,0,1"
    akun_style = f"Style: Akun,{font},34,&H40FFFFFF,&H40FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,1,0,1,2,0,8,80,80,{banner_v + int(uk * 1.1)},1"
    kepala = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{utama}
{banner}
{akun_style}
{judul_style}
{tanda_style}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    a, b = klip.mulai, klip.selesai
    baris = []
    bersih = lambda t: t.replace("{", "").replace("}", "")  # noqa: E731
    if g.get("banner", False) and klip.judul:
        teks = bersih(f"{g.get('awalan', '')}{klip.judul}{g.get('akhiran', '')}")
        # banner_durasi > 0 -> banner hanya tampil N detik pertama (mis. 5 dtk)
        b_dur = float(g.get("banner_durasi", 0) or 0)
        b_akhir = min(b_dur, b - a) if b_dur > 0 else (b - a)
        gb2 = g.get("_gaya_banner_obj") or {}
        baris.append(f"Dialogue: 1,{waktu_ass(0)},{waktu_ass(b_akhir)},Banner,,0,0,0,,"
                     f"{ubah_huruf(teks, 'kapital' if gb2.get('kapital', True) else 'biasa')}")
    elif g.get("judul_buka", True) and klip.judul:  # judul pembuka 3 dtk (bila banner tidak dipakai)
        teks = bersih(tanpa_emoji(klip.judul))
        baris.append(baris_judul(teks, c, b - a))
    if c.get("watermark"):
        baris.append(f"Dialogue: 2,{waktu_ass(0)},{waktu_ass(b - a)},Tanda,,0,0,0,,{bersih(tanpa_emoji(str(c['watermark'])))[:40]}")
    if c.get("akun"):
        baris.append(f"Dialogue: 1,{waktu_ass(0)},{waktu_ass(b - a)},Akun,,0,0,0,,{bersih(str(c['akun']))[:40]}")
    if g.get("subtitle", True):
        kata = [k for s in kal for k in s.kata if k.selesai > a and k.mulai < b]
        kunci = kunci_klip(kata, klip)
        per = c["per"]
        huruf = c.get("huruf", "kapital")
        for i in range(0, len(kata), per):
            grup = kata[i:i + per]
            teks = [bersih(ubah_huruf(x.teks, huruf)) for x in grup]
            if mode == "karaoke":
                isi = []
                for j, x in enumerate(grup):
                    dur = ((grup[j + 1].mulai if j + 1 < len(grup) else x.selesai) - x.mulai)
                    isi.append("{\\kf" + str(max(int(dur * 100), 1)) + "}" + teks[j])
                if grup[-1].selesai - grup[0].mulai >= 0.02:
                    baris.append(f"Dialogue: 0,{waktu_ass(grup[0].mulai - a)},{waktu_ass(grup[-1].selesai - a)},Utama,,0,0,0,,{' '.join(isi)}")
                continue
            for j, aktif in enumerate(grup):
                m = aktif.mulai - a
                sl = (grup[j + 1].mulai if j + 1 < len(grup) else grup[-1].selesai) - a
                if sl - m < 0.02:  # baris berdurasi nol membuat libass menghilangkan judul pembuka → lewati
                    continue
                isi = []
                for x, t in zip(grup, teks):
                    kk = _norm(x.teks) in kunci
                    hijau = "{\\c" + HIJAU + "&}" + t + "{\\r}" if kk else t  # kata kunci = hijau
                    if mode == "polos":
                        isi.append(hijau)
                    elif mode == "tebal":
                        isi.append(("{\\fn" + c["font_aktif"] + "\\b1}" if c.get("font_aktif") else "{\\b1}") + t + "{\\r}"
                                   if x is aktif else t)
                    elif mode == "terbaca":
                        isi.append("{\\c" + putih + "&}" + t + "{\\r}" if x is aktif else hijau)
                    elif mode == "kotak":  # kotak warna di belakang kata aktif (tepi tebal sewarna = blok), teks gelap
                        isi.append("{\\c&H00111111&\\3c" + sorot + "&\\bord18\\shad0\\fscx104\\fscy104}" + t + "{\\r}"
                                   if x is aktif else hijau)
                    elif mode in ("pop", "komik"):
                        warna = "{\\c" + HIJAU + "&}" if kk else ""
                        if x is aktif:
                            skala = "125" if mode == "komik" else "110"
                            isi.append("{" + warna.strip("{}") + "\\fscx" + skala + "\\fscy" + skala +
                                       "\\t(0,110,\\fscx106\\fscy106)}" + t + "{\\r}")
                        else:
                            isi.append(warna + t + ("{\\r}" if warna else ""))
                    else:  # warna
                        isi.append("{\\c" + sorot + "&\\fscx110\\fscy110}" + t + "{\\r}" if x is aktif else hijau)
                awal = "{\\fscx70\\fscy70\\t(0,120,\\fscx100\\fscy100)}" if mode == "pop" and j == 0 else ""
                baris.append(f"Dialogue: 0,{waktu_ass(m)},{waktu_ass(sl)},Utama,,0,0,0,,{awal}{' '.join(isi)}")
    out.write_text(kepala + "\n".join(baris) + "\n", encoding="utf-8")


def detik_kunci(kal: list[Kalimat], klip: Klip) -> list[float]:
    """Detik (relatif klip) kata pemikat (hook) — atau kata kunci bila tidak ada — untuk zoom halus. Jarak ≥ 3 dtk, maks 8."""
    kata = [k for s in kal for k in s.kata if k.selesai > klip.mulai and k.mulai < klip.selesai]
    calon = [k for k in kata if is_hook(k.teks)]
    if not calon:
        kunci = kunci_klip(kata, klip)
        calon = [k for k in kata if _norm(k.teks) in kunci]
    hasil: list[float] = []
    for k in calon:
        if not hasil or k.mulai - klip.mulai - hasil[-1] >= 3:
            hasil.append(max(k.mulai - klip.mulai, 0))
    return hasil[:8]


# ── 6b. B-roll: file sendiri atau Pixabay (kunci API milik pengguna) ──────────
STOP_BROLL = set("""yang dan di ke dari ini itu dengan untuk pada adalah akan juga tidak nggak gak enggak kita kami kamu saya aku dia
mereka anda ada sudah udah belum bisa lagi kalau kalo karena jadi atau tapi tetapi seperti kayak banyak sangat banget sekali lebih
paling semua setiap masih harus mau ingin pernah sama begitu gitu begini gini terus lalu kemudian sih dong kok nah ya iya oke aja
saja memang emang sebenarnya mungkin kenapa gimana bagaimana apa siapa mana kapan orang hal cara waktu sesuatu namanya tadi nanti
sekarang dulu the and that this with for you""".split())

# Kamus kata benda konkret (Indonesia → kueri Inggris), sama dengan aplikasi Klip HP. Kata di luar kamus tidak diberi B-roll stok.
KAMUS_BROLL = {
    "jin": "dark smoke mystery", "setan": "dark shadow horror", "hantu": "ghost dark night", "iblis": "fire darkness",
    "malaikat": "heavenly light clouds", "masjid": "mosque", "doa": "praying hands", "sholat": "muslim prayer",
    "salat": "muslim prayer", "quran": "quran reading", "alquran": "quran reading", "allah": "sky light clouds",
    "surga": "paradise nature", "neraka": "fire flames", "langit": "sky clouds", "bintang": "night stars", "bulan": "moon night",
    "matahari": "sunrise", "hujan": "rain", "laut": "ocean waves", "gunung": "mountains", "hutan": "forest", "pantai": "beach",
    "kota": "city traffic", "jalan": "street walking", "malam": "city night", "uang": "money cash", "duit": "money cash",
    "gaji": "salary money", "bisnis": "business meeting", "kantor": "office work", "kerja": "working laptop", "toko": "small shop",
    "mobil": "car driving", "motor": "motorcycle", "pesawat": "airplane", "kereta": "train", "rumah": "house", "keluarga": "family",
    "anak": "children playing", "ibu": "mother", "ayah": "father", "istri": "wife couple", "suami": "husband couple",
    "cewek": "woman", "perempuan": "woman", "wanita": "woman", "pacar": "couple love", "cowok": "man", "laki": "man",
    "nikah": "wedding", "pernikahan": "wedding", "cinta": "love couple", "hati": "heart", "sekolah": "school",
    "kuliah": "university students", "buku": "books reading", "belajar": "studying", "guru": "teacher", "dokter": "doctor",
    "rumahsakit": "hospital", "sakit": "sick person", "makan": "eating food", "makanan": "food", "kopi": "coffee",
    "hp": "smartphone", "handphone": "smartphone", "internet": "internet technology", "komputer": "computer",
    "ai": "artificial intelligence", "robot": "robot", "olahraga": "workout", "lari": "running", "sepakbola": "football",
    "bola": "football", "musik": "music", "api": "fire", "air": "water", "waktu": "clock time", "jam": "clock",
    "tidur": "sleeping", "mimpi": "dream surreal", "takut": "fear dark", "marah": "angry", "sedih": "sad rain",
    "senang": "happy people", "tertawa": "laughing", "perang": "war", "dunia": "earth globe", "negara": "flag",
    "indonesia": "indonesia", "jakarta": "jakarta", "pasar": "market", "petani": "farmer", "sawah": "rice field",
}
GAMBAR = (".jpg", ".jpeg", ".png", ".webp")


def rencana_broll(kata: list[Kata], mulai: float, durasi: float, lama: float = 2.4, jarak: float = 7.0,
                  kamus: bool = False) -> list[tuple[float, str]]:
    """Titik sisip tiap ±8 dtk (setelah 4 dtk pertama, supaya pembicara tetap jadi pembuka) → [(detik relatif, kueri)]."""
    bersih = lambda w: re.sub(r"[^a-z]", "", w.lower())  # noqa: E731
    out, t, dipakai = [], 4.0, set()
    while t + lama < durasi - 1.5:
        jendela = [(bersih(k.teks), k.mulai - mulai) for k in kata if t - 0.5 <= k.mulai - mulai < t + lama + 2.0]
        if kamus:
            calon = next(((w, KAMUS_BROLL[w], tk) for w, tk in jendela if w in KAMUS_BROLL and w not in dipakai), None)
        else:
            cocok = [(w, tk) for w, tk in jendela if len(w) >= 4 and w not in STOP_BROLL and w not in dipakai]
            calon = (lambda x: (x[0], x[0], x[1]))(max(cocok, key=lambda x: len(x[0]))) if cocok else None
        if calon and calon[2] + lama < durasi - 0.5:
            dipakai.add(calon[0])
            out.append((max(calon[2], 0.0), calon[1]))
            t = calon[2] + lama + jarak
        else:
            t += 1.5
    return out


def cache_pixabay() -> Path:
    d = Path.home() / ".studio-isanovski" / "pixabay"
    d.mkdir(parents=True, exist_ok=True)
    batas = time.time() - 24 * 3600  # aturan Pixabay: cache maksimal 24 jam
    for f in d.iterdir():
        if f.stat().st_mtime < batas:
            f.unlink(missing_ok=True)
    return d


def cari_pixabay(kunci: str, q: str, cache: Path) -> tuple[int, str] | None:
    import urllib.error
    import urllib.parse
    import urllib.request
    cj = cache / ("q_" + re.sub(r"[^0-9A-Za-z]", "", q) + ".json")
    if cj.exists():
        teks = cj.read_text(encoding="utf-8")
    else:
        url = ("https://pixabay.com/api/videos/?" + urllib.parse.urlencode(
            {"key": kunci, "q": q, "lang": "en", "video_type": "film", "safesearch": "true", "per_page": 10}))
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                teks = r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code in (400, 401, 403):
                sys.exit("API key Pixabay ditolak. Periksa lagi kuncinya di Pengaturan.")
            if e.code == 429:
                log("Batas permintaan Pixabay tercapai, B-roll dilewati.")
            return None
        except OSError:
            return None
        cj.write_text(teks, encoding="utf-8")
    for h in json.loads(teks).get("hits", []):
        if (h.get("duration") or 0) < 3 or h.get("type") == "animation":
            continue
        v = h.get("videos") or {}
        pilih = next((v[k]["url"] for k in ("medium", "small", "large") if v.get(k, {}).get("url")), None)
        if pilih:
            return int(h["id"]), pilih
    return None


def siapkan_broll(g: dict, kal: list[Kalimat], klip: Klip) -> tuple[list[dict], str]:
    """Kembalikan (sisipan, kredit). g["broll"] = "pixabay" atau "file"; g["broll_file"] = daftar path."""
    jenis = g.get("broll")
    if not jenis:
        return [], ""
    lama = float(g.get("broll_lama", 2.4))
    durasi = klip.selesai - klip.mulai
    kata = [k for s in kal for k in s.kata if k.selesai > klip.mulai and k.mulai < klip.selesai]
    if jenis == "file":
        files = [f for f in (g.get("broll_file") or []) if Path(f).exists()]
        if not files:
            return [], ""
        rencana = rencana_broll(kata, klip.mulai, durasi, lama)
        return [{"a": t, "b": t + lama, "file": str(Path(files[i % len(files)]).resolve()), "kunci": q,
                 "gambar": Path(files[i % len(files)]).suffix.lower() in GAMBAR} for i, (t, q) in enumerate(rencana)], ""
    kunci = g.get("pixabay_key") or baca_env().get("PIXABAY_API_KEY")
    if not kunci:
        log("B-roll Pixabay dilewati: isi API key Pixabay dulu (gratis di pixabay.com/api/docs).")
        return [], ""
    import urllib.request
    cache = cache_pixabay()
    hasil: list[dict] = []
    rencana = rencana_broll(kata, klip.mulai, durasi, lama, kamus=True)
    for i, (t, q) in enumerate(rencana, 1):
        log(f"Mencari B-roll “{q}” di Pixabay ({i}/{len(rencana)})…")
        ketemu = cari_pixabay(kunci, q, cache)
        if not ketemu:
            continue
        vid, link = ketemu
        f = cache / f"pixabay_{vid}.mp4"
        if not f.exists() or f.stat().st_size < 10_000:
            try:
                with urllib.request.urlopen(link, timeout=30) as r, open(f, "wb") as out:
                    out.write(r.read())
            except OSError:
                f.unlink(missing_ok=True)
                continue
        if all(h["file"] != str(f) for h in hasil):
            hasil.append({"a": t, "b": t + lama, "file": str(f), "kunci": q, "gambar": False})
    return hasil, ("Video dari Pixabay" if hasil else "")


# ── 7. Render satu klip dengan gaya ─────────────────────────────────────────
RASIO = {"9:16": 9 / 16, "1:1": 1.0, "4:3": 4 / 3, "16:9": 16 / 9}
FOKUS = {"kiri": 0.35, "tengah": 0.5, "kanan": 0.65}


def _pip_dari_bingkai(fr, sisi: str, model: Path) -> tuple[list[int], dict] | None:
    """Kotak PiP 16:9 yang PERSIS di dalam bingkai PiP, dari satu frame.

    Dipandu kotak wajah: gradien Sobel hanya diukur pada pita yang dilalui
    wajah, sehingga tepi konten gameplay tidak ikut terpilih. PiP pojok
    menempel pada 2 tepi gambar, jadi hanya 2 tepi dalam yang perlu dicari:
      sisi kanan -> tepi KIRI + ATAS ; sisi kiri -> tepi KANAN + ATAS.
    """
    import cv2
    import numpy as np

    h, w = fr.shape[:2]
    sk = 640 / w
    kecil = cv2.resize(fr, (640, max(2, int(h * sk))))
    det = cv2.FaceDetectorYN.create(str(model), "", (kecil.shape[1], kecil.shape[0]), 0.6, 0.3, 50)
    _, ws = det.detect(kecil)
    if ws is None or not len(ws):
        return None
    b = max(ws, key=lambda a: a[2] * a[3])
    fx, fy, fw, fh = (float(v) / sk for v in b[:4])
    f = {"x": fx, "y": fy, "w": fw, "h": fh, "cx": fx + fw / 2, "cy": fy + fh / 2}

    abu = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
    gx = np.abs(cv2.Sobel(abu, cv2.CV_32F, 1, 0, ksize=3))
    gy = np.abs(cv2.Sobel(abu, cv2.CV_32F, 0, 1, ksize=3))
    y0, y1 = int(fy), int(fy + fh)
    x0, x1 = int(fx), int(fx + fw)
    if y1 - y0 < 4 or x1 - x0 < 4:
        return None

    # Tepi ATAS: pita horizontal sejajar wajah, cari ke atas dari wajah
    prof_atas = np.convolve(gy[:, x0:x1].mean(axis=1), np.ones(5) / 5, mode="same")
    ymin = max(0, int(fy - 2 * fh))
    kan = prof_atas[ymin:y0]
    atas = ymin + int(np.argmax(kan)) if len(kan) else max(0, int(fy - fh))

    # Tepi DALAM: pita vertikal sejajar wajah
    prof_sisi = np.convolve(gx[y0:y1, :].mean(axis=0), np.ones(5) / 5, mode="same")
    if sisi == "kanan":
        xmin = max(0, int(fx - 3 * fw))
        kan = prof_sisi[xmin:x0]
        dalam = xmin + int(np.argmax(kan)) if len(kan) else int(fx - fw)
        pip = [dalam, atas, w - dalam, h - atas]
    else:
        xmax = min(w, int(fx + fw + 3 * fw))
        kan = prof_sisi[x1:xmax]
        dalam = x1 + int(np.argmax(kan)) if len(kan) else int(fx + 2 * fw)
        pip = [0, atas, dalam, h - atas]

    px, py, pw, ph = pip
    if pw < 40 or ph < 30:
        return None

    # Kotak 16:9 DI DALAM PiP (nol bleed), dipusatkan pada wajah
    cw = float(pw)
    ch = cw * 9 / 16
    if ch > ph:
        ch = float(ph)
        cw = ch * 16 / 9
    x = max(px, min(f["cx"] - cw / 2, px + pw - cw))
    y = max(py, min(f["cy"] - ch / 2, py + ph - ch))
    return [int(round(x)), int(round(y)), int(round(cw)), int(round(ch))], f


def deteksi_kotak_pip(file: Path, a: float, b: float, sisi: str) -> list[int] | None:
    """Kotak crop PiP presisi [x, y, lebar, tinggi] dalam piksel sumber.

    Menggantikan tebakan proporsional (`kotak_facecam`) yang selalu kebesaran
    dan menyeret gameplay ke dalam band facecam. Sampel 3 frame, ambil median
    per komponen supaya tahan outlier. None kalau wajah tidak ketemu.
    """
    import cv2

    model = Path(__file__).resolve().parent / "model" / "face_detection_yunet_2023mar.onnx"
    if not model.exists() or not hasattr(cv2, "FaceDetectorYN"):
        return None
    cap = cv2.VideoCapture(str(file))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if not w or not h:
        cap.release()
        return None
    hasil = []
    for t in (a + (b - a) * 0.25, a + (b - a) * 0.5, a + (b - a) * 0.75):
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, fr = cap.read()
        if not ok:
            continue
        r = _pip_dari_bingkai(fr, sisi, model)
        if r:
            hasil.append(r[0])
    cap.release()
    if not hasil:
        return None
    return [int(sorted(c)[len(c) // 2]) for c in zip(*hasil)]


def deteksi_sisi_facecam(kunci: list[tuple[float, float]], ambang: float = 0.5) -> str:
    """Tentukan sisi PiP facecam dari jejak wajah.

    Jejak wajah = daftar (detik, posisi-x 0..1) wajah pembicara aktif.
    PiP di pojok KANAN -> wajah Ada di kanan (x > 0.5); pojok KIRI -> x < 0.5.
    Pakai median, bukan rata-rata, supaya satu frame outlier tidak mengubah
    keputusan.
    """
    xs = sorted(float(x) for _, x in kunci if x is not None)
    if not xs:
        return "kanan"
    return "kanan" if xs[len(xs) // 2] >= ambang else "kiri"


def kotak_facecam(w: int, h: int, sisi: str, preset: float = 0.26,
                  x_wajah: float | None = None) -> tuple[int, int, int, int]:
    """Kotak crop PiP facecam di file sumber (rasio 16:9), pojok bawah.

    Lebar = `preset` × lebar sumber (default 26%). Kotak di-anchor ke pojok
    sesuai `sisi`. Kalau posisi-x wajah hasil deteksi diketahui, kotak digeser
    60% ke arah wajah (40% tetap di pojok) supaya wajah tidak keluar dari frame.
    """
    cw = max(64, int(w * preset) // 2 * 2)
    ch = max(36, int(round(cw * 9 / 16)) // 2 * 2)
    if ch > h:
        ch = h // 2 * 2
        cw = max(64, int(round(ch * 16 / 9)) // 2 * 2)
    x = 0 if sisi == "kiri" else w - cw
    # Koreksi posisi HANYA kalau wajah terdeteksi di sisi yang sama dengan PiP.
    # x_wajah ~ 0.5 = deteksi gagal/netral -> JANGAN dipakai, karena akan menarik
    # kotak ke tengah dan keluar dari PiP. Geseran juga dibatasi 25% lebar sumber
    # supaya kotak tidak pernah kabur jauh dari pojok.
    if x_wajah is not None:
        cocok = (sisi == "kanan" and x_wajah > 0.55) or (sisi == "kiri" and x_wajah < 0.45)
        if cocok:
            baru = int(float(x_wajah) * w) - cw // 2
            baru = max(0, min(baru, w - cw))
            batas = int(w * 0.25)
            x = max(x - batas, min(int((x * 0.4 + baru * 0.6) // 2 * 2), x + batas))
            x = max(0, min(x, w - cw))
    return cw, ch, x, h - ch


def cari_berkas_branding(g: dict) -> Path | None:
    """Berkas gambar bar branding gamer (idealnya 1080x320).

    Urutan: gaya render -> aset user (~/Isanovski Studio/aset/branding.png)
    -> bawaan repo (klip/aset/branding.png). Gambar dipakai UTUH, ruang kosong
    di dalamnya dibiarkan supaya owner bisa isi sendiri.
    """
    for nilai in (g.get("branding"), g.get("logo")):
        if nilai and Path(nilai).is_file():
            return Path(nilai)
    for p in (Path.home() / "Isanovski Studio" / "aset" / "branding.png",
              Path(__file__).resolve().parent / "aset" / "branding.png"):
        if p.is_file():
            return p
    return None


def render(file: Path, klip: Klip, kal: list[Kalimat], out: Path, kerja: Path, w: int, h: int, g: dict) -> None:
    rasio = g.get("rasio", "9:16")
    layout = g.get("layout", "tunggal")
    fokus = g.get("fokus", "auto")
    dua = dua_wajah(file, klip.mulai, klip.selesai, w, h) if layout == "split" else None
    if layout == "split" and not dua:
        log("   Split Podcast: hanya satu orang terlihat → bingkai tunggal")
    cx = FOKUS.get(fokus, 0.5)
    if fokus == "manual" and g.get("face_x") is not None:
        cx = float(g["face_x"])
    durasi = klip.selesai - klip.mulai
    graf = []
    bar_atas = 0
    masukan_extra: list[str] = []
    n_in = 1  # input 0 = video sumber

    if layout == "split" and dua:
        # dua pembicara ditumpuk: kiri di atas, kanan di bawah, garis pemisah tipis
        graf.append("[0:v]split=2[va][vb]")
        for lbl, p in (("atas", dua[0]), ("bawah", dua[1])):
            zoom = min(max(p["s"] * 3.0, 0.3), 1.0)
            graf.append(f"[{'va' if lbl == 'atas' else 'vb'}]{potong(w, h, 1080 / 958, p['x'], p['y'], zoom)},"
                        f"scale=1080:958:flags=lanczos,setsar=1[{lbl}]")
        graf.append("color=c=0x111111:s=1080x4:d=1[gp];[atas][gp][bawah]vstack=inputs=3[vid]")
    elif layout == "lebar":
        # Landscape utuh tanpa crop — video di tengah kanvas 1080x1920,
        # black bars atas-bawah (pillarbox). Cocok untuk klip gaming/YouTube
        # yang ingin jaga 16:9 asli, hanya dipotong momennya saja.
        graf.append(f"color=c=black:s=1080x1920:d={durasi:.2f}[bg]")
        src_ratio = w / h if h else 16 / 9
        land_w = 1080
        land_h = max(2, int(1080 / src_ratio) // 2 * 2)
        land_y = (1920 - land_h) // 2
        graf.append(f"[0:v]scale={land_w}:{land_h}:flags=lanczos,setsar=1[v_land]")
        graf.append(f"[bg][v_land]overlay=x=0:y={land_y}[vid]")
        print(f"• Layout lebar: {w}x{h} → {land_w}x{land_h} di y={land_y} (black bars atas-bawah)")
    elif layout == "gamer":
        # Kanvas 1080x1920 (UKURAN TERKUNCI 20 Nov 2026):
        #   facecam  1080x608  (LEBAR PENUH — nol bolong kiri-kanan)
        #   gameplay 1080x992  (di bawah facecam)
        #   branding 1080x320  (bar paling bawah: logo + nama channel)
        brand_h = int(g.get("brand_h", 320))     # tinggi bar branding (0 = mati)
        zoom = float(g.get("game_zoom", 1.0))    # >1 = perbesar gameplay (potong makin banyak kiri-kanan)
        fc_w = 1080                              # lebar facecam = lebar kanvas (penuh)
        # Tinggi slot facecam MENGIKUTI rasio PiP sumber (default) supaya tidak ada
        # gambar yang terpotong. Kalau slot dipaksa 16:9 sedangkan PiP kotak/4:3,
        # 44% gambar facecam terbuang. fc_rasio="16:9" mengembalikan perilaku lama.
        # DEFAULT = slot TETAP (keputusan user): facecam 1080x608, gameplay 1080x992,
        # branding 1080x320. fc_rasio="sumber" hanya kalau user ingin tinggi slot
        # mengikuti rasio PiP (opsional, bukan bawaan).
        ikut_sumber = str(g.get("fc_rasio", "16:9") or "16:9") == "sumber"
        fc_h = int(g.get("fc_h", 608))           # dipakai hanya bila fc_rasio != sumber
        game_h = int(g.get("game_h", 992))
        # Layout gamer: subtitle + banner diaktifkan (preset random di bawah)
        # Tidak dipaksa mati lagi.

        if g.get("facecam"):
            # Dua file: facecam terpisah + gameplay (OPSIONAL — satu file juga bisa)
            if ikut_sumber:
                _, fw, fh = info_video(Path(g["facecam"]))
                if fw and fh:
                    fc_h = max(200, min(1100, int(round(fc_w * fh / fw)) // 2 * 2))
            game_h = max(200, 1920 - fc_h - brand_h)
            if ikut_sumber:
                # Rasio slot == rasio sumber → skala saja, TIDAK ada yang terpotong
                graf.append(f"[FACECAM:v]scale={fc_w}:{fc_h}:flags=lanczos,setsar=1[fc]")
            else:
                graf.append(f"[FACECAM:v]scale={fc_w}:{fc_h}:force_original_aspect_ratio=increase,"
                            f"crop={fc_w}:{fc_h},setsar=1[fc]")
            print(f"• Layout gamer: facecam {fc_w}x{fc_h} · gameplay {fc_w}x{game_h} · branding {fc_w}x{brand_h}")

            # Gameplay: skala memperbesar (tinggi penuh tetap utuh), lalu potong kiri-kanan
            graf.append(f"[0:v]scale=-1:{int(game_h * zoom)}:flags=lanczos,"
                        f"crop=w='min(iw\\,1080)':h='min(ih\\,{int(game_h * zoom)})':x='(iw-min(iw\\,1080))/2':y=0,"
                        f"scale=1080:{game_h}:flags=lanczos,setsar=1[game_scaled]")
        else:
            # SATU FILE: gameplay + PiP facecam di pojok bawah → facecam dipotong otomatis.
            # Tidak perlu file facecam terpisah.
            graf.append("[0:v]split=2[va][vb]")

            kunci = jejak_wajah(file, klip.mulai, klip.selesai, w, h) if is_installed() else []
            xs_wajah = sorted(float(x) for _, x in kunci if x is not None)
            x_wajah = xs_wajah[len(xs_wajah) // 2] if xs_wajah else None

            sisi = str(g.get("fc_sisi", "otomatis") or "otomatis")
            if sisi == "otomatis":
                sisi = deteksi_sisi_facecam(kunci)
            preset_fc = float(g.get("fc_preset", 0.26) or 0.26)

            # Kotak crop eksplisit dari UI (pratinjau visual) MENANG atas deteksi otomatis.
            # Format: [x, y, lebar, tinggi] dalam piksel file sumber.
            fc_crop = g.get("fc_crop")
            if fc_crop and len(fc_crop) == 4:
                x_src, y_src, cw_src, ch_src = (int(v) for v in fc_crop)
                x_src = max(0, min(x_src, w - 2))
                y_src = max(0, min(y_src, h - 2))
                cw_src = max(2, min(cw_src, w - x_src)) // 2 * 2
                ch_src = max(2, min(ch_src, h - y_src)) // 2 * 2
                print(f"• Facecam MANUAL: crop={cw_src}x{ch_src}+{x_src}+{y_src} dari sumber {w}x{h}")
            else:
                # Deteksi PRESISI batas PiP (nol bleed) — bukan tebakan proporsional.
                pip = deteksi_kotak_pip(file, klip.mulai, klip.selesai, sisi)
                if pip:
                    x_src, y_src, cw_src, ch_src = pip
                    print(f"• Facecam PiP PRESISI: sisi={sisi} crop={cw_src}x{ch_src}+{x_src}+{y_src} "
                          f"dari sumber {w}x{h} (kotak 16:9 di dalam PiP)")
                else:
                    cw_src, ch_src, x_src, y_src = kotak_facecam(w, h, sisi, preset_fc, x_wajah)
                    print(f"• Facecam otomatis (fallback): sisi={sisi} "
                          f"crop={cw_src}x{ch_src}+{x_src}+{y_src} dari sumber {w}x{h}")

            # Tinggi slot mengikuti rasio kotak PiP → TIDAK ada gambar yang terpotong
            if ikut_sumber:
                fc_h = max(200, min(1100, int(round(fc_w * ch_src / cw_src)) // 2 * 2))
            game_h = max(200, 1920 - fc_h - brand_h)
            print(f"• Layout gamer: facecam {fc_w}x{fc_h} (rasio {cw_src/ch_src:.3f}) · "
                  f"gameplay {fc_w}x{game_h} · branding {fc_w}x{brand_h}")

            # Facecam: crop kotak PiP → skala ke slot (rasio sama → utuh, tidak kepotong)
            graf.append(f"[va]crop={cw_src}:{ch_src}:{x_src}:{y_src},"
                        f"scale={fc_w}:{fc_h}:flags=lanczos,setsar=1[fc]")

            # Gameplay: crop area yang BERSIH dari PiP facecam (geser menjauh dari pojok PiP)
            sh_g = max(2, int(game_h * zoom))
            sw_g = max(2, int(round(w * sh_g / h)))
            crop_w = min(sw_g, fc_w)
            crop_h = min(sh_g, game_h)
            tengah = (sw_g - crop_w) // 2
            fc_kiri_s = int(x_src * sh_g / h)
            fc_kanan_s = int((x_src + cw_src) * sh_g / h)
            if sisi == "kanan" and fc_kiri_s - crop_w >= 0:
                x_game = min(tengah, fc_kiri_s - crop_w)      # geser ke kiri, PiP tidak ikut
            elif sisi == "kiri" and fc_kanan_s <= sw_g - crop_w:
                x_game = max(tengah, fc_kanan_s)               # geser ke kanan, PiP tidak ikut
            else:
                x_game = tengah                               # tidak bisa hindari → tengah
            print(f"• Gameplay crop: x={x_game} (dari {sw_g}px lebar, PiP di {'kanan' if sisi == 'kanan' else 'kiri'})")
            graf.append(f"[vb]scale=-1:{sh_g}:flags=lanczos,"
                        f"crop={crop_w}:{crop_h}:{x_game}:0,"
                        f"scale={fc_w}:{game_h}:flags=lanczos,setsar=1[game_scaled]")

        # Kanvas hitam → facecam (lebar penuh) → gameplay → bar branding
        graf.append(f"color=c=black:s=1080x1920:d={durasi:.2f}[bg]")
        graf.append(f"[bg][fc]overlay=x=0:y=0[t1]")
        graf.append(f"[t1][game_scaled]overlay=x=0:y={fc_h}[t2]")
        if brand_h > 0:
            aset_branding = cari_berkas_branding(g)
            if aset_branding:
                # Gambar branding milik user (idealnya 1080x320) dipakai UTUH —
                # ruang kosong di kanannya dibiarkan, isi sendiri.
                graf.append(f"[BRANDING:v]scale={fc_w}:{brand_h}:flags=lanczos,setsar=1[brg]")
            else:
                graf.append(f"color=c=0x121212:s={fc_w}x{brand_h}:d={durasi:.2f}[brg]")
            graf.append(f"[t2][brg]overlay=x=0:y={1920 - brand_h}[vid]")
        else:
            graf.append(f"[t2]null[vid]")

    elif rasio == "9:16":
        if fokus == "auto":
            # Smart face framing: ikuti wajah pembicara aktif per shot (dari framing.py)
            if is_installed():
                kunci = jejak_wajah(file, klip.mulai, klip.selesai, w, h)
                crop = potong_jejak(w, h, 9 / 16, kunci)
            else:
                log("   Face tracking: model YuNet belum siap → bingkai tengah")
                crop = potong(w, h, 9 / 16, cx)
        elif fokus == "manual":
            # User menentukan posisi wajah (0.0 kiri … 1.0 kanan)
            crop = potong(w, h, 9 / 16, cx)
        else:  # "fit" → layar penuh, tidak dipotong
            crop = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1"
        graf.append(f"[0:v]{crop},scale=1080:1920:flags=lanczos,setsar=1[vid]")
    else:
        r = RASIO.get(rasio, 1.0)
        ih = int(1080 / r) // 2 * 2
        bar_atas = (1920 - ih) // 2
        graf.append("[0:v]split=2[va][vb]")
        crop = potong_jejak(w, h, r, jejak_wajah(file, klip.mulai, klip.selesai, w, h)) if fokus == "auto" \
            else potong(w, h, r, cx)
        graf.append(f"[va]{crop},scale=1080:{ih}:flags=lanczos,setsar=1[isi]")
        if gaya_akhir(g).get("latar", "hitam") == "blur":
            graf.append(f"[vb]{potong(w, h, 9 / 16, 0.5)},scale=540:960,boxblur=20:2,scale=1080:1920,eq=brightness=-0.08,setsar=1[latar]")
        else:
            graf.append(f"[vb]scale=1080:1920,drawbox=c=black:t=fill,setsar=1[latar]")
        graf.append(f"[latar][isi]overlay=x=0:y={bar_atas}[vid]")

    c = gaya_akhir(g)
    v = "vid"
    # zoom punch-in singkat pada kata kunci (diabaikan untuk layout gamer — wajah + gameplay sudah cukup ramai)
    if c.get("zoom") and g.get("layout") != "gamer":
        tt = detik_kunci(kal, klip)
        if tt:
            import cv2
            cap = cv2.VideoCapture(str(file)); fps = cap.get(cv2.CAP_PROP_FPS) or 30; cap.release()
            # naik cepat 0,25 dtk lalu turun pelan 1,25 dtk ke 1,0 (maks 1,08)
            z = "+".join(f"if(between(it,{t - 0.1:.2f},{t + 0.15:.2f}),(it-{t - 0.1:.2f})/0.25,"
                         f"if(between(it,{t + 0.15:.2f},{t + 1.4:.2f}),1-(it-{t + 0.15:.2f})/1.25,0))" for t in tt)
            graf.append(f"[{v}]zoompan=z='1+0.08*min({z},1)':x='iw/2-(iw/zoom/2)':y='ih*0.4-(ih/zoom*0.4)':d=1:s=1080x1920:fps={fps:.3f}[vz]")
            v = "vz"
    # B-roll: zoom pelan 1,00→1,08 + sedikit digelapkan, menutupi video selama ±2,4 dtk
    for i, sp in enumerate(g.get("_sisipan") or []):
        lama = sp["b"] - sp["a"]
        if sp.get("gambar"):
            masukan_extra += ["-loop", "1", "-t", f"{lama:.2f}", "-i", sp["file"]]
        else:
            masukan_extra += ["-t", f"{lama:.2f}", "-i", sp["file"]]
        fr = int(lama * 30) + 1
        graf.append(f"[{n_in}:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30,"
                    f"zoompan=z='1+0.08*on/{fr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=30,"
                    f"eq=brightness=-0.10,format=yuv420p,setpts=PTS-STARTPTS+{sp['a']:.2f}/TB[br{i}]")
        graf.append(f"[{v}][br{i}]overlay=enable='between(t,{sp['a']:.2f},{sp['b']:.2f})':eof_action=pass[vb{i}]")
        v = f"vb{i}"
        n_in += 1

    def hiasan(nama: str, mulai: float, tahan: float = 0.0, beku: int | None = None) -> None:
        """Tempel animasi transparan anim/<nama>/NN.webp mulai detik `mulai`.

        `tahan` = berapa detik frame terakhir ditahan setelah animasi selesai.
        `beku` = pakai frame ke-`beku` sebagai frame terakhir (animasi yang ujungnya
        "keluar" layar, mis. pita sobek, jadi bisa ditahan saat pitanya masih penuh).
        """
        nonlocal v, n_in
        if not (ANIM_DIR / nama / "00.webp").exists():
            return
        masukan_extra.extend(["-framerate", "30", "-start_number", "0", "-i", str(ANIM_DIR / nama / "%02d.webp")])
        potong = f",trim=end_frame={beku},setpts=PTS-STARTPTS" if beku else ""
        tpad = f",tpad=stop_mode=clone:stop_duration={tahan:.2f}" if tahan > 0 else ""
        tunda = f",tpad=start_duration={mulai:.3f}:start_mode=add:color=black@0" if mulai > 0 else ""
        graf.append(f"[{n_in}:v]format=rgba,scale=1080:1920{potong}{tpad}{tunda},setpts=PTS-STARTPTS[an{n_in}]")
        graf.append(f"[{v}][an{n_in}]overlay=eof_action=pass[va{n_in}]")
        v = f"va{n_in}"
        n_in += 1

    # transisi sapuan menutupi setiap pergantian ke/dari B-roll (penuh tepat di titik potong)
    if g.get("transisi"):
        # tiga pita (indigo, cyan, lime) digambar ffmpeg sendiri (tanpa berkas): menyapu kanan→kiri 0,6 dtk,
        # menutup penuh tepat di titik potong. Sumber `color` tak berujung → tidak ada antrean input yang bisa macet.
        n_sw = 0
        for titik in [x for sp in (g.get("_sisipan") or []) for x in (sp["a"], sp["b"])]:
            for i, warna in enumerate(("0xC6FF3D", "0x22D3EE", "0x5B5BF6")):
                t0 = titik - 0.3 + i * 0.06
                graf.append(f"color=c={warna}:s=1300x1920:r=30[sw{n_sw}]")
                graf.append(f"[{v}][sw{n_sw}]overlay=x='W-(t-{t0:.3f})/0.6*(W+1300)':y=0:"
                            f"enable='between(t,{t0:.3f},{t0 + 0.6:.3f})':eof_action=pass:shortest=1[vs{n_sw}]")
                v = f"vs{n_sw}"
                n_sw += 1
    # hiasan judul pembuka: coretan neon / pita kertas sobek
    if klip.judul and g.get("judul_buka", True) and not (g.get("banner", True) and klip.judul):
        if c.get("judul") == "neon":
            hiasan("neon", 0.0, tahan=max(durasi - 1.0, 0))   # coretan ikut sampai akhir
        elif c.get("judul") == "sobek":
            # frame 40 = pita sudah penuh; frame terakhir animasi justru pitanya keluar layar
            hiasan("sobek", 0.0, tahan=max(durasi - 1.0, 0), beku=40)
    # emoji otomatis (gambar Twemoji) di atas baris subtitle
    if c.get("emoji") and g.get("subtitle", True) and g.get("layout") != "gamer":
        rencana = rencana_emoji(kal, klip, c["per"])
        y_emoji = int(1920 * float(g.get("posisi_y", 72)) / 100 - c["uk"] * 1.4 - 150)
        for kode in dict.fromkeys(x[2] for x in rencana):
            masukan_extra += ["-loop", "1", "-t", f"{durasi:.2f}", "-i", str(EMOJI_DIR / f"{kode}.png")]
            kapan = "+".join(f"between(t,{m:.2f},{sl:.2f})" for m, sl, k in rencana if k == kode)
            graf.append(f"[{n_in}:v]scale=150:150,format=rgba[em{n_in}]")
            graf.append(f"[{v}][em{n_in}]overlay=x=(W-w)/2:y={max(y_emoji, 40)}:enable='{kapan}':eof_action=pass[ve{n_in}]")
            v = f"ve{n_in}"
            n_in += 1
    # progress bar tipis di bawah (maju sesuai durasi klip)
    if c.get("progres"):
        graf.append(f"color=c={c['warna']}:s=1080x10:r=30:d={durasi:.2f}[pb]")
        graf.append(f"[{v}][pb]overlay=x='-W+W*t/{durasi:.2f}':y=H-10:eof_action=pass[vp]")
        v = "vp"
    if g.get("layout") == "gamer":
        # Layout gamer: TANPA subtitle, TANPA banner teks otomatis.
        # Hanya facecam + gameplay + branding (PNG di bawah).
        import random as _r
        if not g.get("preset"):
            g["preset"] = _r.choice(list(PRESET.keys()))
        g["subtitle"] = False
        g["banner"] = False
        g["banner_durasi"] = 0
        g["banner_tengah"] = True
        g["banner_tengah"] = True
        # Gaya banner berbeda untuk setiap klip (kotak + font + warna acak)
        g["_gaya_banner_obj"] = pilih_gaya_banner(klip)
        g["judul_buka"] = False
        g["akun"] = ""
        g["watermark"] = ""
        if "posisi_y" not in g:
            g["posisi_y"] = 50
    if g.get("subtitle", True) or g.get("banner", True) or c.get("akun") or (g.get("judul_buka", True) and klip.judul) \
            or c.get("watermark"):
        ass = kerja / f"{out.stem}.ass"
        tulis_ass(kal, klip, ass, g, bar_atas)
        fdir = kerja / "font"
        if FONT_DIR.exists() and not fdir.exists():
            try:
                fdir.symlink_to(FONT_DIR, target_is_directory=True)
            except OSError:  # Windows tanpa izin symlink → salin
                import shutil as _sh
                _sh.copytree(FONT_DIR, fdir)
        graf.append(f"[{v}]subtitles=filename='{ass.name}':fontsdir='{FONT_DIR}'[vout]" if (ada_audio(file) and kal) else f"[{v}]null[vout]")
    else:
        graf.append(f"[{v}]null[vout]")

    # audio: suara asli (boost) + musik latar + SFX hook
    # Bar branding gamer: gambar 1080x320 milik user, dipakai utuh sebagai input
    if layout == "gamer" and int(g.get("brand_h", 320)) > 0:
        aset_branding = cari_berkas_branding(g)
        if aset_branding:
            masukan_extra += ["-loop", "1", "-t", f"{durasi:.2f}", "-i", str(aset_branding.resolve())]
    masukan = ["-ss", f"{klip.mulai:.2f}", "-t", f"{durasi:.2f}", "-i", str(file.resolve()), *masukan_extra]
    fc_path = g.get("facecam")
    if fc_path:
        masukan += ["-ss", f"{klip.mulai:.2f}", "-t", f"{durasi:.2f}", "-i", str(Path(fc_path).resolve())]
    aud = [f"[0:a]volume={float(g.get('suara', 100)) / 100:.2f}[a0]"]
    campur = ["[a0]"]
    idx = n_in
    musik = g.get("musik")
    if musik and Path(musik).exists():
        masukan += ["-stream_loop", "-1", "-i", str(Path(musik).resolve())]
        aud.append(f"[{idx}:a]volume={float(g.get('volume_musik', 18)) / 100:.2f},atrim=0:{durasi:.2f},"
                   f"afade=t=out:st={max(durasi - 1.5, 0):.2f}:d=1.5[am]")
        campur.append("[am]")
        idx += 1
    sfx = g.get("sfx")
    if sfx and Path(sfx).exists():
        masukan += ["-i", str(Path(sfx).resolve())]
        aud.append(f"[{idx}:a]volume=0.9[as]")
        campur.append("[as]")
        idx += 1
    if len(campur) > 1:
        aud.append(f"{''.join(campur)}amix=inputs={len(campur)}:duration=first:normalize=0,alimiter=limit=0.95[aout]")
    else:
        aud.append("[a0]anull[aout]")

    # facecam selalu input terakhir (setelah semua masukan_extra); hitung berapa -i di masukan_extra
    fc_in = 1 + sum(1 for i, a in enumerate(masukan_extra) if a == "-i")
    # Branding = input terakhir di masukan_extra → tepat satu indeks di bawah facecam
    graf = [g.replace("[FACECAM:v]", f"[{fc_in}:v]") for g in graf]
    graf = [g.replace("[BRANDING:v]", f"[{max(fc_in - 1, 0)}:v]") for g in graf]

    subprocess.run([
        ffmpeg(), "-y", "-v", "error", *masukan,
        "-filter_complex", ";".join(graf + aud), "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out.resolve()),
    ], check=True, cwd=kerja)


# ── 8. Subtitle dari berkas .srt & rentang ──────────────────────────────────
def detik(t: str) -> float:
    t = t.strip().replace(",", ".")
    bag = [float(x) for x in t.split(":")]
    s = 0.0
    for b in bag:
        s = s * 60 + b
    return s


def baca_srt(p: Path) -> list[Kalimat]:
    """SRT/TXT bertanda waktu → kalimat; waktu per kata dibagi rata (cukup untuk subtitle)."""
    teks = p.read_text(encoding="utf-8", errors="replace")
    hasil = []
    for blok in re.split(r"\n\s*\n", teks.strip()):
        m = re.search(r"(\d[\d:.,]*)\s*-->\s*(\d[\d:.,]*)", blok)
        if not m:
            continue
        isi = " ".join(b for b in blok[m.end():].strip().splitlines() if b.strip())
        isi = re.sub(r"<[^>]+>", "", isi).strip()
        a, b = detik(m.group(1)), detik(m.group(2))
        kata = isi.split()
        if not kata:
            continue
        lang = (b - a) / len(kata)
        hasil.append(Kalimat(a, b, isi, [Kata(a + i * lang, a + (i + 1) * lang, k) for i, k in enumerate(kata)]))
    if not hasil:
        sys.exit("Berkas subtitle tidak berisi penanda waktu (format SRT: 00:00:01,000 --> 00:00:03,000).")
    return hasil


def baca_rentang(r: str | None, panjang: float) -> tuple[float, float]:
    if not r:
        return 0.0, panjang
    a, _, b = r.partition("-")
    return detik(a) if a else 0.0, min(detik(b), panjang) if b else panjang


# ── Utama ───────────────────────────────────────────────────────────────────
def muat_transkrip(file: Path, a, kerja: Path) -> list[Kalimat]:
    if a.subtitle_file:
        log(f"Memakai subtitle dari {Path(a.subtitle_file).name}.")
        return baca_srt(Path(a.subtitle_file))
    if not ada_audio(file):
        log("Tidak ada audio di video → subtitle dilewati.")
        return []
    cache = kerja / f"transkrip-{file.stem}-{a.model}-b{getattr(a, 'beam', 5)}.json"
    if cache.exists():
        log("Transkrip diambil dari cache.")
        return [Kalimat(k["mulai"], k["selesai"], k["teks"], [Kata(**x) for x in k["kata"]])
                for k in json.loads(cache.read_text(encoding="utf-8"))]
    kal = transkrip(file, a.model, None if a.bahasa in ("auto", "", None) else a.bahasa,
                    getattr(a, "beam", 5), getattr(a, "potong", 0))
    cache.write_text(json.dumps([asdict(k) for k in kal], ensure_ascii=False), encoding="utf-8")
    return kal


def analisis(a, keluar: Path, kerja: Path) -> None:
    file, heatmap, judul = ambil_sumber(a.sumber, kerja)
    panjang, w, h = info_video(file)
    log(f"Video: {judul} — {panjang:.0f} detik, {w}x{h}. Heatmap YouTube: {'ada' if heatmap else 'tidak ada'}.")
    semua = muat_transkrip(file, a, kerja)
    ra, rb = baca_rentang(a.rentang, panjang)
    kal = [k for k in semua if k.selesai > ra and k.mulai < rb]
    if a.rentang:
        log(f"Rentang analisis: {ra:.0f}–{rb:.0f} detik ({len(kal)} kalimat).")

    if a.hanya_prompt:
        out = keluar / "prompt-claude.md"
        tulis_prompt(kal, a.durasi, a.jumlah, out, a.arahan)
        log(f"Prompt siap: {out}\n  Tempel ke Claude, simpan balasannya sebagai pilihan.json, lalu jalankan:\n"
            f"  uv run klip.py \"{a.sumber}\" --pilihan pilihan.json")
        return

    ringkasan, hashtag = "", []
    # Riset internet: topik lagi viral di Indonesia (Google Trends)
    topik_trending = ambil_trending_topik()
    if topik_trending:
        log(f"Topik trending Indonesia: {', '.join(topik_trending[:5])}")
    penyedia = (a.ai or baca_env().get("AI", "lokal")).lower()
    if a.pilihan:
        data = json.loads(Path(a.pilihan).read_text(encoding="utf-8"))
        sumber_ai = "pilihan.json"
        if isinstance(data, dict):
            ringkasan, hashtag = data.get("ringkasan", ""), data.get("hashtag", [])
            data = data.get("klip", [])
        klips = [Klip(float(d["mulai"]), float(d["selesai"]), d.get("judul", ""), float(d.get("skor", 0) or 0),
                      d.get("alasan", ""), d.get("caption", ""), "",
                      [str(x) for x in (d.get("kata_kunci") or []) if x][:8]) for d in data]
        hooks = [d.get("hook") for d in data]
        # model kecil (mis. Ollama) kadang memilih potongan terlalu pendek → perpanjang ke akhir kalimat terdekat dari target
        for k in klips:
            if k.selesai - k.mulai < a.durasi * 0.6:
                target = k.mulai + a.durasi
                akhir = [x.selesai for x in kal if x.selesai >= target - 2]
                k.selesai = min(akhir[0] if akhir else target, panjang or target)
                log(f"Momen “{k.judul}” terlalu pendek → diperpanjang ke {k.selesai - k.mulai:.0f} dtk.")
        log(f"Memakai {len(klips)} momen dari {sumber_ai}.")
    else:
        mode_momen = getattr(a, "momen", "") or ("gamer" if a.layout == "gamer" else "umum")
        tahap_ai = ai_tahap_aktif("skor", {"ai_tahap": getattr(a, "ai_tahap", "")})
        pakai_ai = ai_siap(penyedia, {}) and tahap_ai
        if not pakai_ai:
            _ai_catat(False, f"AI tidak diaktifkan (penyedia='{penyedia}', tahap AI='{getattr(a, 'ai_tahap', '') or 'default'}'). "
                             "Momen dipilih heuristik lokal: kamus gamer + sinyal fisik.")
        # Sinyal lokal (energi/lonjakan/reaksi/aksi) dipakai apa adanya:
        # inilah bukti gaming yang tidak bisa dinilai LLM dari teks saja.
        sinyal = hitung_sinyal(file, getattr(a, "facecam", "") or "")
        en = sinyal["energi"]
        if pakai_ai:
            log(f"Mode momen AI utama: AI '{penyedia}' pilih momen dari teks Whisper.")
            klips = ai_pilih_momen_utama(
                kal, a.durasi, a.jumlah, a.arahan,
                penyedia=penyedia,
                cache=kerja / f"ai-momen-{mode_momen}.json",
                mode=mode_momen,
                sinyal=sinyal,
                durasi_bebas=getattr(a, "durasi_bebas", False),
                topik_trending=topik_trending,
            )
            if klips:
                sumber_ai = f"{penyedia}"
                log(f"   AI utama memilih {len(klips)} momen dari teks Whisper.")
            else:
                if not AI_STATUS.get("alasan"):
                    _ai_catat(False, "AI tidak mengembalikan momen yang bisa dipakai, jadi dipilih heuristik lokal.")
                log("   AI utama gagal → pakai heuristik lokal.")
                klips = (pilih_momen(kal, en, heatmap, a.durasi, a.jumlah, panjang, a.arahan,
                                     mode="gamer", sinyal=sinyal,
                                     durasi_bebas=getattr(a, "durasi_bebas", False),
                                     topik_trending=topik_trending)
                         if mode_momen == "gamer"
                         else pilih_momen(kal, en, heatmap, a.durasi, a.jumlah, panjang, a.arahan,
                                          durasi_bebas=getattr(a, "durasi_bebas", False),
                                          topik_trending=topik_trending))
                sumber_ai = "lokal"
        elif mode_momen == "gamer":
            log("Mode momen GAMER: cari teriakan, reaksi wajah, aksi game, dan kata gaming…")
            klips = pilih_momen(kal, en, heatmap, a.durasi, a.jumlah, panjang, a.arahan,
                                mode="gamer", sinyal=sinyal,
                                durasi_bebas=getattr(a, "durasi_bebas", False),
                                topik_trending=topik_trending)
            sumber_ai = "lokal"
        else:
            log("Mencari momen terbaik (heatmap + energi suara + kepadatan kata + kata hook)…")
            klips = pilih_momen(kal, en, heatmap, a.durasi, a.jumlah, panjang, a.arahan,
                                durasi_bebas=getattr(a, "durasi_bebas", False),
                                topik_trending=topik_trending)
            sumber_ai = "lokal"
        hooks = [None] * len(klips)

    # Tahap AI: perbaiki transkrip (in-memory, cache tetap aman) lalu metadata siap posting
    if ai_siap(penyedia, {}) and ai_tahap_aktif("transkrip", {"ai_tahap": getattr(a, "ai_tahap", "")}) and kal:
        log("Tahap AI: mengoreksi salah dengar transkrip…")
        kal = ai_polih_transkrip(kal, penyedia, kerja / "ai-transkrip.json")
    metadata_ai = []
    if ai_siap(penyedia, {}) and ai_tahap_aktif("hook", {"ai_tahap": getattr(a, "ai_tahap", "")}) and klips:
        log("Tahap AI: membuat hook + judul + caption + alasan publish…")
        metadata_ai = ai_metadata(klips, penyedia, kerja / "ai-metadata.json")
        if metadata_ai:
            log(f"   Metadata dibuat untuk {len(metadata_ai)} klip.")
        else:
            log("   Metadata AI gagal → pakai judul lokal.")


    daftar = []
    peta_meta = {m["no"]: m for m in metadata_ai}
    for i, (k, hk) in enumerate(zip(klips, hooks), 1):
        isi = [x for x in kal if x.selesai > k.mulai and x.mulai < k.selesai]
        k.kutipan = " ".join(x.teks for x in isi)[:400]
        if not k.caption:
            k.caption = k.judul
        if hk is None:
            kena = [x for x in isi if set(re.findall(r"\w+", x.teks.lower())) & KATA_HOOK or "?" in x.teks]
            hk = (kena[0] if kena else (isi[0] if isi else k)).mulai
        baris = {**asdict(k), "no": i, "hook": round(float(hk), 1), "file": ""}
        meta = peta_meta.get(i)
        if meta:
            baris.update({"hook_text": meta.get("hook", ""), "judul_yt": meta.get("judul_yt", ""),
                          "caption_ig": meta.get("caption_ig", ""), "caption_tiktok": meta.get("caption_tiktok", ""),
                          "why": meta.get("why", "")})
            if meta.get("caption_tiktok") and not k.caption:
                k.caption = meta["caption_tiktok"]
        daftar.append(baris)

    try:
        en = energi_audio(file)
        langkah = max(len(en) // 120, 1)
        energi_ringkas = [round(float(en[i:i + langkah].mean()), 3) for i in range(0, len(en), langkah)]
    except Exception:  # noqa: BLE001
        energi_ringkas = []
    # sumber untuk pratinjau di Studio + gambar kecil untuk riwayat
    tautan = keluar / f"sumber{file.suffix}"
    if not tautan.exists():
        try:
            tautan.symlink_to(file)
        except OSError:
            import shutil
            shutil.copy(file, tautan)
    t_gambar = (klips[0].mulai + 2) if klips else min(5, panjang / 2)
    subprocess.run([ffmpeg(), "-y", "-v", "error", "-ss", f"{t_gambar:.1f}", "-i", str(file), "-frames:v", "1",
                    "-vf", "scale=320:-2", str(keluar / "gambar.jpg")], check=False)
    (keluar / "info.json").write_text(json.dumps({
        "judul": judul, "durasi": round(panjang, 1), "lebar": w, "tinggi": h, "heatmap": heatmap,
        "energi": energi_ringkas, "ai": sumber_ai, "ringkasan": ringkasan, "hashtag": hashtag,
        # Rincian apakah AI ikut andil — ditampilkan di web UI setelah analisis
        "ai_info": {
            "pakai": bool(AI_STATUS.get("pakai")) and sumber_ai != "lokal",
            "penyedia": sumber_ai,
            "model": AI_STATUS.get("model", ""),
            "alasan": AI_STATUS.get("alasan", ""),
            "dari_cache": bool(AI_STATUS.get("dari_cache")),
            "tahap": getattr(a, "ai_tahap", "") or "default",
            "momen": locals().get("mode_momen", "") or "",
        },
        "sumber": str(file), "pratinjau": tautan.name, "rentang": [ra, rb],
    }, ensure_ascii=False), encoding="utf-8")
    (keluar / "klip.json").write_text(json.dumps(daftar, ensure_ascii=False, indent=2), encoding="utf-8")
    (keluar / "transkrip.json").write_text(json.dumps([asdict(k) for k in kal], ensure_ascii=False), encoding="utf-8")
    log(f"Analisis selesai: {len(daftar)} momen.")


def render_terpilih(keluar: Path, kerja: Path, pilih: str | None, gaya: dict) -> None:
    info = json.loads((keluar / "info.json").read_text(encoding="utf-8"))
    daftar = json.loads((keluar / "klip.json").read_text(encoding="utf-8"))
    kal = [Kalimat(k["mulai"], k["selesai"], k["teks"], [Kata(**x) for x in k["kata"]])
           for k in json.loads((keluar / "transkrip.json").read_text(encoding="utf-8"))]
    nomor = {int(x) for x in pilih.split(",")} if pilih else {d["no"] for d in daftar}
    file = Path(info["sumber"])
    if not file.exists():
        file = keluar / info["pratinjau"]
    w, h = info.get("lebar"), info.get("tinggi")
    if not w:
        _, w, h = info_video(file)
    target = [d for d in daftar if d["no"] in nomor]
    for d in daftar:
        if d.get("jejak"):
            _JEJAK_SIAP[(round(d["mulai"], 2), round(d["selesai"], 2))] = d["jejak"]
    for n, d in enumerate(target, 1):
        # Snap batas klip ke batas kalimat utuh agar tidak terpotong di tengah
        # kalimat (penting untuk durasi bebas / pilihan AI).
        a, b = snap_batas_kalimat(kal, d["mulai"], d["selesai"])
        k = Klip(a, b, d.get("judul_banner") or d["judul"], d.get("skor", 0),
                 kata_kunci=d.get("kata_kunci") or [])
        out = keluar / f"klip-{d['no']:02d}.mp4"
        log(f"Render {n}/{len(target)} {out.name}: {k.mulai:.1f}–{k.selesai:.1f}s  “{d['judul']}”")
        sisipan, kredit = siapkan_broll(gaya, kal, k)
        if sisipan:
            log(f"B-roll: {len(sisipan)} sisipan ({', '.join(x['kunci'] for x in sisipan)}).")
        render(file, k, kal, out, kerja, w, h, {**gaya, "_sisipan": sisipan})
        d["file"] = out.name
        # Tahap QC: cek hasil render (durasi, resolusi, audio, frame hitam)
        if ai_tahap_aktif("qc", gaya):
            cek = qc_klip(out, k.selesai - k.mulai, gaya.get("layout", ""))
            d["qc"] = cek
            if cek["ok"]:
                log(f"   QC ✓ {cek.get('durasi')}s {cek.get('resolusi')}")
            else:
                log(f"   QC ⚠ {cek['catatan']}")
        d["broll"] = [{"detik": round(x["a"], 1), "kunci": x["kunci"], "file": Path(x["file"]).name} for x in sisipan]
        if kredit:
            d["kredit"] = kredit
            if kredit not in (d.get("caption") or ""):
                d["caption"] = ((d.get("caption") or "") + f"\n{kredit}").strip()
        (keluar / "klip.json").write_text(json.dumps(daftar, ensure_ascii=False, indent=2), encoding="utf-8")
    (keluar / "gaya.json").write_text(json.dumps(gaya, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"Selesai. {len(target)} klip di {keluar}")


def main() -> None:
    p = argparse.ArgumentParser(description="Potong video panjang jadi klip pendek 9:16.")
    p.add_argument("sumber", nargs="?", help="file video atau link YouTube")
    p.add_argument("--jumlah", type=int, default=3, help="jumlah klip (default 3)")
    p.add_argument("--durasi", type=int, default=30, help="target detik per klip (default 30)")
    p.add_argument("--durasi-bebas", action="store_true",
                   help="durasi bebas mengikuti isi pembicaraan (AI menentukan panjang tiap klip, tidak terpotong)")
    p.add_argument("--model", default="small", help="model whisper: tiny/base/small/medium/large-v3")
    p.add_argument("--beam", type=int, default=5, help="beam size whisper: 1=greedy (cepat, RAM kecil), 5=akurasi (lambat, RAM besar)")
    p.add_argument("--potong", type=int, default=0, help="pecah audio jadi chunk N detik saat transkripsi (0=off). Wajib untuk model besar di RAM kecil")
    p.add_argument("--momen", choices=["umum", "gamer"], default="",
                   help="cara cari momen: umum (default) atau gamer (teriakan + reaksi wajah + aksi game). Kosong = ikut layout")
    p.add_argument("--bahasa", default="id", help="kode bahasa, mis. id atau en; 'auto' = deteksi otomatis (default id)")
    p.add_argument("--bahasa-judul", choices=["id", "en"], default="id",
                   help="bahasa untuk judul/banner yang ditulis AI: id (Indonesia) atau en (English)")
    p.add_argument("--keluar", default="hasil-klip", help="folder hasil")
    p.add_argument("--tanpa-wajah", action="store_true", help="bingkai tengah, jangan ikuti wajah")
    p.add_argument("--tanpa-subtitle", action="store_true")
    p.add_argument("--warna", default=None, help="warna sorot subtitle (hex); kosong = warna preset")
    p.add_argument("--hanya-prompt", action="store_true", help="Opsi B: tulis prompt Claude lalu berhenti")
    p.add_argument("--pilihan", help="Opsi B: JSON momen dari Claude")
    p.add_argument("--arahan", default="", help="momen yang dicari, mis. 'momen lucu' atau 'tips praktis'")
    p.add_argument("--ai", default=None, help="penyedia AI: lokal (default), openrouter (model FREE), gemini, "
                        "openai (Ollama dll.), claude-code, codex, opencode")
    p.add_argument("--ai-tahap", default="", help="tahap AI yang aktif: transkrip,skor,hook,layout,qc | all | off "
                        "(default: semua, kalau --ai bukan lokal)")
    p.add_argument("--rentang", help="bagian video yang dianalisis, mis. 10:00-25:30")
    p.add_argument("--subtitle-file", help="pakai subtitle .srt sendiri (lewati transkripsi)")
    p.add_argument("--hanya-analisis", action="store_true", help="cari momen tanpa render")
    p.add_argument("--render", action="store_true", help="render dari hasil analisis di --keluar")
    p.add_argument("--jejak", type=int, help="hitung jejak wajah klip nomor N (disimpan di klip.json, dipakai pratinjau)")
    p.add_argument("--pilih", help="nomor klip yang dirender, mis. 1,3,4 (default semua)")
    p.add_argument("--uji-ai", help="uji sambungan AI (lokal/gemini/openai/claude-code/codex/opencode)")
    p.add_argument("--deteksi-pip", choices=["kiri", "kanan"], default=None,
                   help="hanya cetak kotak crop PiP presisi sebagai JSON (dipakai pratinjau web UI)")
    p.add_argument("--broll", choices=["pixabay", "file"], help="sisipkan B-roll: pixabay (butuh PIXABAY_API_KEY) atau file sendiri")
    p.add_argument("--broll-file", nargs="*", default=[], help="video/foto milikmu untuk B-roll (dengan --broll file)")
    p.add_argument("--watermark", help="teks di tengah klip, putih transparan ±50%%, mis. @akunmu")
    p.add_argument("--layout", default=None, choices=["tunggal", "split", "gamer", "lebar"],
                   help="tampilan klip: tunggal (satu layar), split (dua pembicara atas-bawah), gamer (wajah atas + gameplay bawah + branding), atau lebar (landscape utuh tanpa crop, black bars atas-bawah)")
    p.add_argument("--face-mode", default="auto", choices=["auto", "manual", "fit"], help="bingkai 9:16: auto (ikuti wajah bicara), manual (tentukan --face-x), fit (layar penuh)")
    p.add_argument("--face-x", type=float, default=0.5, help="posisi wajah 0.0 (kiri) … 1.0 (kanan) untuk --face-mode manual")
    p.add_argument("--gaya", help="JSON gaya render (rasio, latar, fokus, layout, banner, subtitle, musik, …)")
    a = p.parse_args()
    globals()["BAHASA_JUDUL"] = a.bahasa_judul

    if a.deteksi_pip:
        # Mode ringan untuk pratinjau web UI: deteksi kotak PiP lalu keluar.
        if not a.sumber:
            p.error("--deteksi-pip butuh file video sumber")
        dur, w0, h0 = info_video(Path(a.sumber))
        kotak = deteksi_kotak_pip(Path(a.sumber), 0.0, min(dur, 8.0) if dur else 8.0, a.deteksi_pip)
        print(json.dumps({"crop": kotak, "w": w0, "h": h0}))
        return

    # Konfirmasi interaktif HANYA kalau --layout tidak diberikan sama sekali.
    # Kalau "tunggal" sudah datang dari ./mulai atau studio.py, jangan tanya lagi
    # (duplikat prompt = membingungkan, dan input bisa ket吞 salah).
    if a.layout is None:
        a.layout = "tunggal"
        if sys.stdin.isatty():
            print("\nPilih layout klip:")
            print("  1. Biasa (tunggal layar)")
            print("  2. Gamer (wajah di atas + gameplay landscape di bawah)")
            pilih = input("Masukkan 1 atau 2 [1]: ").strip()
            a.layout = "gamer" if pilih == "2" else "tunggal"

    if a.uji_ai:
        if a.uji_ai == "lokal":
            print("SIAP (mode lokal tidak memakai AI luar)")
            return
        if a.uji_ai == "openrouter":
            try:
                jawab = tanya_openrouter("Balas persis satu kata saja: SIAP", baca_env()).strip()
            except Exception as e:  # noqa: BLE001
                sys.exit(f"GAGAL: {type(e).__name__}: {str(e)[:200]}")
            print(jawab[:200])
            return
        jawab = tanya_ai(a.uji_ai, "Ini uji sambungan. Balas persis satu kata saja: SIAP").strip()
        print(jawab[:200])
        return

    keluar = Path(a.keluar).resolve()
    kerja = keluar / ".kerja"
    kerja.mkdir(parents=True, exist_ok=True)
    gaya = {**( {"warna": a.warna} if a.warna else {}), "subtitle": not a.tanpa_subtitle,
            "fokus": "tengah" if a.tanpa_wajah else a.face_mode,
            "layout": a.layout, "banner": False,
            **( {"broll": a.broll, "broll_file": a.broll_file} if a.broll else {}),
            **( {"watermark": a.watermark} if a.watermark else {}),
            **( {"facecam": a.facecam} if getattr(a, "facecam", None) else {}),
            **( {"face_x": a.face_x} if a.face_mode == "manual" else {} ),
            **( {"ai_tahap": a.ai_tahap} if a.ai_tahap else {} )}
    if a.gaya:
        isi = a.gaya if a.gaya.lstrip().startswith("{") else Path(a.gaya).read_text(encoding="utf-8")
        gaya.update(json.loads(isi))

    if a.jejak:
        info = json.loads((keluar / "info.json").read_text(encoding="utf-8"))
        daftar = json.loads((keluar / "klip.json").read_text(encoding="utf-8"))
        d = next(x for x in daftar if x["no"] == a.jejak)
        file = Path(info["sumber"])
        if not file.exists():
            file = keluar / info["pratinjau"]
        w, h = info.get("lebar"), info.get("tinggi")
        if not w:
            _, w, h = info_video(file)
        d["jejak"] = [[round(t, 2), round(x, 3)] for t, x in jejak_wajah(file, d["mulai"], d["selesai"], w, h)]
        (keluar / "klip.json").write_text(json.dumps(daftar, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(d["jejak"]))
        return
    if a.render:
        render_terpilih(keluar, kerja, a.pilih, gaya)
        return
    if not a.sumber:
        sys.exit("Isi file video atau link YouTube.")
    analisis(a, keluar, kerja)
    if a.hanya_analisis or a.hanya_prompt:
        return
    render_terpilih(keluar, kerja, a.pilih, gaya)


if __name__ == "__main__":
    main()
