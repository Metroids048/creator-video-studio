"""Exercise event invariants and the actual frozen-input production path."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import event_templates as events
import studio
import video_templates


class EventTemplatesTest(unittest.TestCase):
    def prepare(self, base, template='object-assembly'):
        data = json.loads((ROOT / 'templates' / template / 'v1/example.json').read_text())
        events.prepare(data, base / 'prepared', ROOT)
        path = base / 'prepared/brief.json'
        return json.loads(path.read_text()), path

    def test_frozen_js_modules_keep_relative_import_filenames(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            brief, path = self.prepare(base)
            project = base / brief['id']
            project.mkdir()
            studio.import_inputs(brief, path, project)
            studio.check_inputs(brief, project)
            shot = {**brief['shots'][0], 'width': 1080, 'height': 1920, 'fps': 30}
            film = base / 'native/film'
            studio.prepare_code_scene(shot, brief, project, film)
            self.assertTrue((film / 'assets/three.module.min.js').is_file())
            self.assertTrue((film / 'assets/three.core.min.js').is_file())
            self.assertIn('./three.core.min.js', (film / 'assets/three.module.min.js').read_text())

    def test_actual_plan_rejects_spoiler_and_missing_event_timeline(self):
        with tempfile.TemporaryDirectory() as tmp:
            brief, path = self.prepare(Path(tmp))
            studio.check_inputs(brief, path.parent)
            brief['shots'][0]['cues'][0]['start'] -= 8
            with self.assertRaisesRegex(ValueError, '字幕或片长'):
                studio.check_inputs(brief, path.parent)
            brief, path = self.prepare_second(Path(tmp))
            brief.pop('eventTimeline')
            with self.assertRaisesRegex(ValueError, '绑定故事'):
                studio.check_inputs(brief, path.parent)

    def prepare_second(self, base):
        data = json.loads((ROOT / 'templates/object-assembly/v1/example.json').read_text())
        events.prepare(data, base / 'second', ROOT)
        path = base / 'second/brief.json'
        return json.loads(path.read_text()), path

    def test_contact_frame_drift_is_blocked_on_real_input_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            brief, path = self.prepare(Path(tmp))
            sync_path = path.parent / 'event-sync.json'
            sync = json.loads(sync_path.read_text())
            sync['events'][0]['frame'] += 1
            sync_path.write_text(json.dumps(sync))
            for item in brief['inputs']:
                if item['id'] == 'event-sync':
                    item['sha256'] = studio.digest(sync_path)
            with self.assertRaisesRegex(ValueError, '接触帧'):
                studio.check_inputs(brief, path.parent)

    def test_no_actor_fallback_or_early_caption(self):
        original = json.loads((ROOT / 'templates/paper-cut-story/v1/example.json').read_text())
        for mutate, error in [(lambda d: d['objects'][0].update(shape='person'), '人物表演'),
                              (lambda d: d['events'][0].update(captionFrame=1), '提前|先于')]:
            data = copy.deepcopy(original)
            mutate(data)
            with self.assertRaisesRegex(ValueError, error):
                events.validate(data)

    def test_archived_existing_parent_remains_valid_for_picture_revision(self):
        version = ROOT / 'works/paper-pocket-1113/versions/v0004'
        brief = json.loads((version / 'brief.json').read_text())
        self.assertEqual(brief['template']['id'], 'paper-cut-story')
        studio.check_inputs(brief, version.parent.parent)
        shot = brief['shots'][0]
        revised = studio.picture_brief(version, {
            'base': version.name, 'shot': shot['id'],
            'visual': {'sceneAsset': shot['sceneAsset']},
        }, preview_only=True)
        self.assertEqual(revised, brief)

    def test_audio_revision_keeps_story_and_picture_and_blocks_wrong_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            brief, path = self.prepare(base)
            project = base / brief['id']
            project.mkdir()
            studio.import_inputs(brief, path, project)
            version = project / 'versions/v0001'
            version.mkdir(parents=True)
            studio.save(version / 'brief.json', brief)
            change = {'base': 'v0000', 'reason': 'material correction',
                      'inputs': [], 'audio': {'mode': 'supplied', 'asset': 'replacement'}}
            change_path = base / 'change.json'
            studio.save(change_path, change)
            with self.assertRaisesRegex(ValueError, '确切父版'):
                studio.audio_brief(version, change_path)
            story = json.loads((project / 'inputs/story.json').read_text())
            source = base / 'material.wav'
            provenance = events.write_material_audio(story, source, ROOT, profile='kenney-recorded-v1')
            self.assertEqual(provenance['profile'], 'kenney-recorded-v1')
            self.assertIn('metal-clang', provenance['sounds'])
            self.assertIn('book-place', provenance['sounds'])
            sync = json.loads((project / 'inputs/event-sync.json').read_text())
            sync.update(audio_sha256=studio.digest(source), source=provenance)
            studio.save(base / 'material-sync.json', sync)
            change.update(base='v0001', inputs=[
                {'id': 'replacement', 'kind': 'audio', 'path': 'material.wav', 'sha256': studio.digest(source)},
                {'id': 'replacement-sync', 'kind': 'data', 'path': 'material-sync.json',
                 'sha256': studio.digest(base / 'material-sync.json')}],
                eventTimeline={**brief['eventTimeline'], 'audio': 'replacement', 'sync': 'replacement-sync'})
            studio.save(change_path, change)
            revised = studio.audio_brief(version, change_path)
            self.assertEqual(revised['shots'], brief['shots'])
            self.assertEqual(revised['eventTimeline']['story'], brief['eventTimeline']['story'])
            studio.check_inputs(revised, project)
            # A forged sync hash cannot hide contact drift on the production gate.
            sync['events'][0]['frame'] += 1
            new_sync = project / 'inputs/replacement-sync.json'
            studio.save(new_sync, sync)
            revised['inputs'][-1]['sha256'] = studio.digest(new_sync)
            with self.assertRaisesRegex(ValueError, '接触帧'):
                studio.check_inputs(revised, project)

    def test_make_blocks_missing_event_binding_before_creating_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            brief, path = self.prepare(Path(tmp))
            brief['id'] = 'reject-event-binding-test'
            # Pass the newer routing gate so this still exercises the original
            # missing-event production guard, before any project is created.
            brief['request'] = 'object-assembly 台灯装配'
            brief['script'] = '底座先放稳，再插入灯杆，安装灯罩，最后点亮一盏台灯。'
            brief['template']['selection'] = video_templates.selection_receipt(
                brief['request'], brief['script'], '9:16', 'object-assembly', 'engineering_validation')
            video_templates.check_binding(brief, require_selection=True)
            brief.pop('eventTimeline')
            path.write_text(json.dumps(brief))
            project = ROOT / 'works' / brief['id']
            self.assertFalse(project.exists())
            run = subprocess.run([sys.executable, ROOT / 'scripts/studio.py', '--mode',
                                  'production', 'make', path], capture_output=True, text=True, timeout=20)
            self.assertNotEqual(run.returncode, 0)
            self.assertIn('绑定故事', run.stderr)
            self.assertFalse(project.exists())
