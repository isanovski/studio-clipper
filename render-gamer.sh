#!/bin/bash
# ============================================================
# LAYOUT GAMER SIMPLE — facecam atas, subtitle tengah, gameplay bawah
# Output: 1080x1920
# Simpan sebagai: render-gamer.sh
# ============================================================

INPUT_VIDEO="contoh/video-dari-hp.mp4"   # <-- gameplay kamu
INPUT_FACECAM="contoh/facecam.mp4"       # <-- facecam kamu
OUTPUT="hasil/klip-gamer.mp4"

# ---------- PENGATURAN ----------

# Waktu klip (detik)
START="10.5"
DURATION="28"

# Facecam: diperagang agar pas (tidak ada letterbox di sisi)
FC_SIZE="720"
FC_X="180"     # (1080 - 720) / 2 = tengah
FC_Y="0"       # atas

# Kalau wajah di file facecam masih kecil / bukan sudah di-crop,
# isi crop di sini, contoh: "400:400:100:720"
FC_CROP=""

# Gameplay: 4:3 center crop -> 1080x810
GAME_WIDTH="1080"
GAME_HEIGHT="840"
GAME_Y="750"   # langsung di bawah facecam

# Subtitle (pengaturan font & size ada di dalam file .ass)
SUB_FILE="hasil/klip-baru/.kerja/klip-01-sub.ass"
SUB_FONT="Archivo Black"
SUB_SIZE="64"

# --------------------------------------------------------

mkdir -p hasil

# Bangun filter facecam (opsional crop dulu kalau perlu)
if [ -n "$FC_CROP" ]; then
  FC_FILTER="crop=$FC_CROP,scale=$FC_SIZE:$FC_SIZE:flags=lanczos,setsar=1"
else
  FC_FILTER="scale=$FC_SIZE:$FC_SIZE:flags=lanczos,setsar=1"
fi

FONTS_DIR="/home/ubuntu/studio-clipper/klip/font"

ffmpeg -y \
  -ss "$START" -t "$DURATION" -i "$INPUT_VIDEO" \
  -ss "$START" -t "$DURATION" -i "$INPUT_FACECAM" \
  -filter_complex "
    color=c=black:s=1080x1920:d=$DURATION[bg];

    [0:v]crop=min(iw\\,ih*4/3):min(ih\,iw*3/4),
         scale=$GAME_WIDTH:$GAME_HEIGHT:flags=lanczos,setsar=1[game];

    [1:v]$FC_FILTER[fc];

    [bg][fc]overlay=x=$FC_X:y=$FC_Y[t1];
    [t1][game]overlay=x=0:y=$GAME_Y[t2];

    [t2]subtitles=filename='$SUB_FILE':fontsdir='$FONTS_DIR':force_style='Fontname=Montserrat-ExtraBold,Fontsize=72,Outline=10,BackColour=&H78000000,Alignment=2,MarginV=960'[vout]
  " \
  -map "[vout]" -map "0:a" \
  -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p \
  -c:a aac -b:a 192k \
  "$OUTPUT"

echo "Selesai: $OUTPUT"
