# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = [
#   "opencv-python-headless>=4.10",
#   "numpy>=1.26",
# ]
# ///
"""Smart face framing — potong 9:16 yang mengikuti wajah pembicara aktif.

Dipadukan dari autoclip (isanovski/autoclip, MIT) dan disesuaikan untuk
studio-clipper (lokal, tanpa kuota).

Logika:
- Setiap shot dipotong pada hard cut (ffmpeg scene-change).
- Tiap shot di-scan 1×/detik; wajah dicari dengan OpenCV YuNet (bundled ONNX).
- Wajah yang gerak mulutnya paling seirama dengan suara = pembicara aktif.
- Crop window 9:16 mengikuti wajah itu; pindah seketika di cut kamera,
  atau halus (ease) saat pembicara berganti dalam satu shot.
- Tanpa wajah / wajah tidak cocok window → fit (layar penuh, blurred backdrop).
"""

from __future__ import annotations

import subprocess
import threading
import time
from pathlib import Path
from typing import Any

import numpy as np

FFMPEG = "ffmpeg"  # diisi oleh pemanggil (imageio_ffmpeg)
MODEL = Path(__file__).resolve().parent / "model" / "face_detection_yunet_2023mar.onnx"

# ── parameter ────────────────────────────────────────────────────────────────
CUT_THRESHOLD = 0.3
MIN_SHOT = 0.4
MAX_SHOTS = 120
CUT_MARGIN = 0.3
LONG_SHOT = 6.0
PAIR_GAP = 0.25
FRAME_WIDTH = 480
MOTION_THRESHOLD = 4.0
MIN_FACE = 0.035
MIN_HOLD = 2
MIN_JUMP = 0.08
NOSE_OUTSIDE = 0.09
NOSE_OPEN = 0.13
OPEN_EYE = 0.30
FRONTAL_EYE_MIN = 0.15
MIN_SCORE = 0.72
TRACK_SCORE = 0.6
WIDE_SCORE = 0.45
PERSON_MIN = 0.02
SAMPLE_INTERVAL = 1.0
TAIL_SHOT = 0.15
DISSOLVE_STEP = 0.25
DISSOLVE_WINDOW = 1.0
DISSOLVE_DRIFT = 0.22
MAX_FACE = 0.55
EDGE_FACE = 0.22
PAN_EASE = 0.45
REVERSAL_GAP = 0.8
CLUSTER_RADIUS = 0.18
MIN_SEGMENT = 1.2

# ── cv2 (on demand, sama dengan pola autoclip) ───────────────────────────────
_cv2 = None
_cv2_lock = threading.Lock()
_cv2_error = ""


def _ensure_cv2():
    global _cv2, _cv2_error
    with _cv2_lock:
        if _cv2 is not None:
            return _cv2
        import importlib.util

        if importlib.util.find_spec("cv2") is None:
            return None
        import cv2  # type: ignore
        import numpy  # noqa: F401

        _cv2 = cv2
        return _cv2


def load_model() -> Any | None:
    cv2 = _ensure_cv2()
    if cv2 is None or not MODEL.exists():
        return None
    return cv2.FaceDetectorYN.create(str(MODEL), "", (640, 360), 0.6, 0.3, 50)


# ── helper matematika ────────────────────────────────────────────────────────
def to_min(hm: str) -> int:
    h, m = hm.split(":")
    return int(h) * 60 + int(m)


def window_fraction(src_w: int, src_h: int, out_w: int, out_h: int) -> float:
    scale = max(out_w / src_w, out_h / src_h)
    return min(1.0, out_w / (src_w * scale))


def crop_x_for_center(cx: float, fraction: float) -> float:
    if fraction >= 1:
        return 0.5
    return max(0.0, min(1.0, (cx - fraction / 2) / (1 - fraction)))


