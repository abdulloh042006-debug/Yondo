#!/bin/sh
# Reel 1 mux: video.mp4 + mix.wav -> yondo-reel1-shaharda-yolgiz-emassan.mp4 (H.264 + AAC 48 kHz, two-pass loudnorm -14 LUFS / -1.5 dBTP)
set -e
D=${1:?work dir}
J=$(ffmpeg -hide_banner -i "$D/mix.wav" -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
g() { echo "$J" | python3 -c "import sys,json;print(json.load(sys.stdin)['$1'])"; }
ffmpeg -y -loglevel error -i "$D/video.mp4" -i "$D/mix.wav" -map 0:v -map 1:a -c:v copy \
  -af "loudnorm=I=-13.6:TP=-1.5:LRA=11:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true,alimiter=limit=0.68:level=false:attack=1:release=50,aresample=48000" \
  -c:a aac -b:a 192k -ar 48000 -movflags +faststart -shortest "$D/yondo-reel1-shaharda-yolgiz-emassan.mp4"
echo "$D/yondo-reel1-shaharda-yolgiz-emassan.mp4"
