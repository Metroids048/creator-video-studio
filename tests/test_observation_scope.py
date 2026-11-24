import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import studio
import video_review
from review_fixture import reviewed_contract
import test_video_review


class ObservationScopeTest(unittest.TestCase):
    # Reuse the isolated source setup, without duplicating the parent tests.
    setUp = test_video_review.ReviewGateTest.setUp
    def test_ai_booleans_cannot_upgrade_sampling_to_continuous_av(self):
        base, review = reviewed_contract(studio, self.version)
        review['reviewer']['kind'] = 'ai'
        review['continuous_review']['method'] = 'ai_normal_speed_av'
        studio.save(base / 'claimed.json', review)
        result = video_review.evaluate(studio, self.version, base / 'claimed.json')
        self.assertEqual(result['status'], 'blocked')
        self.assertTrue(any('感知适配器' in reason for reason in result['blockers']))

    def test_full_requirements_are_preserved_in_review_preparation(self):
        brief = {'request': '原要求', 'requirements': [{'id': 'duration', 'text': '90–120秒'},
                 {'id': 'voice', 'text': '排除已否决音色'}], 'content_strategy': {'topic': {
                     'promises': [{'id': 'p', 'text': '结尾兑现开头'}]}}}
        self.assertEqual(video_review.requirements_for(brief),
                         ['原要求', '90–120秒', '排除已否决音色', '结尾兑现开头'])


if __name__ == '__main__':
    unittest.main()
