#!/bin/bash
# doctor.sh — check (and, with --fix, repair) everything the kit needs. Run first in every new session.
KIT=$(cd "$(dirname "$0")/.." && pwd); . "$KIT/bin/env.sh"
ok=1
row() { printf '  %-14s %s\n' "$1" "$2"; }
bad() { row "$1" "MISSING  $2"; ok=0; }

echo "vibe-film kit: $KIT"
[ -n "$FFMPEG" ] && row ffmpeg "$FFMPEG ($("$FFMPEG" -version | head -1 | cut -d' ' -f3))" || bad ffmpeg "set FFMPEG=…"
[ -n "$FFPROBE" ] && row ffprobe "$FFPROBE" || bad ffprobe "set FFPROBE=…"
if [ -n "$FFMPEG" ]; then
  filters=$("$FFMPEG" -hide_banner -filters 2>/dev/null)
  for f in ass loudnorm ebur128 showspectrumpic blackdetect freezedetect; do
    echo "$filters" | grep -q " $f " || bad "ffmpeg:$f" "filter not built in (ass = libass, needed for vertical karaoke)"
  done
fi
[ -n "$VF_NODE" ] && row node "$VF_NODE ($("$VF_NODE" -v))" || bad node "set VF_NODE=…"
[ -n "$CHROME_PATH" ] && row chrome "$CHROME_PATH" || bad chrome "set CHROME_PATH=…"
[ -n "$VF_PY" ] && row python "$VF_PY ($("$VF_PY" -V 2>&1))" || bad python "set VF_PY=…"
if [ -n "$VF_PY" ] && ! "$VF_PY" -c 'import numpy, scipy' 2>/dev/null; then bad "numpy/scipy" "$VF_PY -m pip install numpy scipy"; fi
if [ -n "$VF_PY" ] && ! "$VF_PY" -c 'import fontTools' 2>/dev/null; then
  if [ "${1:-}" = --fix ]; then "$VF_PY" -m pip install -q fonttools && row fonttools installed; else bad fonttools "run doctor.sh --fix (glyph checks for titles/lyrics)"; fi
fi

if [ ! -d "$KIT/node_modules/puppeteer-core" ] || [ ! -d "$KIT/node_modules/p5.brush" ]; then
  if [ "$1" = --fix ]; then
    SRC=$(ls -d "$VF_PROJECT_ROOT"/outputs/*/node_modules 2>/dev/null | while read d; do [ -d "$d/p5.brush" ] && [ -d "$d/puppeteer-core" ] && echo "$d" && break; done)
    if [ -n "$SRC" ]; then cp -Rc "$SRC" "$KIT/node_modules" && row node_modules "cloned from $SRC"
    elif [ -x "$HOME/.openclaw/scene-runtime/bin/npm" ]; then (cd "$KIT" && "$HOME/.openclaw/scene-runtime/bin/npm" install --no-audit --no-fund) && row node_modules installed
    else bad node_modules "no npm; copy a node_modules with puppeteer-core + p5 + p5.brush into $KIT"; fi
  else bad node_modules "run: $KIT/bin/doctor.sh --fix"; fi
else row node_modules "ok (puppeteer-core $(grep -m1 '"version"' "$KIT/node_modules/puppeteer-core/package.json" | cut -d'"' -f4))"; fi

for f in PermanentMarker-Regular.ttf ShantellSans-VF.ttf $(sed -nE 's/.*"font": *"([^"]+)".*/\1/p' "$KIT"/styles/[!_]*.json); do
  [ -f "$KIT/fonts/$f" ] || bad "font" "$KIT/fonts/$f"
  case $f in Permanent*|Shantell*) ;; *) grep -q "\"$f\"" "$KIT/styles/_metrics.json" || bad "metrics" "$f — run kit/lyrics/font_metrics.py" ;; esac
done
row styles "$(ls "$KIT"/styles/[!_]*.json | wc -l | tr -d ' ') presets, fonts + metrics checked"
fc=$(ls /System/Library/Fonts/Supplemental/Songti.ttc /System/Library/AssetsV2/com_apple_MobileAsset_Font*/*/AssetData/Songti.ttc 2>/dev/null | head -1)
[ -n "$fc" ] && row "Songti SC" "$fc" || row "Songti SC" "not found as a file (Chrome may still have it via the OS) — check the first contact sheet"

free=$(df -g "$VF_PROJECT_ROOT" | awk 'NR==2{print $4}')
row disk "${free}G free on the project volume"
[ "${free:-0}" -lt 15 ] && { echo "  ! under 15G: a 90 s film at 24 fps needs ~3–8G of frames; clean old out/frames first"; ok=0; }

[ $ok = 1 ] && echo "DOCTOR OK" || { echo "DOCTOR FOUND PROBLEMS"; exit 1; }
