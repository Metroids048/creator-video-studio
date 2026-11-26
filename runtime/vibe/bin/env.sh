# env.sh — sourced by every kit script. Resolves the tools once so no script hard-codes a path.
# Override any of them by exporting it first: FFMPEG FFPROBE CHROME_PATH VF_PY VF_NODE VF_PROJECT_ROOT.
# Callers set KIT before sourcing.

: "${VF_PROJECT_ROOT:=$(cd "$KIT/../.." && pwd -P)}"
_OC=$HOME/.openclaw/scene-runtime/bin

_first() { for p in "$@"; do [ -n "$p" ] && [ -x "$p" ] && { echo "$p"; return 0; }; done; return 1; }

FFMPEG=$(_first "${FFMPEG:-}" "$(command -v ffmpeg 2>/dev/null)" "$_OC/ffmpeg" \
  "$(ls "$VF_PROJECT_ROOT"/.venv/lib/python*/site-packages/imageio_ffmpeg/binaries/ffmpeg-* 2>/dev/null | head -1)") || true
FFPROBE=$(_first "${FFPROBE:-}" "$(command -v ffprobe 2>/dev/null)" "$_OC/ffprobe" "$(dirname "${FFMPEG:-/x}")/ffprobe") || true
CHROME_PATH=$(_first "${CHROME_PATH:-}" "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  "/Applications/Chromium.app/Contents/MacOS/Chromium" "$(command -v google-chrome 2>/dev/null)" "$(command -v chromium 2>/dev/null)") || true
VF_PY=$(_first "${VF_PY:-}" "$VF_PROJECT_ROOT/.venv/bin/python" "$(command -v python3 2>/dev/null)") || true
VF_NODE=$(_first "${VF_NODE:-}" "$(command -v node 2>/dev/null)" "$_OC/node" \
  "$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node") || true

# ffmpeg first on PATH so child tools (render.mjs, beat_grid.py) find the same binary
if [ -n "$FFMPEG" ]; then PATH="$(dirname "$FFMPEG"):$PATH"; fi
export FFMPEG FFPROBE CHROME_PATH VF_PY VF_NODE VF_PROJECT_ROOT KIT PATH

vf_need() {   # vf_need FFMPEG VF_NODE ... — fail loudly instead of half-running
  for v in "$@"; do eval "[ -n \"\${$v:-}\" ]" || { echo "vibe-film: $v not found — run $KIT/bin/doctor.sh" >&2; exit 3; }; done
}
