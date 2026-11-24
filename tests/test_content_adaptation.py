"""Failure-chain regressions; fixtures are not evidence of creative quality."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import studio


def value_sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


class AdaptationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        original = {'events': [{'id': 'attempt', 'action': 'try', 'result': 'fails'}]}
        target = {'events': [{'id': 'attempt', 'action': 'try again', 'result': 'changes route'}]}
        for name, payload in [('original.json', original), ('story.json', target)]:
            studio.save(self.base / name, payload)
        (self.base / 'scene.js').write_text('/* synthetic renderer */')
        self.brief = {'purpose': 'self-media', 'route': 'code', 'production_stage': 'representative',
            'script': 'Try, fail, change the route.', 'requirements': [{'id': 'payoff', 'text': 'A visible consequence'}],
            'inputs': [{'id': name, 'kind': kind, 'path': path, 'sha256': studio.digest(self.base / path)}
                       for name, kind, path in [('scene', 'scene', 'scene.js'), ('original', 'data', 'original.json'),
                                                 ('story', 'data', 'story.json')]],
            'shots': [{'id': 'main', 'kind': 'code', 'sceneAsset': 'scene', 'sceneAssets': ['story'], 'frames': 60}],
            'audio': {'mode': 'silent'}}
        self.adaptation = {'schema': 1, 'script_sha256': hashlib.sha256(self.brief['script'].encode()).hexdigest(),
            'units': [{'id': 'attempt', 'shot': 'main', 'frames': [0, 60], 'requirements': ['payoff'],
                'source': {'asset': 'original', 'pointer': '/events/@attempt', 'sha256': value_sha(original['events'][0])},
                'target': {'asset': 'story', 'pointer': '/events/@attempt', 'sha256': value_sha(target['events'][0])},
                'goal': 'get there', 'before': 'blocked', 'action': 'try again', 'after': 'new route',
                'reaction': 'changes choice', 'camera': 'show both routes', 'preserve': 'attempt and consequence',
                'changes': 'different destination', 'capability': 'unverified'}]}

    def bound(self):
        self.brief['content_adaptation'] = copy.deepcopy(self.adaptation)
        return self.brief

    def test_shell_only_self_media_cannot_reach_plan_inputs(self):
        with self.assertRaisesRegex(ValueError, '事件改编'):
            studio.check_inputs(self.brief, self.base)

    def test_original_and_changed_units_are_consumed_by_existing_input_check(self):
        studio.check_inputs(self.bound(), self.base)
        self.brief['shots'][0]['sceneAssets'] = []
        with self.assertRaisesRegex(ValueError, '消费'):
            studio.check_inputs(self.brief, self.base)

    def test_new_script_or_uncovered_requirement_invalidates_adaptation(self):
        for change in ('script', 'requirement'):
            brief = copy.deepcopy(self.bound())
            if change == 'script':
                brief['script'] += 'Different ending.'
            else:
                brief['requirements'].append({'id': 'voice', 'text': 'Preserve the voice decision'})
            with self.subTest(change=change), self.assertRaises(ValueError):
                studio.check_inputs(brief, self.base)

    def test_relabelled_story_still_rejects_stale_unit(self):
        self.bound()
        studio.save(self.base / 'story.json', {'events': [{'id': 'attempt', 'action': 'only walking'}]})
        self.brief['inputs'][2]['sha256'] = studio.digest(self.base / 'story.json')
        with self.assertRaisesRegex(ValueError, '事件.*变化'):
            studio.check_inputs(self.brief, self.base)

    def test_unknown_acting_cannot_expand_to_full_film(self):
        self.bound()['production_stage'] = 'full'
        with self.assertRaisesRegex(ValueError, '未验证'):
            studio.check_inputs(self.brief, self.base)

    def test_missing_shot_and_unsupported_acting_are_rejected(self):
        for key, value in [('shot', 'missing'), ('capability', 'unsupported')]:
            brief = copy.deepcopy(self.bound())
            brief['content_adaptation']['units'][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                studio.check_inputs(brief, self.base)

    def test_actual_plan_rejects_stale_adaptation_without_render(self):
        brief = self.bound()
        brief.pop('purpose')
        brief.update(id='adaptation-fixture', title='fixture', width=64, height=64, fps=30)
        brief['shots'][0]['accent'] = '#ffffff'
        brief['script'] += 'changed'
        studio.save(self.base / 'brief.json', brief)
        run = subprocess.run([sys.executable, str(Path(studio.__file__)), 'plan', str(self.base / 'brief.json')],
                             capture_output=True, text=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn('完整文案', run.stderr)

    def test_actual_scene_context_reads_events_without_writing(self):
        studio.save(self.base / 'brief.json', self.bound())
        before = {p.name: p.read_bytes() for p in self.base.iterdir()}
        run = subprocess.run([sys.executable, str(Path(studio.__file__)), 'scene-context',
                              str(self.base / 'brief.json'), '--shot', 'main'], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        self.assertEqual(report['events'][0]['id'], 'attempt')
        self.assertEqual(report['context_shots'], ['main'])
        self.assertFalse(report['quality_verified'])
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.base.iterdir()})

    def test_prepare_preserves_contract_and_does_not_publish_failed_directory(self):
        import video_templates
        root = Path(studio.__file__).resolve().parents[1]
        story = studio.load(root / 'templates/paper-ink-landscape/v1/example.json')
        story['requirements'] = self.brief['requirements']
        story['script'] = self.brief['script']
        story['scenes'][0]['id'] = 'attempt'
        story['content_adaptation'] = copy.deepcopy(self.adaptation)
        unit = story['content_adaptation']['units'][0]
        unit['shot'] = 'paperink'
        unit['source'] = {**unit['source'], 'asset': 'original'}
        unit['target'] = {'file': 'story.json', 'pointer': '/scenes/@attempt',
                          'sha256': value_sha(story['scenes'][0])}
        story['production_stage'] = 'representative'
        story['adaptation_inputs'] = [self.brief['inputs'][1]]
        studio.save(self.base / 'request.json', story)
        report = video_templates.prepare(self.base / 'request.json', self.base / 'prepared')
        prepared = studio.load(report['brief'])
        self.assertEqual(prepared['content_adaptation']['units'][0]['target']['asset'].split('-')[0], 'story')
        studio.check_inputs(prepared, Path(report['brief']).parent)
        story['content_adaptation']['units'][0]['target']['sha256'] = 'stale'
        studio.save(self.base / 'request.json', story)
        with self.assertRaisesRegex(ValueError, '事件.*变化'):
            video_templates.prepare(self.base / 'request.json', self.base / 'failed')
        self.assertFalse((self.base / 'failed').exists())


if __name__ == '__main__':
    unittest.main()
