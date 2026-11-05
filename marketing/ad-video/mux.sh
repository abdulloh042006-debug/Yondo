#!/bin/sh
# usage: mux.sh fmt lang
AD=${AD:-/path/to/ad}
f=$1; l=$2; tag=$( [ "$f" = v ] && echo 9x16 || echo 16x9 )
mkdir -p $AD/final
ffmpeg -hide_banner -loglevel error -y -i $AD/out/video-$f-$l.mp4 -i $AD/out/mix-$l.wav \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000" -c:v copy -c:a aac -b:a 192k -ar 48000 -movflags +faststart -shortest \
  $AD/final/yondo-reklama-$l-$tag.mp4 && echo muxed $l $tag
