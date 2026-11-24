"""Real review-prepare handoff; generated signals do not establish listening quality."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / '.studio/bin'


class AudioHandoffTest(unittest.TestCase):
    def test_complete_audio_is_bound_without_changing_source_or_granting_review(self):
        for codec, suffix, mode in [('aac', '.m4a', 'stream_copy'),
                                    ('alac', '.wav', 'decoded_pcm'),
                                    (None, None, None)]:
            with self.subTest(codec=codec), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                version = root / 'works/fixture/versions/v0001'
                version.mkdir(parents=True)
                video = version / 'video.mp4'
                command = [str(BIN / 'ffmpeg'), '-v', 'error', '-f', 'lavfi', '-i',
                           'color=blue:s=64x64:r=24:d=1']
                if codec:
                    command += ['-f', 'lavfi', '-i', 'sine=frequency=731:duration=1', '-c:a', codec]
                subprocess.run(command + ['-c:v', 'libx264', str(video)], check=True)
                digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
                source_sha = digest(video)
                (version / 'receipt.json').write_text(json.dumps({
                    'project': 'fixture', 'version': 'v0001',
                    'delivery': {'video.mp4': source_sha}}))
                cli = [sys.executable, str(ROOT / 'scripts/studio.py'), '--mode', 'development',
                       '--works-root', str(root / 'works'), 'review-prepare', 'fixture',
                       '--version', 'v0001']
                first = subprocess.run(cli, check=True, capture_output=True, text=True)
                prepared = json.loads(first.stdout)
                self.assertEqual(prepared['status'], 'pending')
                inputs = prepared['review_inputs']
                self.assertEqual(inputs['full_video'], {'file': str(video.resolve()), 'sha256': source_sha})
                self.assertEqual(inputs['range'], [0, 1])
                self.assertEqual(inputs['playback_speed'], 1)
                self.assertFalse(inputs['review_attested'])
                packet = next((root / 'works/fixture/reviews/v0001').iterdir())
                manifest = json.loads((packet / 'frames.json').read_text())
                self.assertEqual(manifest['source']['video_sha256'], source_sha)
                if codec:
                    audio = manifest['audio_review']
                    file = packet / audio['file']
                    self.assertEqual(file.suffix, suffix)
                    self.assertEqual(audio['mode'], mode)
                    self.assertEqual(audio['sha256'], digest(file))
                    self.assertEqual(manifest['artifacts'][audio['file']], digest(file))
                    self.assertEqual(inputs['independent_full_audio'],
                                     {'file': str(file.resolve()), 'sha256': digest(file)})
                    def samples(path):
                        return subprocess.check_output([str(BIN / 'ffmpeg'), '-v', 'error',
                            '-i', str(path), '-map', '0:a:0', '-c:a', 'pcm_f32le', '-f', 'f32le', '-'])
                    self.assertEqual(samples(video), samples(file))
                    self.assertEqual(audio['scope'], 'full_primary_audio_not_listening_attestation')
                else:
                    self.assertIsNone(manifest['audio_review'])
                    self.assertFalse(manifest['has_audio'])
                    self.assertIsNone(inputs['independent_full_audio'])
                before = {p.relative_to(packet): p.read_bytes() for p in packet.rglob('*') if p.is_file()}
                again = subprocess.run(cli, check=True, capture_output=True, text=True)
                self.assertTrue(json.loads(again.stdout)['reused'])
                self.assertEqual(json.loads(again.stdout)['review_inputs'], inputs)
                self.assertEqual(before, {p.relative_to(packet): p.read_bytes()
                                        for p in packet.rglob('*') if p.is_file()})
                self.assertEqual(digest(video), source_sha)
                self.assertEqual(json.loads(again.stdout)['status'], 'pending')


if __name__ == '__main__':
    unittest.main()
