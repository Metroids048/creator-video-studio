#!/bin/bash
# film.sh — the one command per project. Each project has a 3-line ./vf that sets FILM_ROOT and calls this.
#   ./vf doctor                         environment check
#   ./vf sheet 1,5,9 [out.jpg] [--cols=1 --w=1100] [--variant=look-a]   contact sheet at times (or: every:2) → Read it
#   ./vf strip 12:14 [out.jpg]          6 fps motion strip of a stretch                → Read it
#   ./vf clip 0:10 [out.mp4]            fast preview MP4 with sound — the 10-second gate (show the user)
#   ./vf render --any --render.mjs --flags
#   ./vf events | score | master        knowledge short: events.json → score.wav → score.m4a (−14 LUFS)
#   ./vf subs                           SUBS rows → out/subs.json (qa caption_sync; build does it for you)
#   ./vf frames [--variant=v] [--workers=4] [--fresh|--keep]   frames (resumable; refuses a stale cache)
#   ./vf encode <out.mp4> [--variant=v] [--audio=…] [--grade[=name]]
#   ./vf build <tag> [--audio=FILE --audio-sha256=HASH] [--grade=paper] [--keep|--fresh] → candidate + QA
#                                       (--keep: delete the changed frame ranges in out/frames first, the rest is reused)
#   ./vf gate [--stage=plan|build|ship]   did every step happen? (refs, BRIEF, style, storyboard 5 columns, QA, review)
#   ./vf qa <mp4> [--profile=mv] [--vertical] [--expect=46.6]   hard gate → qa-<stem>/qa.json
#   ./vf review <mp4> [--vertical]      6 fps timecoded sheets + REVIEW_TASK.md for a fresh reviewer subagent
#   ./vf compare <mp4> <ref-id|ref.mp4>…   our film vs references, same relative moments, one row each → Read it
#   ./vf vertical <in> <out> [opts]     1080×1920 layout (deliver/vertical.py)
#   ./vf specimen [out.jpg]            every lettering preset on one sheet (choose with the user)
#   ./vf style [<preset>]               list presets / switch the film's lettering (font, sizes, colours) in one place
#   ./vf cover <mp4> out/cover.png --t=S --title=… [--sub= --tagline= --tagline2=]   3:4 封面 1080×1440
#   ./vf package --main=<mp4>,<label> [--also=…] [--cover=…]   发布包/ (refuses un-QA'd files)
#   ./vf clean                          delete frame caches (keeps mp4s, QA, review)
# lyric MV helpers:
#   ./vf song "歌名 歌手" --out=assets    audio + LRC (NetEase public endpoints)
#   ./vf beats assets/song.mp3 --lrc=assets/song.lrc     BPM, beat phase, beat index of every lyric line
#   ./vf cut assets/song.mp3 <start> <dur> assets/clip.m4a   cut on a beat + tail fade + loudness/true-peak master
#   ./vf lyrics assets/song.lrc --start=S --end=E          → src/lyrics.js (clip time)
#   ./vf ass src/lyrics.js out/lyrics.ass <dur>            vertical karaoke subtitles
set -e
KIT=$(cd "$(dirname "$0")/.." && pwd); . "$KIT/bin/env.sh"
ROOT=${FILM_ROOT:?run through the project ./vf wrapper}
NAME=$(basename "$ROOT" | sed -E 's/-[0-9]{8}$//')
cd "$ROOT"
R() { vf_need VF_NODE CHROME_PATH; "$VF_NODE" "$KIT/render.mjs" --root="$ROOT" "$@"; }
outarg() { o=$1; SHIFT=0; shift; case ${1:-} in ''|--*) ;; *) o=$1; SHIFT=1 ;; esac; }   # optional output path before the --flags
STYLE_ARG=; [ -f "$ROOT/style.json" ] && STYLE_ARG=--style="$ROOT/style.json"   # older projects have none: tools fall back
cmd=${1:-help}; shift || true
case $cmd in
  doctor) exec "$KIT/bin/doctor.sh" "$@" ;;
  render|r) R "$@" ;;
  sheet) t=${1:?times}; shift; outarg "out/check/sheet-$(date +%H%M%S).jpg" "$@"; shift $SHIFT; R --sheet="$t" --out="$o" "$@" ;;
  strip) t=${1:?a:b}; shift; outarg "out/check/strip-${t/:/-}.jpg" "$@"; shift $SHIFT; R --strip="$t" --out="$o" "$@" ;;
  clip) t=${1:-0:10}; [ $# -gt 0 ] && shift; outarg "out/check/clip-${t/:/-}.mp4" "$@"; shift $SHIFT; R --clip="$t" --out="$o" "$@" ;;
  events) R --events --out=audio/events.json ;;
  subs) R --subs --out=out/subs.json ;;
  score) vf_need VF_PY; KIT="$KIT" "$VF_PY" -I score.py ;;
  master) "$KIT/audio/master.sh" audio/score.wav audio/score.m4a "$@" ;;
  frames) R --frames "$@" ;;
  encode) o=${1:?out.mp4}; shift; R --encode --out="$o" "$@" ;;
  build)
    tag=${1:?tag, e.g. v1}; shift; o="out/$NAME-$tag.mp4"
    [[ "$tag" != */* && "$tag" != . && "$tag" != .. ]] || { echo 'build: tag must be a version name' >&2; exit 2; }
    [ ! -e "$o" ] || { echo "build: preserving existing $o — use a new version tag; run qa directly to recheck" >&2; exit 2; }
    a=(); lock=(); fr=(); en=(); qa=()
    for x in "$@"; do case $x in
      --audio=*) a=("$x") ;;
      --audio-sha256=*) lock=("$x") ;;
      --variant=*|--fps=*|--frames-dir=*|--keep) fr+=("$x"); en+=("$x") ;;
      --grade|--grade=*|--crf=*) en+=("$x") ;;
      --profile=*|--expect=*|--silent-ok|--vertical) qa+=("$x") ;;
      *) fr+=("$x") ;;
    esac; done
    # An explicit existing performance takes precedence over the optional score composer.
    if [ ${#a[@]} -eq 0 ] && [ -f score.py ]; then
      [ ${#lock[@]} -eq 0 ] || { echo 'build: --audio-sha256 requires explicit --audio' >&2; exit 2; }
      R --events --out=audio/events.json
      KIT="$KIT" "$VF_PY" -I score.py
      "$KIT/audio/master.sh" audio/score.wav audio/score.m4a
      a=(--audio=audio/score.m4a)
    fi
    # Fail cheap stages first; unchanged frames resume by default using the renderer's source stamp.
    R --subs --out=out/subs.json
    R --frames ${a[@]+"${a[@]}"} ${lock[@]+"${lock[@]}"} ${fr[@]+"${fr[@]}"}
    R --encode --out="$o" ${a[@]+"${a[@]}"} ${lock[@]+"${lock[@]}"} ${en[@]+"${en[@]}"}
    "$VF_PY" -I "$KIT/qa/qa_film.py" "$o" ${qa[@]+"${qa[@]}"}
    echo "BUILD_CANDIDATE $o — technical QA completed; content and complete audiovisual review still required" ;;
  gate) vf_need VF_PY; "$VF_PY" -I "$KIT/qa/gate.py" "$ROOT" "$@" ;;
  qa) vf_need VF_PY FFMPEG; "$VF_PY" -I "$KIT/qa/qa_film.py" "$@" ;;
  compare) vf_need VF_PY FFMPEG; FFMPEG="$FFMPEG" VF_PROJECT_ROOT="$VF_PROJECT_ROOT" "$VF_PY" -I "$KIT/qa/compare.py" "$@" ;;
  review) vf_need VF_PY FFMPEG; "$VF_PY" -I "$KIT/qa/review.py" "$@" ;;
  vertical) vf_need VF_PY FFMPEG; "$VF_PY" -I "$KIT/deliver/vertical.py" $STYLE_ARG "$@" ;;
  cover) vf_need VF_PY FFMPEG; "$VF_PY" -I "$KIT/deliver/cover.py" $STYLE_ARG "$@" ;;
  specimen) vf_need VF_PY FFMPEG; "$VF_PY" -I "$KIT/lyrics/specimen.py" "${1:-out/check/specimen.jpg}" ;;
  style) vf_need VF_PY; t=lyric-mv; [ -d film ] && t=knowledge-short; "$VF_PY" -I "$KIT/lyrics/style.py" "${1:-list}" --project="$ROOT" --type=$t ;;
  package) vf_need VF_PY; "$VF_PY" -I "$KIT/deliver/package.py" "$ROOT" "$@" ;;
  beats) vf_need VF_PY FFMPEG; "$VF_PY" -I "$KIT/audio/beat_grid.py" "$@" ;;
  lyrics) vf_need VF_PY; "$VF_PY" -I "$KIT/lyrics/lrc_clip.py" "$@" ;;
  ass) vf_need VF_PY; "$VF_PY" -I "$KIT/lyrics/make_ass.py" "$@" $STYLE_ARG ;;
  song) vf_need VF_PY; "$VF_PY" -I "$KIT/lyrics/fetch_song.py" "$@" ;;
  cut) "$KIT/audio/cut_clip.sh" "$@" ;;
  clean) du -sh out/frames* 2>/dev/null || true; rm -rf out/frames out/frames-*; echo "frame caches removed" ;;
  *) sed -n '2,28p' "$0" ;;
esac
