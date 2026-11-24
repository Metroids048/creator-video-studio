"""Isolated contract fixtures, distinct from the real-video pilot and real platform metrics."""
import copy
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import studio
import publishing
import content_analytics as analytics
import content_strategy as strategy
from review_fixture import reviewed_contract


class PublicationTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        active = patch.object(studio, "ROOT", self.root)
        active.start(); self.addCleanup(active.stop)
        self.version = self.root / "works/fixture/versions/v0001"
        self.version.mkdir(parents=True)
        for name, data in {"video.mp4": b"synthetic contract video bytes",
                           "editable.zip": b"synthetic native archive", "publish.json": b"original developer metadata",
                           "subtitles.srt": b"", "brief.json": b"{}"}.items():
            (self.version/name).write_bytes(data)
        studio.save(self.version/"receipt.json", {"project":"fixture", "version":"v0001",
                    "delivery":{p.name:studio.digest(p) for p in self.version.iterdir()}})
        studio.save(self.version.parents[1]/"current.json", {"version":"v0001"})
        reviewed_contract(studio, self.version)
        self.original = {p: p.read_bytes() for p in [*self.version.iterdir(), self.version.parents[1]/"current.json"]}
        for c in "ab":
            (self.root/f"{c}.png").write_bytes(b"\x89PNG\r\n\x1a\n"+b"\x00\x00\x00\rIHDR"+struct.pack('>II',1080,1920))
        _, binding = publishing.source(studio,"fixture","v0001")
        self.spec = {"source":binding,"platform":"douyin","account_alias":"fixture-account","revision":"p0001",
                     "titles":[{"text":title,"reason":"fixture angle"} for title in ('question','result','<script>alert(1)</script>')],
                     "selected_title":2,"covers":[{"file":f"{c}.png","sha256":studio.digest(self.root/f"{c}.png"),"angle":"fixture"} for c in 'ab'],
                     "selected_cover":0,"description":"<b>public copy</b>","tags":["fixture"],
                     "review":{"video_sha256":binding["video_sha256"],"content_observation":"contract fixture only","limitations":["not a real video"]},
                     "rules":{"source":"test contract","checked_at":"2026-11-14"},
                     "experiment":{"hypothesis":"fixture hypothesis","variable":"title"}}
        self.spec_path = self.root/"spec.json"
        account = {"alias":"fixture-account", "platform":"douyin", "promise":"fixture benefit",
                   "audience":{"who":"fixture reader", "situation":"fixture situation", "need":"fixture need"},
                   "pillars":["daily"], "evidence":[{"id":"e1", "kind":"hypothesis", "source":"test fixture",
                       "observation":"isolated contract only", "limitation":"no market evidence"}]}
        topic = {"id":"fixture-topic", "pillar":"daily", "audience_question":"fixture question", "payoff":"fixture payoff",
                 "angle":"fixture angle", "opening":"fixture opening", "visual_plan":"fixture visual", "goal":"recognition",
                 "decision":"ready", "evidence":[], "evidence_ids":["e1"], "promises":[{"id":"p1","text":"fixture promise"}]}
        studio.save(self.root/'context.json', {'content_strategy':strategy.freeze(account,topic,[])})
        self.spec['strategy'] = {'file':'context.json','sha256':studio.digest(self.root/'context.json')}
        for item in self.spec['titles'] + self.spec['covers']: item['promise_id']='p1'
        self.spec['editorial'] = {'fulfillment':[{'promise_id':'p1','at_seconds':0,'observation':'fixture only'}],
                                 'tag_basis':[{'tag':'fixture','role':'subject','basis':'fixture only','evidence_id':'e1'}],
                                 'cover_observations':['fixture A','fixture B']}
        self.spec['cover_research'] = {
            'selection_reason':'fixture comparison, not market proof',
            'references':[{'id':'r1','url':'https://example.com/original','checked_at':'2026-11-14',
                           'metrics':{'views':None,'likes':100},'metrics_source':'synthetic fixture only',
                           'visual_observation':'fixture observation','relevance':'fixture audience',
                           'limitation':'synthetic contract, not a real reference'}]}
        for cover in self.spec['covers']:
            cover['generation'] = {'tool':'image_gen.imagegen','requested_model':'Codex Image 2',
                                   'reported_model':None,'prompt':'fixture prompt','evidence':'fixture only',
                                   'image_sha256':cover['sha256'],'reference_ids':['r1']}
        self.spec['review']['checks'] = [
            {'layer':layer,'status':'unobserved','scope':'fixture only','method':'not performed'}
            for layer in ('video_visual','video_audio','cover_visual','platform_crop','user_acceptance')]
        studio.save(self.spec_path,self.spec)

    def build(self):
        return Path(publishing.build(studio,self.spec_path)["path"])

    def test_missing_video_review_blocks_actual_package_builder(self):
        shutil.rmtree(self.version.parents[1] / "reviews")
        with self.assertRaisesRegex(ValueError, "质量交付被阻止"):
            self.build()
        self.assertFalse((self.version.parents[1] / "publications").exists())

    def test_cover_workflow_cannot_be_omitted_or_silently_use_another_generator(self):
        for change in [lambda s:s.pop('cover_research'),
                       lambda s:s['covers'][0].pop('generation'),
                       lambda s:s['covers'][0]['generation'].update(tool='svg-render'),
                       lambda s:s['covers'][0]['generation'].update(requested_model='other'),
                       lambda s:s['covers'][0]['generation'].update(reported_model='other'),
                       lambda s:s['covers'][0]['generation'].update(image_sha256='0'*64),
                       lambda s:s['covers'][0]['generation'].update(reference_ids=['unknown']),
                       lambda s:s['cover_research']['references'][0].update(metrics={'likes':True}),
                       lambda s:s['review'].pop('checks')]:
            spec=copy.deepcopy(self.spec);change(spec);studio.save(self.spec_path,spec)
            with self.assertRaises(ValueError):self.build()
            self.assertFalse((self.version.parents[1]/'publications').exists())

    def test_pending_quality_and_unreported_model_are_visible_and_rechecked(self):
        package=self.build();manifest=studio.load(package/'manifest.json')
        self.assertEqual(manifest['schema'],4)
        self.assertEqual(manifest['quality']['status'],'candidate')
        self.assertIn('video_audio',manifest['quality']['pending'])
        self.assertEqual(manifest['quality']['model_verification'],'not_exposed')
        self.assertIn('质量待验',(package/'preview.html').read_text())
        manifest['quality']['pending']=[];studio.save(package/'manifest.json',manifest)
        receipt=studio.load(package/'receipt.json');receipt['files']['manifest.json']=studio.digest(package/'manifest.json')
        studio.save(package/'receipt.json',receipt)
        with self.assertRaisesRegex(ValueError,'质量'):publishing.verify(studio,package)

    def test_observed_cover_check_must_bind_both_exact_images(self):
        check = self.spec['review']['checks'][2]
        check.update(status='observed', evidence='an image was viewed')
        with self.assertRaisesRegex(ValueError, '图片绑定'):
            publishing.packaging_quality(self.spec)
        check['images'] = [{'index': i, 'sha256': c['sha256'], 'observation': 'synthetic fixture only'}
                           for i, c in enumerate(self.spec['covers'])]
        publishing.packaging_quality(self.spec)
        check['images'][0]['sha256'] = 'stale'
        with self.assertRaisesRegex(ValueError, '图片绑定'):
            publishing.packaging_quality(self.spec)

    def test_old_package_is_not_delivery_eligible_after_video_rejection(self):
        package = self.build()
        import video_review
        with patch.object(video_review, 'status', return_value={'status': 'blocked', 'blockers': ['rejected']}):
            result = publishing.verify(studio, package)
        self.assertFalse(result['delivery_eligible'])
        self.assertEqual(result['delivery_status'], 'blocked')
        with patch.object(video_review, 'status', return_value={'status': 'reviewed', 'blockers': []}):
            result = publishing.verify(studio, package)
        self.assertEqual(result['delivery_status'], 'pending')

    def test_legacy_package_verification_does_not_allow_legacy_new_builds(self):
        package=self.build();manifest=studio.load(package/'manifest.json')
        manifest['schema']=2;manifest.pop('cover_research');manifest.pop('quality')
        studio.save(package/'manifest.json',manifest)
        receipt=studio.load(package/'receipt.json');receipt['files']['manifest.json']=studio.digest(package/'manifest.json')
        studio.save(package/'receipt.json',receipt)
        self.assertEqual(publishing.verify(studio,package)['quality']['status'],'legacy_unassessed')
        self.spec.pop('cover_research');self.spec['revision']='p0002';self.spec['schema']=2
        studio.save(self.spec_path,self.spec)
        with self.assertRaises(ValueError):self.build()

    def test_legacy_schema_three_is_readable_but_not_upgraded(self):
        package = self.build(); manifest = studio.load(package/'manifest.json')
        manifest['schema'] = 3
        for check in manifest['review']['checks']:
            check.update(status='observed', evidence='legacy synthetic declaration')
        manifest['quality'] = publishing.packaging_quality(manifest, require_image_bindings=False)
        studio.save(package/'manifest.json', manifest)
        receipt = studio.load(package/'receipt.json')
        receipt['files']['manifest.json'] = studio.digest(package/'manifest.json')
        studio.save(package/'receipt.json', receipt)
        report = publishing.verify(studio, package)
        self.assertEqual(report['delivery_status'], 'pending')
        self.assertFalse(report['delivery_eligible'])

    def test_new_publication_rejects_missing_strategy_and_unfulfilled_promises(self):
        for change in [lambda s:s.pop('strategy'),
                       lambda s:s['titles'][0].update(promise_id='invented'),
                       lambda s:s['editorial']['tag_basis'][0].update(evidence_id='invented')]:
            spec=copy.deepcopy(self.spec);change(spec);studio.save(self.spec_path,spec)
            with self.assertRaises(ValueError): self.build()
            self.assertFalse((self.version.parents[1]/'publications').exists())

    def test_changed_context_invalidates_prepared_package(self):
        context=studio.load(self.root/'context.json');context['content_strategy']['account']['promise']='changed'
        studio.save(self.root/'context.json',context)
        with self.assertRaisesRegex(ValueError,'哈希|快照'):self.build()

    def test_self_media_production_uses_same_contract_without_breaking_legacy_editing(self):
        legacy={'id':'fixture','route':'editor','inputs':[{'id':'clip'}],'operations':[{'op':'trim'}]}
        studio.validate(legacy)
        brief={**legacy,'purpose':'self-media'}
        with self.assertRaisesRegex(ValueError,'受众与选题'):studio.validate(brief)
        brief['content_strategy']=studio.load(self.root/'context.json')['content_strategy']
        studio.validate(brief)
        self.assertEqual(studio.editorial_plan(brief)['viewer_question'],'fixture question')
        topic=copy.deepcopy(brief['content_strategy']['topic']);topic['decision']='research'
        brief['content_strategy']=strategy.freeze(brief['content_strategy']['account'],topic,[])
        with self.assertRaisesRegex(ValueError,'尚未就绪'):studio.validate(brief)

    def test_unknown_account_and_out_of_video_promise_are_rejected(self):
        receipt=studio.load(self.version/'receipt.json');receipt['media']={'format':{'duration':'30'}}
        studio.save(self.version/'receipt.json',receipt)
        self.spec['source']['receipt_sha256']=studio.digest(self.version/'receipt.json')
        for change in [lambda s:s.update(account_alias='another-account'),
                       lambda s:s['editorial']['fulfillment'][0].update(at_seconds=30)]:
            spec=copy.deepcopy(self.spec);change(spec);studio.save(self.spec_path,spec)
            with self.assertRaisesRegex(ValueError,'账号|时间'):self.build()

    def test_feedback_returns_reusable_next_brief_without_fabricating_data(self):
        package=self.build(); context=studio.load(self.root/'context.json')['content_strategy']
        topic=copy.deepcopy(context['topic']);topic.update(id='next-topic',decision='research')
        feedback={'manifest_sha256':studio.digest(package/'manifest.json'),'kind':'editorial_review',
                  'observations':['fixture is not market data'],'hypothesis':'a clearer circumstance may help',
                  'variable':'opening','alternative':'subject interest could explain response','next_topic':topic}
        file=self.root/'feedback.json';studio.save(file,feedback)
        result=analytics.save_review(studio,package,feedback_path=file)
        next_path=Path(result['path'])/'next-brief.json'
        self.assertEqual(strategy.load(studio,next_path)['topic']['id'],'next-topic')
        self.assertEqual(result['status'],'awaiting_data');self.assertIsNone(result['metrics'])
        feedback['manifest_sha256']='0'*64;studio.save(file,feedback)
        with self.assertRaisesRegex(ValueError,'不符'):analytics.report(studio,package,feedback_path=file)

    def test_real_cli_modes_block_before_read_or_write(self):
        for command, args in [("publish-pack", ["missing.json"]), ("content-review", ["missing-package"])]:
            for mode in [[],["--mode","production"],["--mode","research"]]:
                result = subprocess.run([sys.executable,ROOT/"scripts/studio.py",*mode,command,*args],capture_output=True,text=True)
                self.assertEqual(result.returncode,2)
                self.assertIn("需要显式 --mode delivery",result.stderr)

    def test_portable_package_and_revision_leave_production_bytes_unchanged(self):
        package=self.build()
        publishing.verify(studio,package)
        self.assertEqual((package/"video.mp4").read_bytes(),self.original[self.version/"video.mp4"])
        self.assertFalse((package/"subtitles.srt").exists())
        self.assertFalse((package/"editable.zip").exists())
        html=(package/"preview.html").read_text()
        self.assertNotIn('<script>alert(1)</script>',html)
        self.assertIn('&lt;script&gt;',html)
        self.assertNotIn('<b>public copy</b>',html)
        with zipfile.ZipFile(package.with_suffix('.zip')) as z:
            self.assertEqual(set(z.namelist()),{f'p0001/{p.name}' for p in package.iterdir()})
            for file in package.iterdir(): self.assertEqual(z.read(f'p0001/{file.name}'),file.read_bytes())
            unpacked=self.root/'away';z.extractall(unpacked)
        publishing.verify(studio,unpacked/'p0001')
        with self.assertRaisesRegex(ValueError,'已存在'): self.build()
        self.spec['revision']='p0002';self.spec['selected_title']=0
        studio.save(self.spec_path,self.spec);second=self.build()
        self.assertEqual(studio.digest(package/'video.mp4'),studio.digest(second/'video.mp4'))
        for file,data in self.original.items(): self.assertEqual(file.read_bytes(),data)

    def test_wrong_source_or_cover_hash_rejected_without_package(self):
        for modify in [lambda s:s['source'].update(version='v0002'),
                       lambda s:s['source'].update(video_sha256='0'*64),
                       lambda s:s['source'].update(receipt_sha256='0'*64),
                       lambda s:s['covers'][0].update(sha256='0'*64)]:
            spec=copy.deepcopy(self.spec);modify(spec);studio.save(self.spec_path,spec)
            with self.assertRaises((ValueError,FileNotFoundError)):self.build()
            self.assertFalse((self.version.parents[1]/'publications').exists())

    def test_original_tamper_and_pack_tamper_are_detected(self):
        package=self.build()
        (package/'cover-a.png').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'哈希'):publishing.verify(studio,package)
        (self.version/'publish.json').write_bytes(b'changed developer metadata')
        with self.assertRaises(ValueError):publishing.plan(studio,self.spec_path)

    def test_no_data_review_is_bound_and_does_not_invent_metrics(self):
        package=self.build()
        result=analytics.save_review(studio,package)
        self.assertEqual(result['status'],'awaiting_data');self.assertIsNone(result['metrics'])
        self.assertFalse(result['published_by_this_workflow'])
        self.assertEqual(result['publication']['manifest_sha256'],studio.digest(package/'manifest.json'))
        second=analytics.save_review(studio,package)
        self.assertNotEqual(result['path'],second['path'])
        publishing.verify(studio,package)
        for file,data in self.original.items(): self.assertEqual(file.read_bytes(),data)

    def test_metrics_cannot_bind_to_another_video_or_publication(self):
        package=self.build();path=self.root/'metrics.json'
        data=snapshot();data.update(platform='douyin',account_alias='fixture-account',video_sha256='0'*64,
                                   publication_manifest_sha256=studio.digest(package/'manifest.json'))
        studio.save(path,data)
        with self.assertRaisesRegex(ValueError,'不符'):analytics.report(studio,package,path)
        data['video_sha256']=self.spec['source']['video_sha256'];studio.save(path,data)
        result=analytics.save_review(studio,package,path)
        self.assertEqual(result['status'],'observed')
        self.assertEqual(studio.load(Path(result['path'])/'snapshot.json'),data)

    def test_intent_loads_new_skills_without_entering_video_creation(self):
        for request,expected in [('给这条现有知识视频做标题、封面、标签和离线发布包，先不发布',{'publish'}),
                                 ('复盘这个视频的播放数据，没有数据就先标待验',{'analytics'}),
                                 ('做这条视频的标题封面和数据复盘',{'analytics','publish'})]:
            run=subprocess.run([sys.executable,ROOT/'scripts/studio.py','intent',request],capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)
            result=json.loads(run.stdout)
            self.assertTrue(expected <= result['packs'].keys())
            self.assertTrue(all(not result['packs'][name]['missing'] for name in expected))
            self.assertFalse(result['render_started']);self.assertFalse(result['model_request_sent'])
            self.assertFalse(result['template_match']['applicable'])

    def test_preview_keeps_native_aspect_ratio_with_portrait_poster(self):
        receipt=studio.load(self.version/'receipt.json')
        receipt['media']={'streams':[{'codec_type':'video','width':1920,'height':1080}]}
        studio.save(self.version/'receipt.json',receipt)
        reviewed_contract(studio, self.version)
        self.spec['source']['receipt_sha256']=studio.digest(self.version/'receipt.json')
        studio.save(self.spec_path,self.spec)
        package=self.build()
        self.assertIn('aspect-ratio:1920/1080;', (package/'preview.html').read_text())

    def test_new_video_with_packaging_keeps_original_creation_route(self):
        cases = [
            ('做一条讲解网络原理的视频，同时准备标题和封面', 'explainer'),
            ('做一段歌词MV，完成后给标题和标签', 'mv-silent'),
            ('做一条水彩绘本动画，附封面', 'storybook'),
            ('做一条视频并准备标题封面', 'theme'),
            ('做一条科普视频，后续复盘播放数据', 'explainer'),
        ]
        for request, expected in cases:
            with self.subTest(request=request):
                run = subprocess.run([sys.executable, ROOT/'scripts/studio.py', 'intent', request],
                                     capture_output=True, text=True)
                self.assertEqual(run.returncode, 0, run.stderr)
                result = json.loads(run.stdout)
                self.assertEqual(result['profile'], expected)
                self.assertIn('style-templates', result['packs'])
                self.assertFalse(result['execution_authorized_by_route'])


