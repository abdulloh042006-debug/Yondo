#!/bin/sh
# usage: mux.sh fmt lang
AD=/tmp/claude-0/-home-claude/80ed5239-9a87-5b7a-bb32-cb2c8e001f18/scratchpad/ad
f=$1; l=$2; tag=$( [ "$f" = v ] && echo 9x16 || echo 16x9 )
mkdir -p /mnt/user-data/outputs/yondo-ad
ffmpeg -hide_banner -loglevel error -y -i $AD/out/video-$f-$l.mp4 -i $AD/out/mix-$l.wav \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000" -c:v copy -c:a aac -b:a 192k -ar 48000 -movflags +faststart -shortest \
  /mnt/user-data/outputs/yondo-ad/yondo-reklama-$l-$tag.mp4 && echo muxed $l $tag
