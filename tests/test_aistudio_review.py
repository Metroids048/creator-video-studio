"""Synthetic evidence contracts, not real media or perceptual quality tests."""
import json
import unittest

import test_video_review
from review_fixture import reviewed_contract
import studio
import video_review


class AIStudioReviewTest(unittest.TestCase):
    setUp = test_video_review.ReviewGateTest.setUp

    def review(self):
        base, review = reviewed_contract(studio, self.version)
        (self.version / 'audio.m4a').write_bytes(b'synthetic primary audio')
        report = {'modalities_received': ['video_frames', 'audio_track'], 'range': [0, 1], 'speed': 1,
                  'segments': [{'start': 0, 'end': 1, 'visual': 'fixture', 'audio': 'fixture',
                                'synchronization': 'fixture'}], 'limitations': ['synthetic precision limit']}
        capture = {'url': 'https://aistudio.google.com/prompts/synthetic', 'free': True,
                   'model': 'synthetic model', 'report_turn': 'synthetic-response',
                   'captured_at': 'synthetic capture, not an actual browser run',
                   'run_state': 'Response ready.',
                   'setup': {'fields_after': [{'label': 'Start Time', 'value': '0s'},
                                             {'label': 'End Time', 'value': '1s'},
                                             {'label': 'FPS', 'value': '24'}]},
                   'hashes': {'state': 'done', 'files': [
                       {'sha256': review['source']['video_sha256']},
                       {'sha256': studio.digest(self.version / 'audio.m4a')}]},
                   'code': [json.dumps(report)]}
        audio = {'url': 'https://aistudio.google.com/prompts/synthetic-blind', 'free': True,
                 'model': 'synthetic model', 'report_turn': 'synthetic-audio-response',
                 'captured_at': 'synthetic capture',
                 'run_state': 'Response ready.',
                 'upload': {'state': 'uploaded_to_ui', 'sha256': studio.digest(self.version / 'audio.m4a')},
                 'code': [json.dumps({'modalities_received': ['audio'], 'segments': [
                     {'time_range': '0-1秒', 'vocal_content': 'synthetic', 'accompaniment': 'synthetic'}]})]}
        studio.save(base / 'av-capture.json', capture)
        studio.save(base / 'audio-capture.json', audio)
        (base / 'cross-check.md').write_text('Synthetic cross-check; no real observation.')
        receipt = {'schema': 1, 'adapter': 'aistudio_full_av_v1', 'source': review['source'],
                   'capture': 'av-capture.json', 'audio_capture': 'audio-capture.json',
                   'cross_check': 'cross-check.md', 'unresolved_observation_conflicts': [],
                   'evidence': {name: studio.digest(base / name) for name in
                                ('av-capture.json', 'audio-capture.json', 'cross-check.md')},
                   'observation': 'Synthetic contract only; not real video review.'}
        studio.save(base / 'ai-av.json', receipt)
        review['reviewer'] = {'kind': 'ai', 'name': 'synthetic model', 'method': 'native video and independent full audio'}
        review['continuous_review'].update(method='ai_normal_speed_av', attestation='ai-av.json',
            limitations=report['limitations'], evidence={'ai-av.json': studio.digest(base / 'ai-av.json')})
        return base, review, capture, audio, receipt

    def evaluate(self, base, review):
        studio.save(base / 'new.json', review)
        return video_review.evaluate(studio, self.version, base / 'new.json')

    def test_complete_ai_review_with_quality_issues_is_complete_but_not_deliverable(self):
        base, review, *_ = self.review()
        review['checks'][0]['status'] = 'issue'
        result = self.evaluate(base, review)
        self.assertEqual(result['review_completion'], 'complete')
        self.assertEqual(result['quality_status'], 'issues')
        self.assertEqual(result['status'], 'blocked')
        self.assertEqual(result['observation_scope'], 'ai_full_video_24fps_and_independent_full_audio')
        self.assertFalse(any('待审' in x for x in result['blockers']))
        self.assertEqual(result['observation_limits'], ['synthetic precision limit'])
        video_review.save(studio, self.version, base / 'new.json')
        with self.assertRaisesRegex(ValueError, '审阅已完成，质量交付被阻止'):
            video_review.require(studio, self.version)

    def test_review_save_accepts_the_prepared_audio_and_rejects_other_uploads(self):
        base, review, capture, audio, receipt = self.review()
        (self.version / 'audio.m4a').unlink()
        handoff_file = base / 'audio-review.m4a'
        handoff_file.write_bytes(b'synthetic full audio extracted from the candidate')
        sha = studio.digest(handoff_file)
        packet = studio.load(base / 'frames.json')
        packet['audio_review'] = {'file': handoff_file.name, 'sha256': sha}
        packet['artifacts'][handoff_file.name] = sha
        studio.save(base / 'frames.json', packet)
        review['packet_sha256'] = studio.digest(base / 'frames.json')
        capture['hashes']['files'][1]['sha256'] = sha
        studio.save(base / 'av-capture.json', capture)
        for expected, uploaded in [('incomplete', '0' * 64), ('complete', sha)]:
            with self.subTest(expected=expected):
                audio['upload']['sha256'] = uploaded
                studio.save(base / 'audio-capture.json', audio)
                receipt['evidence'].update({name: studio.digest(base / name) for name in
                                            ('av-capture.json', 'audio-capture.json')})
                studio.save(base / 'ai-av.json', receipt)
                review['continuous_review']['evidence']['ai-av.json'] = studio.digest(base / 'ai-av.json')
                self.assertEqual(self.evaluate(base, review)['review_completion'], expected)
        video_review.save(studio, self.version, base / 'new.json')
        self.assertEqual(video_review.status(studio, self.version)['review_completion'], 'complete')

    def test_low_fps_wrong_media_gaps_and_unresolved_conflicts_cannot_complete_review(self):
        for defect in ('fps', 'video', 'audio', 'range', 'missing_audio_segment', 'limits', 'running', 'conflict'):
            with self.subTest(defect=defect):
                base, review, capture, audio, receipt = self.review()
                if defect == 'fps':
                    capture['setup']['fields_after'][2]['value'] = '1'
                elif defect == 'video':
                    capture['hashes']['files'][0]['sha256'] = '0' * 64
                elif defect == 'audio':
                    audio['upload']['sha256'] = '0' * 64
                elif defect == 'range':
                    r = json.loads(capture['code'][0]); r['segments'][0]['end'] = .5
                    capture['code'] = [json.dumps(r)]
                elif defect == 'missing_audio_segment':
                    r = json.loads(audio['code'][0]); r['segments'] = []; audio['code'] = [json.dumps(r)]
                elif defect == 'limits':
                    review['continuous_review']['limitations'] = []
                elif defect == 'running':
                    capture['run_state'] = 'Running'
                else:
                    receipt['unresolved_observation_conflicts'] = ['unverified claim']
                studio.save(base / 'av-capture.json', capture)
                studio.save(base / 'audio-capture.json', audio)
                receipt['evidence'].update({name: studio.digest(base / name) for name in
                                           ('av-capture.json', 'audio-capture.json')})
                studio.save(base / 'ai-av.json', receipt)
                review['continuous_review']['evidence']['ai-av.json'] = studio.digest(base / 'ai-av.json')
                result = self.evaluate(base, review)
                self.assertEqual(result['review_completion'], 'incomplete')
                self.assertEqual(result['status'], 'blocked')

    def test_captured_report_mutation_invalidates_saved_review(self):
        base, review, *_ = self.review()
        studio.save(base / 'new.json', review)
        video_review.save(studio, self.version, base / 'new.json')
        capture = studio.load(base / 'av-capture.json'); capture['model'] = 'changed'
        studio.save(base / 'av-capture.json', capture)
        self.assertEqual(video_review.status(studio, self.version)['status'], 'pending')


if __name__ == '__main__':
    unittest.main()
