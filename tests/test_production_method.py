"""Real preparation/plan bindings; these do not render or certify a new film."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import video_templates
import studio


class ProductionMethodTest(unittest.TestCase):
    def test_prepare_freezes_executable_prompt_and_plan_consumes_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = video_templates.read(ROOT / 'templates/paper-ink-landscape/v1/example.json')
            source['content_format'] = 'general'
            studio.save(base / 'request.json', source)
            report = video_templates.prepare(base / 'request.json', base / 'prepared')
            brief_path = Path(report['brief'])
            brief = studio.load(brief_path)
            item = next(x for x in brief['inputs'] if x['id'] == 'studio-production-method')
            artifact = brief_path.parent / item['path']
            self.assertEqual(hashlib.sha256(artifact.read_bytes()).hexdigest(), item['sha256'])
            result = studio.plan(brief_path)
            method = result['production_method']
            self.assertEqual(method['status'], 'bound')
            self.assertIn('第一次给用户', method['execution_prompt']['text'])
            self.assertFalse(method['quality_verified'])
            self.assertFalse(list(base.rglob('*.mp4')))
            artifact.write_text(artifact.read_text() + '\n')
            with self.assertRaisesRegex(ValueError, '校验失败'):
                studio.plan(brief_path)

    def test_knowledge_context_carries_verified_v13_source_map(self):
        run = subprocess.run([sys.executable, ROOT / 'scripts/studio.py', 'content-plan',
                              '--format', 'knowledge-song', '--question', '核对既有作品的制作交接'],
                             capture_output=True, text=True, check=True)
        method = json.loads(run.stdout)['development_context']['production_method']
        baseline = method['baseline']
        self.assertEqual(len(baseline['files']), 13)
        self.assertEqual(baseline['status'], 'source_hashes_verified')
        self.assertIn('musicClock', baseline['reuse_map']['music'])
        self.assertFalse(method['quality_verified'])
        self.assertFalse(method['production_authorized'])

    def test_new_production_cannot_drop_prepared_method(self):
        from production_method import require_new
        with self.assertRaisesRegex(ValueError, '制作方法'):
            require_new({'purpose': 'self-media', 'inputs': []}, {}, existing=False)
        self.assertEqual(require_new({'purpose': 'self-media'}, {}, existing=True)['status'],
                         'legacy_unbound')

    def test_import_preserves_frozen_prompt_and_resume_input_check(self):
        from production_method import bind_prepared
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            brief = {'id': 'method-import-fixture', 'inputs': [], 'shots': []}
            bind_prepared({'content_format': 'general'}, brief, base, ROOT)
            expected = (base / 'production-method.json').read_bytes()
            project = base / 'project'
            project.mkdir()
            studio.import_inputs(brief, base / 'brief.json', project)
            self.assertEqual((project / brief['inputs'][0]['path']).read_bytes(), expected)
            from production_method import inspect
            self.assertEqual(inspect(brief, studio.check_inputs(brief, project))['status'], 'bound')
            (base / 'production-method.json').write_text('changed source after import')
            self.assertEqual(inspect(brief, studio.check_inputs(brief, project))['status'], 'bound')
            (project / brief['inputs'][0]['path']).write_text('changed frozen input')
            with self.assertRaisesRegex(ValueError, '校验失败'):
                studio.check_inputs(brief, project)

    def test_actual_make_rejects_missing_method_after_real_stage_confirmation(self):
        import stage_handoff
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            # Structural guard fixture only: make must stop before any media operation.
            (base / 'input.dat').write_text('not media')
            brief = {'id': 'method-guard-fixture', 'route': 'editor', 'purpose': 'self-media',
                     'primary': 'clip', 'operations': [],
                     'inputs': [{'id': 'clip', 'kind': 'video', 'path': 'input.dat',
                                 'sha256': studio.digest(base / 'input.dat')}],
                     'stage_handoff': {'task': str(base / 'task.json')}}
            studio.save(base / 'brief.json', brief)
            task = {'project': brief['id'], 'brief': 'brief.json', 'stages': [
                {'id': 'fixture', 'needs': [], 'fields': ['/' + k for k in brief if k != 'stage_handoff']}]}
            studio.save(base / 'task.json', task)
            stage_handoff.update(base / 'task.json', confirm='fixture')
            run = subprocess.run([sys.executable, ROOT / 'scripts/studio.py', '--mode', 'production',
                                  '--works-root', base / 'works', 'make', base / 'brief.json'],
                                 capture_output=True, text=True, timeout=15)
            self.assertNotEqual(run.returncode, 0)
            self.assertIn('缺少冻结制作方法', run.stderr)
            self.assertFalse((base / 'works').exists())

    def test_invalid_format_does_not_publish_prepared_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = video_templates.read(ROOT / 'templates/paper-ink-landscape/v1/example.json')
            source['content_format'] = 'invalid'
            studio.save(base / 'request.json', source)
            with self.assertRaisesRegex(ValueError, '不支持的内容形式'):
                video_templates.prepare(base / 'request.json', base / 'prepared')
            self.assertFalse((base / 'prepared').exists())


if __name__ == '__main__':
    unittest.main()
