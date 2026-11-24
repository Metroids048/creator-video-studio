#!/bin/bash
set -eu
root=$(cd "$(dirname "$0")/.." && pwd)
mode=design
if [ "${1:-}" = --mode ]; then
  mode=${2:-}
  case "$mode" in
    design|research|development|production|delivery) shift 2 ;;
    *) echo "未知工作室执行模式" >&2; exit 2 ;;
  esac
fi
case "${1:-}:${2:-}" in
  --help:|--version:|runtime-check:|episode:status|episode:validate|assets:list|assets:validate|\
  stage-check:*|reference:validate|content:validate|workflow:status|workflow:next|timeline:validate|validate-script:*) ;;
  ingest:*|plan:*|adopt-analysis:*|adopt-visual-review:*|adopt-creative-review:*|adopt-approval:*|preview:*|final-render:*|qa:*|creative-review:*|deliver:*|export:*|episode:create|assets:approve|content:init|content:approve|timeline:build|subtitles:build)
    if [ "$mode" != production ]; then
      echo "修改 AVS 作品需要显式 --mode production，请放在子命令前" >&2
      exit 2
    fi ;;
  doctor:*)
    echo "AVS 原诊断含目录写入和凭据检查；工作室请用 scripts/studio.py doctor" >&2
    exit 2 ;;
  *)
    echo "当前工作室只启用 AVS 的本地检查、合同写回和受保护原生阶段。旧模型、自动续跑及自动 TTS 未接入。" >&2
    exit 2 ;;
esac
cd "$root/runtime/avs"
if [ "${1:-}" = runtime-check ]; then
  set -- "$root/scripts/avs-runtime-check.py"
elif [ "${1:-}" = stage-check ]; then
  shift
  set -- "$root/scripts/avs-stage.py" --check "$@"
elif [ "${1:-}" = preview ] || [ "${1:-}" = final-render ] || [ "${1:-}" = qa ] || [ "${1:-}" = creative-review ] || [ "${1:-}" = deliver ] || [ "${1:-}" = export ]; then
  operation=$1
  if [ "$operation" = qa ]; then operation=technical-qa; fi
  shift
  set -- "$root/scripts/avs-stage.py" --mode production "$operation" "$@"
elif [ "${1:-}" = plan ]; then
  shift
  set -- "$root/scripts/avs-plan.py" --mode production "$@"
elif [ "${1:-}" = adopt-analysis ] || [ "${1:-}" = adopt-visual-review ] || [ "${1:-}" = adopt-creative-review ] || [ "${1:-}" = adopt-approval ]; then
  operation=analyze
  if [ "$1" = adopt-visual-review ]; then operation=visual-review; fi
  if [ "$1" = adopt-creative-review ]; then operation=creative-gate; fi
  if [ "$1" = adopt-approval ]; then operation=approve; fi
  shift
  set -- "$root/scripts/avs-adopt.py" --mode production "$operation" "$@"
else
  set -- -m avs "$@"
fi
exec /usr/bin/env -i HOME="$HOME" TMPDIR="${TMPDIR:-/tmp}" LANG="${LANG:-en_US.UTF-8}" \
  PATH="$root/runtime/avs-venv/bin:$root/.studio/bin/avs:$root/.studio/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
  PYTHONPATH="$PWD/src" PYTHONDONTWRITEBYTECODE=1 npm_config_offline=true HYPERFRAMES_NO_TELEMETRY=1 \
  HYPERFRAMES_BROWSER_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  "$root/runtime/avs-venv/bin/python" "$@"