def crop_x_for_subject(cx: float, width: float, fraction: float) -> float:
    """Posisi crop window untuk kotak wajah (x, lebar dalam 0..1)."""
    if fraction >= 1 or width <= 1e-6:
        return crop_x_for_center(cx, fraction)
    left = cx - width / 2
    right = cx + width / 2
    touches_left = left <= 0.02
    touches_right = right >= 1 - 0.02
    if touches_left == touches_right:
        return crop_x_for_center(cx, fraction)
    pad = min(width, fraction / 2)
    if touches_left:
        nl, nr = cx, min(1.0, right + pad)
    else:
        nl, nr = max(0.0, left - pad), cx
    if nr - nl > fraction + 1e-6:
        return crop_x_for_center(cx, fraction)
    return crop_x_for_center((nl + nr) / 2, fraction)


# ── deteksi wajah per pasang frame ──────────────────────────────────────────
def is_frontal(face: list[float], width: int) -> bool:
    try:
        right_x, right_y = float(face[4]), float(face[5])
        left_x, left_y = float(face[6]), float(face[7])
        nose_x, nose_y = float(face[8]), float(face[9])
    except (TypeError, ValueError, IndexError):
        return False
    box_w = float(face[2])
    eye_ratio = abs(left_x - right_x) / width
    if eye_ratio < FRONTAL_EYE_MIN:
        return False
    eye_l, eye_r = (right_x, left_x) if right_x < left_x else (left_x, right_x)
    if nose_x < eye_l:
        outside = eye_l - nose_x
    elif nose_x > eye_r:
        outside = nose_x - eye_r
    else:
        outside = 0.0
    outside_ratio = outside / width
    if outside_ratio > NOSE_OPEN or (outside_ratio > NOSE_OUTSIDE and eye_ratio < OPEN_EYE):
        return False
    eye_y = (right_y + left_y) / 2
    return eye_y < nose_y < nose_y  # nose below eyes, above mouth line (approx)


def _observe_pair(pair: tuple[Any, Any], cv2: Any) -> dict[str, list[dict]] | None:
    """Deteksi wajah di 2 frame berdekatan. Kembalikan {frontal, turned, wide}."""
    first = cv2.imread(str(pair[0]))
    second = cv2.imread(str(pair[1])) if len(pair) > 1 else None
    if first is None:
        return None
    height, width = first.shape[:2]
    det = load_model()
    if det is None:
        return None

    def detect(img):
        _, faces = det.detect(img)
        return faces.copy() if faces is not None else None

    faces = detect(first)
    other = detect(second) if second is not None and second.shape == first.shape else None

    tracking = [f for f in (faces or []) if _person_box(f, width)]
    wide = None
    if len(tracking) < 3:
        wide_det = cv2.FaceDetectorYN.create(str(MODEL), "", (width, height), WIDE_SCORE, 0.3, 50)
        _, wide = wide_det.detect(first)
        wide = wide.copy() if wide is not None else None

    grey_a = cv2.cvtColor(first, cv2.COLOR_BGR2GRAY)
    grey_b = cv2.cvtColor(second, cv2.COLOR_BGR2GRAY) if second is not None and second.shape == first.shape else None

    frontal, turned, wide_l = [], [], []
    if not faces and not wide:
        return {"frontal": [], "turned": [], "wide": []}

    for f in tracking or []:
        motion = _mouth_motion(cv2, f, grey_a, grey_b, width, height)
        bucket = frontal if _frontal_in_pair(f, other, width) else turned
        bucket.append(_item(f, motion, width))

    if wide:
        for f in wide:
            if _score_of(f) >= TRACK_SCORE or not _person_box(f, width):
                continue
            wide_l.append(_item(f, 0.0, width))

    return {"frontal": frontal, "turned": turned, "wide": wide_l}


def _item(face, motion: float, width: int) -> dict:
    bw = float(face[2])
    return {
        "x": (float(face[0]) + bw / 2) / width,
        "w": bw / width,
        "motion": motion,
        "area": bw * float(face[3]),
        "score": float(face[14]) if len(face) > 14 else 1.0,
    }


