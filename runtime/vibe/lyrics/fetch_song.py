"""fetch_song.py "<歌名 歌手>" [--id=N] [--out=assets] — song audio + timed lyrics for a lyric MV.

Uses NetEase Cloud Music's public endpoints (no login): api/search/get → song list, api/song/lyric → LRC,
song/media/outer/url → audio. Only fee 0/8 songs download (fee 1 = VIP: the redirect returns a 404 page).
The user's standing instruction (2026-10-22): find the audio yourself, copyright is out of scope for the draft;
the publish plan must still say "发布时在平台里挂官方音源" — the downloaded track is often a 128 kbps preview.
Writes OUT/song.mp3, OUT/song.lrc, OUT/song.json (id, name, artists, fee, duration, bitrate).
"""
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

argv = [a for a in sys.argv[1:] if not a.startswith('--')]
opt = dict((a[2:].split('=', 1) + [True])[:2] for a in sys.argv[1:] if a.startswith('--'))
if not argv and 'id' not in opt:
    sys.exit(__doc__)
out = Path(opt.get('out', 'assets'))
out.mkdir(parents=True, exist_ok=True)
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)', 'Referer': 'https://music.163.com/'}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return r.read(), r.headers.get('Content-Type', ''), r.geturl()


song = None
if argv:
    q = urllib.parse.quote(argv[0])
    songs = json.loads(get(f'https://music.163.com/api/search/get?s={q}&type=1&limit=12')[0])['result']['songs']
    for s in songs:
        print(f"{s['id']:>12}  fee={s.get('fee')}  {s['duration'] / 1000:6.1f}s  {s['name']} — {'/'.join(a['name'] for a in s['artists'])}")
    pick = [s for s in songs if str(s['id']) == str(opt.get('id'))] or [s for s in songs if s.get('fee') in (0, 8)]
    if not pick:
        sys.exit('no downloadable (fee 0/8) version — try another query or pass --id=')
    song = pick[0]
sid = song['id'] if song else int(opt['id'])

lrc = json.loads(get(f'https://music.163.com/api/song/lyric?id={sid}&lv=1&kv=1&tv=-1')[0])
(out / 'song.lrc').write_text(lrc.get('lrc', {}).get('lyric', ''), encoding='utf-8')
if lrc.get('tlyric', {}).get('lyric'):
    (out / 'song.translation.lrc').write_text(lrc['tlyric']['lyric'], encoding='utf-8')

data, ctype, final = get(f'https://music.163.com/song/media/outer/url?id={sid}.mp3')
if 'audio' not in ctype and len(data) < 500_000:
    sys.exit(f'audio download refused ({ctype}, {len(data)} bytes, {final[:80]}) — VIP-only; pick a fee 0/8 version with --id=')
(out / 'song.mp3').write_bytes(data)
probe = subprocess.run([os.environ.get('FFMPEG') or 'ffmpeg', '-hide_banner', '-i', str(out / 'song.mp3')], capture_output=True, text=True).stderr
br = next((l.split('bitrate:')[1].strip() for l in probe.splitlines() if 'bitrate:' in l), '?')
meta = {'id': sid, 'name': song and song['name'], 'artists': song and [a['name'] for a in song['artists']],
        'fee': song and song.get('fee'), 'duration': song and song['duration'] / 1000, 'bitrate': br, 'source': 'music.163.com public endpoints'}
(out / 'song.json').write_text(json.dumps(meta, ensure_ascii=False, indent=1))
print(f"SONG_DONE {out}/song.mp3 ({len(data) / 1e6:.1f} MB, {br}) + song.lrc ({len(lrc.get('lrc', {}).get('lyric', '').splitlines())} lines)")
