"""Read-only editorial entry regressions; these do not grade creative quality."""
import json
import hashlib
from pathlib import Path
import subprocess
import tempfile
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


class OriginalDevelopmentTest(unittest.TestCase):
    def run_cli(self, *args):
        run = subprocess.run([sys.executable, str(ROOT / 'scripts/studio.py'), *args],
                             capture_output=True, text=True, check=True)
        return json.loads(run.stdout)

    def test_original_topic_starts_with_reference_scope(self):
        result = self.run_cli('intent', '想做一些原创一点的视频，主题是收藏很多方法却没有行动')
        self.assertEqual(result['next'], 'select_reference_and_scope')
        self.assertIn('research_references', result['template_match'])
        self.assertFalse(result['template_match']['auto_selected'])
        self.assertIn('具体参考', result['creation_order'][0])
        self.assertFalse(result['render_started'])
        self.assertFalse(result['execution_authorized_by_route'])

    def test_reference_first_applies_to_existing_full_script(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / 'script.txt'
            script.write_text('第一段解释原因。第二段用事实证明，结尾给出适用边界。')
            result = self.run_cli('intent', '做一个知识短片', '--script-file', str(script))
        self.assertEqual(result['next'], 'select_reference_and_scope')
        self.assertTrue(result['template_match']['script_sha256'])

    def test_explicit_template_keeps_fixed_adaptation(self):
        result = self.run_cli('intent', '沿用指定模板换脚本，做一个知识短片')
        self.assertEqual(result['next'], 'adapt_within_fixed_template')
        self.assertFalse(result['execution_authorized_by_route'])

    def test_reference_study_does_not_become_production(self):
        result = self.run_cli('intent', '研究若卿的参考形式，先别做视频')
        self.assertEqual(result['profile'], 'reference')
        self.assertEqual(result['next'], 'reference_to_shot_rules')
        self.assertFalse(result['render_started'])

    def test_direct_workflow_plan_uses_reference_first(self):
        with tempfile.TemporaryDirectory() as directory:
            task = Path(directory) / 'task.json'
            task.write_text(json.dumps({'action': 'plan', 'request': '主题：收藏方法却没有行动'}))
            result = self.run_cli('--mode', 'design', 'workflow', str(task))
        self.assertEqual(result['next'], 'select_reference_and_scope')
        self.assertFalse(result['template_route']['auto_selected'])
        self.assertFalse(result['render_started'])

    def test_project_correction_is_maintenance_not_new_creation(self):
        result = self.run_cli('intent', '希望原创视频，但现在先改项目，别着急做视频了')
        self.assertEqual(result['profile'], 'framework')
        self.assertEqual(result['suggested_mode'], 'development')
        self.assertFalse(result['template_match']['applicable'])
        self.assertFalse(result['render_started'])

    def test_project_retrospective_does_not_request_publication_metrics(self):
        requests = [
            '对整个视频制作项目做项目级复盘，核 GitHub 仓库、Skills、能力模块和设计；先扎实原创内容模块，先别做视频',
            '复盘整个项目的设计和能力，不能等真实任务失败了再发现问题',
            '我们这一次只针对于项目级复盘的一个任务',
            '偏向于整体系统性工程化的一些复盘，希望把工作流程迭代优化，后续不同主题首轮接近V13质量',
            '做制作工作流复盘，不是这条视频的播放数据复盘',
            '只是让你对整体内容复盘，除了这次还有之前几个任务，针对于我们整个的视频工作流程',
        ]
        for request in requests:
            with self.subTest(request=request):
                result = self.run_cli('intent', request)
                self.assertEqual(result['profile'], 'framework')
                self.assertEqual(result['next'], 'inspect_framework')
                self.assertNotIn('analytics', result['packs'])
                self.assertIn('docs/制作配方/视频制作工作流.md', result['packs']['framework']['reads'])
                self.assertFalse(result['template_match']['applicable'])
                self.assertFalse(result['render_started'])
                self.assertFalse(result['execution_authorized_by_route'])

    def test_video_performance_retrospective_keeps_analytics(self):
        result = self.run_cli('intent', '复盘这条视频的播放数据和完播情况，先不发布')
        self.assertEqual(result['profile'], 'analytics')
        self.assertEqual(result['next'], 'verify_publication_and_import_real_metrics')

    def test_knowledge_song_consumes_first_cut_recipe_without_inheriting_quality(self):
        result = self.run_cli('content-plan', '--format', 'knowledge-song',
                              '--question', '沿已有参考与定版音轨完成当前作品的制作交接')
        context = result['development_context']
        recipe = context['production_recipe']
        path = ROOT / 'docs/制作配方/知识歌曲首版.md'
        resource = next(r for r in context['resources'] if r['file'] == str(path))
        self.assertEqual(resource['text'], path.read_text())
        self.assertEqual(recipe['source_sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(recipe['stage_handoff']['artifacts'], [str(path)])
        self.assertFalse(recipe['quality_inheritance'])
        self.assertEqual(context['viewer_question'], '沿已有参考与定版音轨完成当前作品的制作交接')
        self.assertEqual(context['quality_status'], 'unassessed')
        self.assertFalse(result['model_request_sent'])
        self.assertFalse(result['render_started'])

    def test_general_content_entry_consumes_cross_task_production_workflow(self):
        result = self.run_cli('content-plan', '--question', '根据已有输入整理完整制作交接')
        context = result['development_context']
        method = context['production_workflow']
        path = ROOT / 'docs/制作配方/视频制作工作流.md'
        resource = next(r for r in context['resources'] if r['file'] == str(path))
        self.assertEqual(resource['text'], path.read_text())
        self.assertEqual(method['source_sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(method['stage_handoff']['artifacts'], [str(path)])
        self.assertFalse(method['quality_inheritance'])
        self.assertNotIn('production_recipe', context)
        self.assertFalse(result['model_request_sent'])
        self.assertFalse(result['render_started'])

    def test_fixed_engineering_trial_keeps_adaptation_route(self):
        result = self.run_cli('intent', '固定工程、固定原反例的换稿能力试验，主题是收藏方法却没有行动')
        self.assertNotEqual(result['next'], 'develop_original_content')
        self.assertFalse(result['execution_authorized_by_route'])

    def test_existing_full_script_is_not_sent_back_to_ideation(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / 'script.txt'
            script.write_text('小林存下教程。收到作业截止提醒后，关掉教程，交出第一份练习。', encoding='utf-8')
            result = self.run_cli('intent', '原创主题：收藏方法却没有行动',
                                  '--script-file', str(script))
        self.assertNotEqual(result['next'], 'develop_original_content')
        self.assertFalse(result['execution_authorized_by_route'])

    def test_real_content_plan_carries_feedback_and_working_method(self):
        source = ROOT / 'productions/fixed-adaptation-trial-20261115/brief.json'
        result = self.run_cli('content-plan', str(source))
        contract = result['creative_contract']
        evidence = result['content_strategy']['topic']['evidence']
        self.assertEqual(contract['evidence'], evidence)
        development = result['development_context']
        self.assertEqual(development['viewer_question'], contract['viewer_question'])
        self.assertIn('动作不是表演', development['method']['text'])
        self.assertIn('未证明', development['limitations'])
        self.assertEqual(development['quality_status'], 'unassessed')
        self.assertFalse(result['model_request_sent'])
        self.assertFalse(result['render_started'])

    def test_question_can_start_research_without_inventing_a_finished_plan(self):
        result = self.run_cli('content-plan', '--question', '收藏了那么多方法，为什么一个也没用')
        context = result['development_context']
        self.assertIsNone(result['content_strategy'])
        self.assertIsNone(result['creative_contract'])
        self.assertIsNone(context['audience'])
        self.assertIsNone(context['proposed_payoff'])
        self.assertIsNone(context['current_opening'])
        self.assertEqual(context['topic_decision'], 'research')
        self.assertGreaterEqual(len(context['resources']), 3)
        self.assertTrue(all(r['text'] and r['source_sha256'] for r in context['resources']))
        self.assertFalse(result['render_started'])

    def test_original_failure_returns_actual_rejection_not_only_trial_permission(self):
        result = self.run_cli('content-plan', str(ROOT / 'productions/fixed-adaptation-trial-20261115/brief.json'))
        feedback = result['development_context']['previous_work']
        self.assertEqual(feedback['relation'], 'same_script_and_strategy')
        self.assertEqual(feedback['review_status'], 'blocked')
        self.assertEqual(feedback['user_feedback']['decision'], 'rejected')
        self.assertIn('完全不能用', feedback['user_feedback']['observation'])
        self.assertIn('opening-repetition', [f['id'] for f in feedback['findings']])
        self.assertEqual(result['content_strategy']['topic']['decision'], 'ready')
        self.assertEqual(result['development_context']['quality_status'], 'unassessed')

    def test_same_work_new_script_does_not_inherit_old_quality_decision(self):
        source = ROOT / 'productions/fixed-adaptation-trial-20261115/brief.json'
        brief = json.loads(source.read_text())
        brief['script'] = '另一篇尚未审查的文本'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'brief.json'
            path.write_text(json.dumps(brief, ensure_ascii=False))
            result = self.run_cli('content-plan', str(path))
        self.assertEqual(result['development_context']['previous_work']['relation'], 'earlier_content')
        self.assertEqual(result['development_context']['quality_status'], 'unassessed')


if __name__ == '__main__':
    unittest.main()
