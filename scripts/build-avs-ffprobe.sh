#!/usr/bin/env bash
# Build the fixed local-file AVS probe from an already downloaded source archive.
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
archive=${1:-"$root/.studio/downloads/ffmpeg-7.1.1.tar.xz"}
expected=733984395e0dbbe5c046abda2dc49a5544e7e0e1e2366bba849222ae9e3a03b1
checksum=$(shasum -a 256 "$archive")
[[ ${checksum%% *} == "$expected" ]] || { echo "FFmpeg source checksum mismatch" >&2; exit 1; }
destination="$root/.studio/bin/avs/ffprobe"
if [[ -e "$destination" ]]; then
    echo "Preserving existing AVS ffprobe: $destination" >&2
    exit 1
fi
mkdir -p "$root/.studio/staging" "$(dirname "$destination")"
build=$(mktemp -d "$root/.studio/staging/ffprobe-build.XXXXXX")
trap 'rm -rf "$build"' EXIT
tar -xf "$archive" -C "$build"
(
    cd "$build/ffmpeg-7.1.1"
    ./configure --disable-autodetect --disable-doc --disable-debug --disable-network \
        --disable-ffmpeg --disable-ffplay --disable-avdevice --disable-avfilter \
        --disable-swscale --disable-swresample --disable-everything \
        --enable-demuxers --enable-parsers --enable-protocol=file \
        --enable-decoder=h264,hevc,av1,vp8,vp9,mpeg4,mjpeg,png,aac,alac,flac,mp3,opus,vorbis,pcm_s16le,pcm_s24le,pcm_f32le
    /usr/bin/make -j "$(sysctl -n hw.logicalcpu)" ffprobe
    ./ffprobe -version
)
install -m 755 "$build/ffmpeg-7.1.1/ffprobe" "$build/ffprobe"
ln "$build/ffprobe" "$destination"
