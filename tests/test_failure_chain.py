"""Historical failure mechanisms; synthetic records never certify film quality."""
import copy
from datetime import date
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import video_templates as templates
import studio
import video_review
from review_fixture import reviewed_contract


class FailureChainTest(unittest.TestCase):
    def benchmark(self, published):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        rows = [{'url': 'https://example.test/' + str(i), 'published': published,
                 'likes': 240000, 'source_role': 'original',
                 'mechanism_reviewed': True, 'full_observation': True,
                 'observer_kind': 'human', 'observation_method': 'human_normal_speed',
                 'limitations': [], 'observation_note': 'Synthetic schema only, no real observer'} for i in range(2)]
        (root / 'proof.json').write_text(json.dumps({'sources': rows}))
        for row in rows:
            row.update(evidence='proof.json', evidence_sha256=templates.sha(root / 'proof.json'))
        config = {'threshold_likes': 200000, 'benchmark_policy': {'max_age_years': 3},
                  'benchmarks': {'fixture': rows}}
        return root, config

    def test_old_high_likes_are_not_recent_market_evidence(self):
        for published in ('2008-07-15', '2011-10-07', None, '2030-01-01'):
            root, config = self.benchmark(published)
            with self.subTest(published=published):
                report = templates.benchmark_status('fixture', root, config)
                self.assertFalse(report['qualified'])
                self.assertEqual(len(report['rejected_sources']), 2)

    def test_recent_source_requires_the_date_in_the_bound_original_record(self):
        root, config = self.benchmark(date.today().isoformat())
        self.assertTrue(templates.benchmark_status('fixture', root, config)['qualified'])
        config['benchmarks']['fixture'][0]['published'] = '2008-07-15'
        self.assertFalse(templates.benchmark_status('fixture', root, config)['qualified'])

    def test_routing_cannot_promote_contradictory_or_sampled_original_observation(self):
        for field, value in [('full_observation', False), ('likes', 5), ('observer_kind', 'ai'),
                             ('limitations', ['1fps samples and three audio chunks'])]:
            root, config = self.benchmark(date.today().isoformat())
            original = templates.read(root / 'proof.json')
            original['sources'][0][field] = value
            studio.save(root / 'proof.json', original)
            for row in config['benchmarks']['fixture']:
                row['evidence_sha256'] = templates.sha(root / 'proof.json')
            with self.subTest(field=field):
                self.assertFalse(templates.benchmark_status('fixture', root, config)['qualified'])

    def test_market_pair_alone_does_not_promote_an_engine_to_template(self):
        market = {'qualified': True, 'confirmed_count': 2, 'required_count': 2,
                  'sources': [], 'gap': 0}
        with patch.object(templates, 'benchmark_status', return_value=market):
            result = templates.match('paper-ink-landscape')
            self.assertFalse(result['candidates'])
            self.assertTrue(result['engineering_candidates'])
            self.assertFalse(result['engineering_candidates'][0]['production_evidence']['qualified'])
            with self.assertRaisesRegex(ValueError, '方法|工程'):
                templates.selection_receipt('paper-ink-landscape', '沿山路绕过断桥。',
                                            '16:9', 'paper-ink-landscape')

    def test_engineering_experiment_cannot_silently_expand_to_self_media_full_film(self):
        story = templates.read(ROOT / 'templates/paper-ink-landscape/v1/example.json')
        with tempfile.TemporaryDirectory() as tmp:
            story.update(topic='山路', script='旅人沿山路绕过断桥。')
            story['routing'] = templates.selection_receipt(story['topic'], story['script'], '16:9',
                                                         story['template'], 'engineering_validation')
            source = Path(tmp) / 'story.json'
            source.write_text(json.dumps(story))
            result = templates.prepare(source, Path(tmp) / 'prepared', require_selection=True)
            brief = templates.read(result['brief'])
            brief['purpose'] = 'self-media'
            with self.assertRaisesRegex(ValueError, '代表段|整片'):
                templates.check_binding(brief, require_selection=True)
            brief['production_stage'] = 'representative'
            templates.check_binding(brief, require_selection=True)

    def test_user_original_link_recalls_its_recipe_without_unrelated_engine_fallback(self):
        for url in ('https://v.douyin.com/uUa2tecTyto/',
                    'https://www.douyin.com/video/7697550142720045449'):
            with self.subTest(url=url):
                report = templates.match('照这个形式换内容 ' + url, script='歌词对应道具的变化。')
                self.assertEqual(report['research_references'][0]['id'], 'lyric-prop')
                self.assertIn(url, report['research_references'][0]['matched_reference_urls'])
                self.assertFalse(report['candidates'])
                self.assertFalse(report['engineering_candidates'])
                self.assertEqual(report['research_references'][0]['compatible_production_templates'], [])
                self.assertIn('studio-verse-prop', report['research_references'][0]['archived_production_templates'])

    def test_prepare_blocks_full_experiment_before_writing_any_output(self):
        story = templates.read(ROOT / 'templates/paper-ink-landscape/v1/example.json')
        story.update(topic='山路', script='旅人沿山路绕过断桥。', purpose='self-media')
        story['content_strategy'] = templates.read(ROOT / 'productions/boxcutter-1114/content-plan.json')['content_strategy']
        story['routing'] = templates.selection_receipt(story['topic'], story['script'], '16:9',
                                                     story['template'], 'engineering_validation')
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / 'story.json', Path(tmp) / 'prepared'
            source.write_text(json.dumps(story))
            with self.assertRaisesRegex(ValueError, '代表段|整片'):
                templates.prepare(source, output, require_selection=True)
            self.assertFalse(output.exists())
            story['production_stage'] = 'representative'
            source.write_text(json.dumps(story))
            with self.assertRaisesRegex(ValueError, '事件改编'):
                templates.prepare(source, output, require_selection=True)
            self.assertFalse(output.exists())

    def test_method_proof_requires_exact_component_and_current_full_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            version = root / 'works/fixture/versions/v0001'
            version.mkdir(parents=True)
            (version / 'video.mp4').write_bytes(b'synthetic method contract, not media')
            studio.save(version / 'receipt.json', {'project': 'fixture', 'version': 'v0001',
                'delivery': {'video.mp4': studio.digest(version / 'video.mp4')}})
            source = root / 'starter/figure.js'
            source.parent.mkdir()
            source.write_text('synthetic component, not a real performance')
            consumer = version / 'native/figure.js'
            consumer.parent.mkdir()
            consumer.write_bytes(source.read_bytes())
            market = {'sources': [{'url': 'https://example.test/a'}, {'url': 'https://example.test/b'}]}
            item = {'id': 'fixture', 'version': '1', 'starter': 'starter',
                    'sample': {'work': 'fixture', 'version': 'v0001'}}
            with patch.object(studio, 'ROOT', root):
                base, review = reviewed_contract(studio, version)
                proof = {'template_id': 'fixture', 'template_version': '1',
                         'reference_urls': [s['url'] for s in market['sources']],
                         'video_sha256': studio.digest(version / 'video.mp4'),
                         'review_sha256': studio.digest(base / 'r0001.json'),
                         'reuse_observation': 'Synthetic contract only, no film quality claim',
                         'reused_components': [{'source': str(source.relative_to(root)),
                             'consumer': str(consumer.relative_to(root)), 'sha256': studio.digest(source)}]}
                studio.save(root / 'method.json', proof)
                config = {'method_proofs': {'fixture': {'file': 'method.json',
                           'sha256': studio.digest(root / 'method.json')}}}
                # An identical file placed beside a video is not runtime reuse.
                self.assertFalse(templates.production_evidence(item, market, root, config)['qualified'])
                consumer.write_text('changed component')
                self.assertFalse(templates.production_evidence(item, market, root, config)['qualified'])
                consumer.write_bytes(source.read_bytes())
                review.pop('continuous_review')
                studio.save(base / 'r0002.json', review)
                self.assertFalse(templates.production_evidence(item, market, root, config)['qualified'])

    def test_declared_continuous_review_with_limits_or_wrong_version_stays_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            version = root / 'works/fixture/versions/v0001'
            version.mkdir(parents=True)
            (version / 'video.mp4').write_bytes(b'synthetic contract, not media')
            studio.save(version / 'receipt.json', {'project': 'fixture', 'version': 'v0001',
                'delivery': {'video.mp4': studio.digest(version / 'video.mp4')}})
            with patch.object(studio, 'ROOT', root):
                base, review = reviewed_contract(studio, version)
                for key, value in [('speed', 2), ('range', [0, .5]), ('limitations', ['帧间不可感知']),
                                   ('video_sha256', '0' * 64), ('audio_observed', False),
                                   ('status', 'issue'), ('method', 'ai_normal_speed_av')]:
                    draft = copy.deepcopy(review)
                    draft['continuous_review'][key] = value
                    studio.save(base / 'invalid.json', draft)
                    with self.subTest(key=key):
                        self.assertEqual(video_review.evaluate(studio, version, base / 'invalid.json')['status'], 'blocked')

    def test_sampling_plus_end_of_playback_is_not_complete_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            version = root / 'works/fixture/versions/v0001'
            version.mkdir(parents=True)
            (version / 'video.mp4').write_bytes(b'synthetic contract, not media')
            studio.save(version / 'receipt.json', {'project': 'fixture', 'version': 'v0001',
                'delivery': {'video.mp4': studio.digest(version / 'video.mp4')}})
            with patch.object(studio, 'ROOT', root):
                base, review = reviewed_contract(studio, version)
                review.pop('continuous_review', None)
                review['reviewer']['method'] = '2fps frames + audio chunks + playback ended'
                studio.save(base / 'sampling-only.json', review)
                report = video_review.evaluate(studio, version, base / 'sampling-only.json')
                self.assertEqual(report['status'], 'blocked')
                self.assertTrue(any('连续' in x for x in report['blockers']))


if __name__ == '__main__':
    unittest.main()