def snapshot(**changes):
    # Synthetic numbers are used only inside isolated unit tests, never the pilot report.
    value={'platform':'test-platform','account_alias':'test-account','content_id':'current',
           'source':'unit test fixture','content_type':'animation','duration_seconds':30,'window_hours':24,
           'published_at':'2026-11-13T12:00:00+08:00','observed_at':'2026-11-14T12:00:00+08:00',
           'metrics':{'views':100,'likes':10,'comments':0,'saves':None}}
    value.update(changes);return value


class AnalyticsTest(unittest.TestCase):
    def test_missing_zero_and_zero_denominator_remain_distinct(self):
        r=analytics.analyze(snapshot())
        self.assertEqual(r['metrics']['comments'],0);self.assertIsNone(r['metrics']['saves'])
        self.assertEqual(r['metrics']['likes_per_view'],.1)
        self.assertIsNone(r['comparison']['likes']['relative_change'])
        self.assertIsNone(analytics.measures(snapshot(metrics={'views':0,'likes':0}))['likes_per_view'])

    def test_comparison_filters_cohort_self_and_missing_per_metric(self):
        baselines=[snapshot(content_id='one',metrics={'views':50}),snapshot(content_id='two',metrics={'views':150,'likes':0}),
                   snapshot(content_id='other-window',window_hours=12,observed_at='2026-11-14T00:00:00+08:00'),
                   snapshot(content_id='other-account',account_alias='different'),snapshot()]
        result=analytics.analyze(snapshot(),baselines)
        self.assertEqual(result['baseline_contents'],2)
        self.assertEqual(result['comparison']['views']['baseline_median'],100)
        self.assertEqual(result['comparison']['likes']['baseline_n'],1)
        self.assertIsNone(result['comparison']['likes']['relative_change'])
        with self.assertRaisesRegex(ValueError,'重复'):analytics.analyze(snapshot(),[baselines[0],baselines[0]])

    def test_invalid_or_demo_or_empty_data_rejected(self):
        for row in [snapshot(metrics={'views':None}),snapshot(metrics={'views':-1}),snapshot(metrics={'views':True}),
                    snapshot(metrics={'views':float('nan')}),snapshot(window_hours=12),snapshot(synthetic=True),
                    snapshot(observed_at='2026-11-14T12:00:00')]:
            with self.subTest(row=row):
                with self.assertRaises(ValueError):analytics.validate(row)


if __name__=='__main__': unittest.main()
