#!/bin/zsh
# record.sh <out.mp4> <seconds> — captures the 1400x788 logical top-left region (2800x1575 physical)
OUT=$1; SECS=$2
IDX=$(ffmpeg -hide_banner -f avfoundation -list_devices true -i "" 2>&1 | grep -i "Capture screen 0" | sed -E 's/.*\[([0-9]+)\] Capture screen 0.*/\1/')
[ -z "$IDX" ] && { echo "no screen device"; exit 1; }
ffmpeg -hide_banner -loglevel error -f avfoundation -capture_cursor 1 -framerate 30 -i "$IDX" -t $SECS \
  -vf "crop=2800:1575:0:56,scale=1920:1080:flags=lanczos" \
  -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p -y "$OUT" 2>&1 | grep -vE "^objc|not linked|pixel format|Supported|uyvy|yuyv|nv12|0rgb|bgr0" || true
