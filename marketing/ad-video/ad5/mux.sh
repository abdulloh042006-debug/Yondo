#!/bin/sh
# Mux a rendered video with a mix: measure integrated loudness, apply one static gain to -14 LUFS, then a true-peak limiter
# at -1.5 dBTP. (ffmpeg's loudnorm overshot to +1.6 dBFS in the first milliseconds of these clips, so it is not used.)
# Usage: sh ad5/mux.sh <video.mp4> <mix.wav> <out.mp4>
set -e
I=$(ffmpeg -hide_banner -nostats -i "$2" -af ebur128 -f null - 2>&1 | sed -n '/Summary:/,$p' | sed -n 's/^ *I: *\(-*[0-9.]*\) LUFS/\1/p' | head -1)
G=$(python3 -c "print(round(-14 - ($I), 2))")
ffmpeg -loglevel error -y -i "$1" -i "$2" -map 0:v -map 1:a -c:v copy \
  -af "volume=${G}dB,alimiter=limit=0.8:attack=1:release=60:level=false:asc=1,aresample=48000" \
  -c:a aac -b:a 192k -shortest -movflags +faststart "$3"
echo "muxed $3 (input $I LUFS, gain $G dB)"