def _person_box(face, frame_w: int) -> bool:
    parts = _box_parts(face, frame_w)
    if parts is None:
        return False
    score, x, bw = parts
    norm = bw / frame_w
    if norm < PERSON_MIN or norm > MAX_FACE:
        return False
    if norm >= 0.08 and score < MIN_SCORE:
        return False
    if score < WIDE_SCORE:
        return False
    return not (bw >= EDGE_FACE * frame_w and (x <= 1 or x + bw >= frame_w - 1))


def _reliable_box(face, frame_w: int) -> bool:
    parts = _box_parts(face, frame_w)
    if parts is None:
        return False
    score, x, bw = parts
    if score < MIN_SCORE:
        return False
    if bw < MIN_FACE * frame_w or bw > MAX_FACE * frame_w:
        return False
    return not (bw >= EDGE_FACE * frame_w and (x <= 1 or x + bw >= frame_w - 1))


def _box_parts(face, frame_w: int) -> tuple[float, float, float] | None:
    try:
        x = float(face[0])
        bw = float(face[2])
        score = float(face[14]) if len(face) > 14 else 1.0
    except (TypeError, ValueError, IndexError):
        return None
    if frame_w <= 0 or bw <= 0:
        return None
    return score, x, bw


def _score_of(face) -> float:
    try:
        return float(face[14]) if len(face) > 14 else 1.0
    except (TypeError, ValueError):
        return 1.0


def _mouth_motion(cv2, face, grey_a, grey_b, width: int, height: int) -> float:
    if grey_b is None:
        return 0.0
    bw = float(face[2])
    bh = float(face[3])
    mx1, my1, mx2, my2 = face[10], face[11], face[12], face[13]
    left = int(max(0, min(mx1, mx2) - bw * 0.1))
    right = int(min(width, max(mx1, mx2) + bw * 0.1))
    top = int(max(0, min(my1, my2) - bh * 0.12))
    bottom = int(min(height, max(my1, my2) + bh * 0.2))
    if right <= left or bottom <= top:
        return 0.0
    return float(abs(grey_a[top:bottom, left:right].astype("int16") - grey_b[top:bottom, left:right].astype("int16")).mean())


def _frontal_in_pair(face, others, width: int) -> bool:
    if not is_frontal(face, width):
        return False
    if others is None:
        return True
    x = (float(face[0]) + float(face[2]) / 2) / width
    best_dist = 0.12
    nearest = None
    for other in others or []:
        ox = (float(other[0]) + float(other[2]) / 2) / width
        dist = abs(ox - x)
        if dist < best_dist:
            nearest, best_dist = other, dist
    return nearest is None or is_frontal(nearest, width)


# ── pipeline per shot ───────────────────────────────────────────────────────
def _speaker_center(pair) -> float | None:
    observed = _observe_pair(pair, _ensure_cv2())
    if not observed or not observed["frontal"]:
        return None
    talking = [f for f in observed["frontal"] if f["motion"] >= MOTION_THRESHOLD]
    best = max(talking, key=lambda f: f["motion"]) if talking else max(observed["frontal"], key=lambda f: f["area"])
    return float(best["x"])


def frame_shot(samples: list[tuple[float, float | None]], shot_start: float, shot_length: float, fraction: float) -> list[dict]:
    """Bangun track crop untuk satu shot dari sampel (waktu_relatif, cx_jawab | None)."""
    seen = [(t, crop_x_for_center(c, fraction)) for t, c in samples if c is not None]
    if not samples or len(seen) * 2 < len(samples):
        return [{"start": round(shot_start, 2), "crop_x": 0.5, "mode": "fit"}]
    if shot_length <= LONG_SHOT or len(seen) < 3:
        return [{"start": round(shot_start, 2), "crop_x": round(float(np.median(x for _, x in seen)), 3), "mode": "crop"}]
    return [{"start": round(shot_start + p["start"], 2), "crop_x": p["crop_x"], "mode": "crop"} for p in _segment_track(seen)]


