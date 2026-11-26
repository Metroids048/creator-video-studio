#!/bin/bash
# new_film.sh <knowledge-short|lyric-mv> <name> [--style=<preset>] — scaffold outputs/<name>-<YYYYMMDD>/ from the template.
# The project gets: ./vf (kit entry), BRIEF.md, FILM_STATUS.md, the template's sources, and its lettering style
# (style.json + style.js; default cute for lyric-mv, modern for knowledge-short — pick by the film's tone, see
# `kit/lyrics/style.py list`; switch later with ./vf style <preset>).
set -e
KIT=$(cd "$(dirname "$0")/.." && pwd); . "$KIT/bin/env.sh"
type=${1:?knowledge-short | lyric-mv}; name=${2:?name}; style=
for a in "$@"; do case $a in --style=*) style=${a#--style=} ;; esac; done
[ -n "$style" ] || { [ "$type" = lyric-mv ] && style=cute || style=modern; }
[ -d "$KIT/templates/$type" ] || { echo "unknown type $type"; exit 2; }
DIR="$VF_PROJECT_ROOT/outputs/$name-$(date +%Y%m%d)"
[ -e "$DIR" ] && { echo "exists: $DIR"; exit 1; }
cp -R "$KIT/templates/$type" "$DIR"
if [ "$type" = lyric-mv ]; then cp "$KIT/web/motion.js" "$DIR/src/"; else cp "$KIT/web/motion.js" "$DIR/film/"; fi   # shared motion vocabulary
cat > "$DIR/vf" <<EOF
#!/bin/bash
export FILM_ROOT=\$(cd "\$(dirname "\$0")" && pwd)
exec "$KIT/bin/film.sh" "\$@"
EOF
chmod +x "$DIR/vf"
[ "$type" = lyric-mv ] && ln -s "$KIT/node_modules" "$DIR/node_modules"
mkdir -p "$DIR/assets" && ln -s "$KIT/fonts" "$DIR/assets/fonts"
"$VF_PY" -I "$KIT/lyrics/style.py" "$style" --project="$DIR" --type="$type"
cp "$KIT/templates/发布方案.md" "$DIR/发布方案.md"
sed -e "s/{NAME}/$name/g" -e "s/{TYPE}/$type/g" -e "s/{DATE}/$(date +%Y-%m-%d)/g" "$KIT/templates/FILM_STATUS.md" > "$DIR/FILM_STATUS.md"
mkdir -p "$DIR/out/check"
echo "NEW_FILM $DIR"
