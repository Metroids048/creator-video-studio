#!/bin/bash
# acquire.sh <name> "<pasted share text or URLs…>" — download every reference the user gave, then make what you LOOK at.
#   1. pulls every v.douyin.com / douyin.com/video / iesdouyin URL out of the pasted text (share text is fine as-is)
#   2. resolves short links, downloads the public player's media (tools/acquire_reference.mjs: no login, no cookies)
#   3. per video: sheet.jpg (≤48 tiles), hook.jpg (first 3 s at 6 fps), info.txt (duration, size, loudness)
#   4. INDEX.md with an analysis table to fill — the brief cites it, so "看过参考" is checkable
# Output: $VF_PROJECT_ROOT/evidence/refs-<name>-<date>/ . Failures (login wall, timeout) are listed, not hidden.
set -u
KIT=$(cd "$(dirname "$0")/.." && pwd); . "$KIT/bin/env.sh"; vf_need FFMPEG VF_NODE
name=${1:?usage: acquire.sh <name> "<links>"}; shift
OUT="$VF_PROJECT_ROOT/evidence/refs-$name-$(date +%Y%m%d)"; mkdir -p "$OUT"
export VF_PUPPETEER_PKG="$KIT/package.json"
urls=$(printf '%s\n' "$@" | grep -oE 'https?://(v\.douyin\.com|www\.douyin\.com/video|www\.iesdouyin\.com/share/video)/[A-Za-z0-9_/-]+' | sort -u)
[ -n "$urls" ] || { echo "no Douyin links found in the input"; exit 2; }
echo "| # | 链接 | 状态 | 时长 | 文件 |" > "$OUT/INDEX.md"; echo "|---|---|---|---|---|" >> "$OUT/INDEX.md"
k=0
for u in $urls; do
  k=$((k + 1))
  final=$u
  if [[ "$u" == *://v.douyin.com/* ]]; then
    wifi=$(/usr/sbin/networksetup -listallhardwareports | awk '/^Hardware Port: Wi-Fi$/ {getline; if ($2 ~ /^en[0-9]+$/) print $2; exit}')
    if [ -n "$wifi" ]; then
      final=$(/usr/bin/curl --disable --noproxy '*' --proxy '' --interface "if!$wifi" --proto '=https' --proto-redir '=https' \
        --retry 0 --max-filesize 1048576 -s -m 12 -o /dev/null -w '%{url_effective}' -L \
        -A 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)' "https://${u#*://}")
    fi
  fi
  id=$(printf '%s' "$final" | grep -oE '/video/[0-9]{10,}' | head -1 | cut -d/ -f3)
  if [ -z "$id" ]; then echo "| $k | $u | 解析失败（${final}） | | |" >> "$OUT/INDEX.md"; continue; fi
  res=$("$VF_NODE" "$VF_PROJECT_ROOT/tools/acquire_reference.mjs" --url="https://www.douyin.com/video/$id" --out="$OUT" 2>&1 | tail -1)
  f="$OUT/douyin-$id.mp4"
  if [ ! -s "$f" ]; then echo "| ${k} | ${u} | 下载失败：$(printf '%s' "$res" | cut -c1-80) | | |" >> "$OUT/INDEX.md"; continue; fi
  d="$OUT/$id"; mkdir -p "$d"
  dur=$("$FFMPEG" -hide_banner -i "$f" 2>&1 | grep -oE 'Duration: [0-9:.]+' | cut -d' ' -f2)
  secs=$(echo "$dur" | awk -F: '{print int($1*3600+$2*60+$3)}'); [ "${secs:-0}" -lt 1 ] && secs=1
  # ≤48 tiles whatever the length: 1 per second for a short, evenly spaced for a long tutorial
  n=$(( secs < 48 ? secs : 48 )); [ $n -lt 1 ] && n=1
  "$FFMPEG" -hide_banner -loglevel error -y -i "$f" -vf "fps=$n/$secs,scale=240:-1,tile=8x$(( (n + 7) / 8 ))" -frames:v 1 "$d/sheet.jpg"
  "$FFMPEG" -hide_banner -loglevel error -y -t 3 -i "$f" -vf "fps=6,scale=240:-1,tile=6x3" -frames:v 1 "$d/hook.jpg"
  { echo "duration $dur"; "$FFMPEG" -hide_banner -i "$f" 2>&1 | grep -E 'Stream'; "$FFMPEG" -hide_banner -i "$f" -af ebur128 -f null - 2>&1 | grep -E '^\s+I:'; } > "$d/info.txt"
  echo "| $k | $u | OK | $dur | douyin-$id.mp4 · $id/sheet.jpg · $id/hook.jpg |" >> "$OUT/INDEX.md"
  echo "[$k] $id  $dur"
done
cat >> "$OUT/INDEX.md" <<'EOF'

## 拆解（每条看完 sheet.jpg + hook.jpg 后填；写看到的，不写猜的）
| # | 第 1 秒是什么（钩子） | 画法/材质 | 主体与隐喻 | 声音（人声/配乐/音效，看 info 与频谱） | 节奏（切点/分钟） | 值得偷的一招 |
|---|---|---|---|---|---|---|
EOF
echo "REFS_DONE $OUT  ($(grep -c '| OK |' "$OUT/INDEX.md")/$k downloaded) — now Read each sheet.jpg and hook.jpg and fill INDEX.md"
