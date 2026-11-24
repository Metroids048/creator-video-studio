import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import studio
import video_templates as templates
import content_adaptation


class ConsumptionTest(unittest.TestCase):
    def test_unused_copy_is_rejected_and_adapted_native_input_is_bound(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            version = root / 'works/test/versions/v0001'
            native = version / 'shots/main/film'
            native.mkdir(parents=True)
            source = root / 'starter/scene.js'; source.parent.mkdir()
            source.write_text('original')
            consumer = native / 'scene.js'; consumer.write_text('adapted')
            brief = {'inputs': [{'id': 'scene', 'sha256': studio.digest(consumer)}],
                     'shots': [{'id': 'main', 'sceneAsset': 'scene'}],
                     'content_adaptation': {'units': [{'id': 'event', 'shot': 'main'}]}}
            studio.save(version / 'brief.json', brief)
            studio.save(native.parent / 'scene-source.json', {'asset': 'scene'})
            component = {'source': 'starter/scene.js', 'consumer': str(consumer.relative_to(root)),
                         'source_sha256': studio.digest(source), 'consumer_sha256': studio.digest(consumer),
                         'shot': 'main', 'input': 'scene', 'events': ['event'], 'changes': 'new content'}
            with self.assertRaisesRegex(ValueError, '消费回执'):
                templates.check_component(component, root, root / 'starter', version)
            content_adaptation.record_consumption(brief, brief['shots'][0], native)
            templates.check_component(component, root, root / 'starter', version)
            consumer.write_text('changed again')
            with self.assertRaises(ValueError):
                templates.check_component(component, root, root / 'starter', version)


if __name__ == '__main__':
    unittest.main()
