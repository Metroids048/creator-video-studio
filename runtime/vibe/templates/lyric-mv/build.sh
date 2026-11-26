#!/bin/bash
# build.sh <tag> — every deliverable of a lyric MV from one set of sources, then QA on each.
#   full + short (chorus cut), horizontal (the lead since 2026-10-24: references post their native 16:9 frame full-screen
#   with small in-picture lyrics); VERTICAL=1 adds the embedded 9:16 layout. Variants come from src/config.js via ?variant= — nothing is
#   rewritten between builds. SHARED=<s> clones the first s seconds of full into short instead of re-rendering them.
# Sources edited since the last build → every variant re-renders (default CACHE=--fresh). To re-render only what changed,
# delete those frames in every out/frames-* yourself and run CACHE=--keep ./build.sh v2. Grade/layout-only change →
# just ./vf encode / ./vf vertical, no frames at all.
set -e
cd "$(dirname "$0")"
TAG=${1:?tag, e.g. v1}; N=$(basename "$PWD" | sed -E 's/-[0-9]{8}$//')
dur() { sed -nE "s/^ *'?$1'?: *\{ *duration: *([0-9.]+).*/\1/p" src/config.js | head -1; }
aud() { sed -nE "s/^ *'?$1'?: *\{[^}]*audio: *'([^']+)'.*/\1/p" src/config.js | head -1; }
title=$(sed -nE "s/.*SONG = \{ *title: *'([^']+)', *artist: *'([^']+)'.*/\1/p" src/config.js)
artist=$(sed -nE "s/.*SONG = \{ *title: *'([^']+)', *artist: *'([^']+)'.*/\2/p" src/config.js)
LYSRC=src/lyrics.js; [ -f "$LYSRC" ] || LYSRC=src/karaoke.js   # where `const LY = [...]` lives
lend() { sed -nE "s/^ *'?$1'?: *\{[^}]*lyricsEnd: *([0-9.]+).*/\1/p" src/config.js | head -1; }   # lyrics stop before the end card
reuse() { [ -n "${SHARED:-}" ] && echo "--reuse=out/frames-$1:0:$SHARED"; }

for v in ${VARIANTS:-full short}; do
  [ -f "$(aud $v)" ] || { echo "missing audio $(aud $v) for variant $v (./vf song …, then cut the clip)"; exit 1; }
  ./vf frames --variant=$v ${CACHE:---fresh} $( [ $v != full ] && reuse full )
  ./vf encode out/$N-$TAG-$v.mp4 --variant=$v --audio="$(aud $v)" --grade
  ./vf qa out/$N-$TAG-$v.mp4 --profile=mv --expect="$(dur $v)" || true
  [ "${VERTICAL:-0}" = 1 ] || continue
  # vertical: the same film without its in-film title (and without the end card's text: frames from lyricsEnd on are
  # re-rendered for the -v variant, never copied from the horizontal film), laid out 9:16 with big karaoke lyrics
  ./vf frames --variant=$v-v ${CACHE:---fresh} --reuse=out/frames-$v:4:$(lend $v || true)$( [ -z "$(lend $v)" ] && dur $v )
  ./vf encode out/$N-$TAG-$v-vsrc.mp4 --variant=$v-v --audio="$(aud $v)" --grade
  ./vf ass "$LYSRC" out/lyrics-$v.ass "$(dur $v)" $( [ -n "$(lend $v)" ] && echo "--until=$(lend $v)" )
  ./vf vertical out/$N-$TAG-$v-vsrc.mp4 out/$N-$TAG-$v-vertical.mp4 --crop=1600:966:160:0 --lines \
    --ass=out/lyrics-$v.ass --fonts=assets/fonts --title-text="$title" --sub-text="$artist"
  ./vf qa out/$N-$TAG-$v-vertical.mp4 --profile=mv --vertical --expect="$(dur $v)" || true
done
echo "BUILD_ALL_DONE $TAG — next: ./vf review on the lead file (out/$N-$TAG-short.mp4), then ./vf package"
