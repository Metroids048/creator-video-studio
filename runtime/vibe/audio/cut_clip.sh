#!/bin/bash
# cut_clip.sh <song> <start> <dur> <out.m4a> [fade=1.8] [LUFS=-13] — the MV's audio clip: cut on a beat, fade the tail,
# master to the platform loudness with true-peak headroom (a raw cut of a commercial master peaks at 0 dBTP → QA FAIL).
set -e
KIT=$(cd "$(dirname "$0")/.." && pwd); . "$KIT/bin/env.sh"; vf_need FFMPEG
song=$1 start=$2 dur=$3 out=$4 fade=${5:-1.8} lufs=${6:--13}
[ -f "$song" ] && [ -n "$out" ] || { echo "usage: cut_clip.sh <song> <start> <dur> <out.m4a> [fade] [LUFS]"; exit 2; }
tmp=$(mktemp -d)/clip.wav
st=$(awk -v d="$dur" -v f="$fade" 'BEGIN { x = d - f; printf "%.3f", (x > 0 ? x : 0) }')
"$FFMPEG" -hide_banner -loglevel error -y -ss "$start" -t "$dur" -i "$song" \
  -af "afade=t=in:d=0.02,afade=t=out:st=$st:d=$fade" -ar 48000 -c:a pcm_s16le "$tmp"
"$KIT/audio/master.sh" "$tmp" "$out" "$lufs" -2.0
rm -rf "$(dirname "$tmp")"
