#!/bin/bash
set -eu

root=$(cd "$(dirname "$0")/.." && pwd)
ffmpeg="$root/.studio/bin/ffmpeg"
if [ ! -x "$ffmpeg" ]; then
  ffmpeg=ffmpeg
fi

media="$root/examples/media/focus"
mkdir -p "$media"
cd "$media"

"$ffmpeg" -v error -n -f lavfi -i 'testsrc2=size=320x180:rate=30:duration=8.9' \
  -c:v libx264 -pix_fmt yuv420p screen.mp4
"$ffmpeg" -v error -n -f lavfi -i 'color=c=navy:s=320x180' -frames:v 1 -update 1 before.png
"$ffmpeg" -v error -n -f lavfi -i 'color=c=teal:s=320x180' -frames:v 1 -update 1 paused.png
"$ffmpeg" -v error -n -f lavfi -i 'sine=frequency=440:duration=3.5' -c:a pcm_s16be start.aiff
"$ffmpeg" -v error -n -f lavfi -i 'sine=frequency=660:duration=4.2' -c:a pcm_s16be pause.aiff
printf '%s\n' '{"width":320,"height":180,"actions":[]}' > capture.json
