import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import video_templates as templates


class QualificationTest(unittest.TestCase):
    def test_method_record_does_not_restore_expired_market(self):
        level = templates.qualification({'qualified': False}, {'qualified': True}, True)
        self.assertFalse(level['production_eligible'])
        self.assertTrue(level['adaptation_recorded'])
        self.assertIn('近期市场依据', level['gaps'])

    def test_likes_and_engine_do_not_certify_content(self):
        level = templates.qualification({'qualified': True}, {'qualified': False}, True)
        self.assertEqual(level['tier'], 'engineering_candidate')
        self.assertFalse(level['content_quality_guaranteed'])
        self.assertIn('同版换稿与完整审阅', level['gaps'])

    def test_catalog_and_match_use_same_layers(self):
        inventory = templates.inventory()
        rows = {row['id']: row for row in inventory['templates']}
        result = templates.match('山路', script='旅人沿山路行走，经过断桥再到山顶。')
        self.assertTrue(result['engineering_candidates'])
        for row in result['engineering_candidates']:
            self.assertEqual(row['qualification'], rows[row['id']]['qualification'])
        self.assertEqual(inventory['production_qualified_count'],
                         sum(row['qualification']['production_eligible'] for row in rows.values()))
        self.assertFalse(result['semantic_fit_verified'])


if __name__ == '__main__':
    unittest.main()