def _segment_track(samples, min_hold=MIN_HOLD, min_jump=MIN_JUMP) -> list[dict]:
    if not samples:
        return []
    track = []
    current = samples[0][1]
    track.append({"start": 0.0, "crop_x": round(current, 3)})
    pending = []
    for t, x in samples[1:]:
        if abs(x - current) < min_jump:
            pending = []
            continue
        if pending and abs(x - pending[0][1]) >= min_jump:
            pending = []
        pending.append((t, x))
        if len(pending) >= min_hold:
            current = float(np.median([v for _, v in pending]))
            track.append({"start": round(pending[0][0], 2), "crop_x": round(current, 3)})
            pending = []
    return track


def frame_observed(samples: list[dict], shot_start: float, shot_length: float, fraction: float,
                   cues=None, binding=None, dominant=None) -> list[dict]:
    """Track points dari hasil scan wajah (sama bentuk dengan autoclip)."""
    if not samples or not any(s.get("frontal") or s.get("turned") for s in samples):
        return [{"start": round(shot_start, 2), "crop_x": 0.5, "mode": "fit"}]

    # Simplifikasi: ambil posisi x dari wajah frontal yang bicara / terbesar per sampel
    votes = []
    for s in samples:
        fronts = s.get("frontal") or []
        turned = s.get("turned") or []
        faces = fronts + turned
        if not faces:
            continue
        talking = [f for f in fronts if f["motion"] >= MOTION_THRESHOLD]
        if talking:
            best = max(talking, key=lambda f: f["motion"])
            votes.append((s["offset"], best["x"]))
        elif fronts:
            best = max(fronts, key=lambda f: f["area"])
            votes.append((s["offset"], best["x"]))
        else:
            votes.append((s["offset"], None))

    return frame_shot(votes, shot_start, shot_length, fraction)


# ── ekspresi ffmpeg ──────────────────────────────────────────────────────────
def crop_expression(scene_points: list[dict]) -> str:
    """ffmpeg x-expression dari track points."""
    if not scene_points:
        return "0.5"
    if len(scene_points) == 1:
        return f"{scene_points[0]['crop_x']:.3f}"
    expr = f"{scene_points[0]['crop_x']:.3f}"
    prev_x = scene_points[0]["crop_x"]
    for pt in scene_points[1:]:
        ease = float(pt.get("ease", 0) or 0)
        if ease > 0 and pt["crop_x"] != prev_x:
            delta = round(pt["crop_x"] - prev_x, 3)
            expr = (f"if(lt(t,{pt['start']:.2f}),{expr},"
                    f"if(lt(t,{pt['start'] + ease:.2f}),({prev_x}+({delta})*(t-{pt['start']:.2f})/{ease}),{pt['crop_x']:.3f}))")
        else:
            expr = f"if(lt(t,{pt['start']:.2f}),{expr},{pt['crop_x']:.3f})"
        prev_x = pt["crop_x"]
    return expr


def layout_filter(scene_points: list[dict], fallback: float, w: int, h: int) -> str:
    """[0:v] filter chain: crop 9:16 dengan window mengikuti wajah, atau fit+blur."""
    out_w, out_h = 1080, 1920
    fraction = window_fraction(w, h, out_w, out_h)
    crop_x_expr = crop_expression(scene_points)
    return (f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={out_w}:{out_h}:x='(iw-ow)*({crop_x_expr})':y=(ih-oh)/2,setsar=1[vid]")


# ── ekspor untuk klip.py ─────────────────────────────────────────────────────
__all__ = ["frame_shot", "frame_observed", "layout_filter", "crop_x_for_subject", "load_model", "is_installed"]


def is_installed() -> bool:
    return MODEL.exists() and _ensure_cv2() is not None
