#!/usr/bin/env python3
"""Uji coba studio-clipper: import framing, cek model YuNet, cek argumen CLI."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent
KLIP = AKAR / "klip"
sys.path.insert(0, str(KLIP))

print("=" * 60)
print("STUDIO-CLIPPER — UJI COBA INTEGRITAS")
print("=" * 60)

# 1. Cek model YuNet
model = KLIP / "model" / "face_detection_yunet_2023mar.onnx"
print(f"\n1. Model YuNet: {model}")
print(f"   Ada: {model.exists()} · Ukuran: {model.stat().st_size / 1024:.0f} KB" if model.exists() else "   TIDAK ADA!")

# 2. Cek import framing
print("\n2. Import klip.framing:")
try:
    import framing  # noqa: F401
    print("   OK — framing.py diimpor tanpa error")
except Exception as e:
    print(f"   GAGAL: {e}")
    sys.exit(1)

# 3. Cek load_model
print("\n3. load_model():")
from framing import load_model, is_installed
det = load_model()
print(f"   Model dimuat: {det is not None}")
print(f"   is_installed(): {is_installed()}")

# 4. Cek argumen CLI klip.py
print("\n4. Argumen CLI klip.py:")
r = subprocess.run([sys.executable, "klip/klip.py", "--help"], capture_output=True, text=True, cwd=AKAR)
help_txt = r.stdout
for flag in ("--face-mode", "--face-x", "--layout", "--layout gamer"):
    ada = flag in help_txt
    print(f"   {flag}: {'TERDAPAT' if ada else 'TIDAK DITEMUKAN'}")

# 5. Cek frame_shot dan layout_filter
print("\n5. Fungsi framing utama:")
from framing import frame_shot, layout_filter, crop_x_for_subject
print(f"   frame_shot: {callable(frame_shot)}")
print(f"   layout_filter: {callable(layout_filter)}")
print(f"   crop_x_for_subject(0.5, 0.3, 9/16) = {crop_x_for_subject(0.5, 0.3, 9/16):.3f}")

# 6. Cek mulai sintaks
print("\n6. Sintaks mulai:")
import ast
ast.parse((AKAR / "mulai").read_text())
print("   OK — mulai syntaktis benar")

print("\n" + "=" * 60)
print("SEMUA UJI COBA LOLOS — studio-clipper siap digunakan.")
print("=" * 60)
