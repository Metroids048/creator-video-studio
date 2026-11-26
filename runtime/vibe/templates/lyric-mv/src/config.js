// config.js — song settings and build variants. The variant comes from the URL (?variant=short, which
// `./vf frames --variant=short` passes), so builds never rewrite this file: a failed build can't leave it wrong.
const SONG = { title: '歌名', artist: '歌手', clipStart: 0 };   // clipStart = song seconds at clip 0, on a beat (./vf beats)
const VARIANTS = {
  full: { duration: 11, audio: 'assets/clip.m4a' },   // add lyricsEnd: <s> once the film has an end card (vertical lyrics stop there)
  short: { duration: 11, audio: 'assets/clip-short.m4a' },                   // chorus cut (≤60 s): the 抖音 lead
  'full-v': { duration: 11, audio: 'assets/clip.m4a', noTitle: true },       // vertical sources: the vertical layout
  'short-v': { duration: 11, audio: 'assets/clip-short.m4a', noTitle: true }, // carries its own big title
};
const VARIANT = new URLSearchParams(location.search).get('variant') || 'full';
const PROJECT = Object.assign({ bpm: 120, offset: 0, variant: VARIANT }, VARIANTS[VARIANT]);
