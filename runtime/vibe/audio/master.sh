#!/bin/bash
# master.sh <in.wav|mp3|m4a> <out.m4a> [LUFS=-14] [TP=-2.0] — loudness for short-video platforms, AAC 256k / 48 kHz stereo.
# Linear gain = min(LUFS target − loudness, TP target − true peak): a song that is already hot ends up a little under
# target instead of being squashed (loudnorm's dynamic fallback pumps music). Only when that would leave it >1 dB short
# does a transient limiter step in (below). A peak over −1 dBTP clips after the platforms' re-encode.
# TP default −2.0 because AAC adds ~0.6 dB of inter-sample overshoot.
set -e
KIT=$(cd "$(dirname "$0")/.." && pwd); . "$KIT/bin/env.sh"; vf_need FFMPEG
in=$1 out=$2 I=${3:--14} TP=${4:--2.0}
[ -f "$in" ] && [ -n "$out" ] || { echo "usage: master.sh <in> <out.m4a> [LUFS] [TP]"; exit 2; }
measure() { "$FFMPEG" -hide_banner -i "$1" -af "loudnorm=I=$I:TP=$TP:print_format=json" -f null - 2>&1 | sed -n '/^{/,/^}/p'; }
field() { echo "$1" | grep "\"$2\"" | cut -d'"' -f4; }
m=$(measure "$in"); mi=$(field "$m" input_i); mtp=$(field "$m" input_tp)
case $mi in ''|-inf) echo "master.sh: no measurable audio in $in" >&2; exit 4 ;; esac
# linear when the peaks allow it; when they would leave the track >1 dB under target (a quiet passage with sharp
# transients: 挪威的森林's intro came out at −18.4 LUFS), push up to +6 dB more and let a fast limiter shave only the
# transient peaks to TP−1 dBFS (sample peak; AAC adds the rest).
read gain lim < <(awk -v i="$I" -v t="$TP" -v mi="$mi" -v mt="$mtp" 'BEGIN { a = i - mi; b = t - mt;
  if (a <= b + 1) printf "%.2f 0\n", (a < b ? a : b); else printf "%.2f %.4f\n", (a < b + 6 ? a : b + 6), exp((t - 1) / 20 * log(10)) }')
chain="volume=${gain}dB"
[ "$lim" != 0 ] && chain="$chain,alimiter=limit=$lim:attack=5:release=60:level=0"
"$FFMPEG" -hide_banner -loglevel error -y -i "$in" -af "$chain,aresample=48000,aformat=channel_layouts=stereo" -c:a aac -b:a 256k "$out"
r=$(measure "$out")
echo "MASTER_DONE $out  ($mi LUFS / $mtp dBTP, gain ${gain} dB$( [ "$lim" != 0 ] && echo " + limiter") → $(field "$r" input_i) LUFS / $(field "$r" input_tp) dBTP after AAC; target $I / $TP)"
