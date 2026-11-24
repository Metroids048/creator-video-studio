#!/bin/bash
set -eu
STUDIO=$(cd "$(dirname "$0")/.." && pwd)
usage="用法: scripts/vibe.sh runtime-check | inspect <id> | status <studio-id> | status --native-receipt <receipt> --source-root <root> | gate <id> [--stage plan|build|ship] | --mode production <id> new <lyric-mv|knowledge-short> [style] | <local vf command>（只产出待审候选）"
case "${1:-}" in
  status)
    exec /usr/bin/env -i HOME="$HOME" TMPDIR="${TMPDIR:-/tmp}" LANG="${LANG:-en_US.UTF-8}" \
      PATH="/usr/bin:/bin:/usr/sbin:/sbin" /usr/bin/python3 -B "$STUDIO/scripts/studio.py" "$@" ;;
  runtime-check|inspect|gate)
    exec /usr/bin/env -i HOME="$HOME" TMPDIR="${TMPDIR:-/tmp}" LANG="${LANG:-en_US.UTF-8}" \
      PATH="/usr/bin:/bin:/usr/sbin:/sbin" /usr/bin/python3 -IB "$STUDIO/scripts/vibe.py" "$@" ;;
esac
if [ "${1:-}" = --help ]; then
  echo "$usage"
  exit 0
fi
if [ "${1:-}" != --mode ] || [ "${2:-}" != production ]; then
  echo "Vibe 作品操作需要显式 --mode production。$usage" >&2
  exit 2
fi
shift 2
KIT="$STUDIO/runtime/vibe"
export VF_PROJECT_ROOT="$STUDIO"
export VF_PY="$STUDIO/runtime/vibe-venv/bin/python"
export VF_NODE="$STUDIO/.studio/bin/node"
export FFMPEG="$STUDIO/.studio/bin/ffmpeg"
export FFPROBE="$STUDIO/.studio/bin/ffprobe"
export CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
for tool in "$VF_PY" "$VF_NODE" "$FFMPEG" "$FFPROBE" "$CHROME_PATH"; do
  [ -x "$tool" ] || { echo "Vibe 缺少固定本机工具，请先 runtime-check: $tool" >&2; exit 1; }
done
id=${1:?"$usage"}
[[ "$id" =~ ^[a-z0-9][a-z0-9-]{0,63}$ ]] || exit 2
shift
export FILM_ROOT="$STUDIO/works/vibe-$id"
case "${1:-}" in
  new)
    type=${2:?lyric-mv or knowledge-short}
    case "$type" in lyric-mv) preset=cute; sub=src;; knowledge-short) preset=modern; sub=film;; *) exit 2;; esac
    [ ! -e "$FILM_ROOT" ] || { echo "工程已存在"; exit 1; }
    stage="$FILM_ROOT.setup"
    mkdir "$stage"
    trap 'rm -rf -- "$stage"' EXIT
    cp -R "$KIT/templates/$type/." "$stage/"
    cp "$KIT/web/motion.js" "$stage/$sub/"
    mkdir -p "$stage/assets" "$stage/out/check"
    cp -R "$KIT/fonts" "$stage/assets/fonts"
    if [ "$type" = lyric-mv ]; then
      mkdir -p "$stage/node_modules/p5/lib" "$stage/node_modules/p5.brush/dist"
      cp "$KIT/node_modules/p5/lib/p5.min.js" "$stage/node_modules/p5/lib/"
      cp "$KIT/node_modules/p5.brush/dist/p5.brush.js" "$stage/node_modules/p5.brush/dist/"
      for pkg in p5 p5.brush; do
        find "$KIT/node_modules/$pkg" -maxdepth 1 -iname 'license*' -exec cp {} "$stage/node_modules/$pkg/" \;
      done
    fi
    "$VF_PY" -I "$KIT/lyrics/style.py" "${3:-$preset}" --project="$stage" --type="$type"
    sed -e "s/{NAME}/$id/g" -e "s/{TYPE}/$type/g" -e "s/{DATE}/$(date +%Y-%m-%d)/g" "$KIT/templates/FILM_STATUS.md" > "$stage/FILM_STATUS.md"
    cp "$KIT/templates/发布方案.md" "$stage/发布方案.md"
    mv "$stage" "$FILM_ROOT"
    trap - EXIT
    echo "$FILM_ROOT"
    ;;
  frames|encode|clip|sheet|strip|render|style|lyrics|ass|beats|cut|qa|review|compare|events|score|master|subs|vertical|cover|gate|build)
    exec /usr/bin/env -i HOME="$HOME" TMPDIR="${TMPDIR:-/tmp}" LANG="${LANG:-en_US.UTF-8}" \
      PATH="$STUDIO/.studio/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
      FILM_ROOT="$FILM_ROOT" VF_PROJECT_ROOT="$STUDIO" VF_PY="$VF_PY" VF_NODE="$VF_NODE" \
      FFMPEG="$FFMPEG" FFPROBE="$FFPROBE" CHROME_PATH="${CHROME_PATH:-}" \
      "$KIT/bin/film.sh" "$@" ;;
  *) echo "请指定 new 或本地制作命令。歌曲下载和清理走单独审批。"; exit 2;;
esac
