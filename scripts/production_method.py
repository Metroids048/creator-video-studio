"""Freeze editorial working material in the existing prepared-input chain.

This checks provenance and reuse, never aesthetics or model compliance.
"""
import hashlib
import json
from pathlib import Path

from knowledge_song import STAGE as PREVIEW_STAGE

ASSET_ID = 'studio-production-method'


def resource(path):
    raw = path.read_bytes()
    return {'file': str(path), 'source_sha256': hashlib.sha256(raw).hexdigest(),
            'text': raw.decode('utf-8')}


def context(root, content_format='general'):
    root = Path(root)
    if content_format not in {'general', 'knowledge-song'}:
        raise ValueError('不支持的内容形式')
    result = {'schema': 1, 'format': content_format,
              'execution_prompt': resource(root / 'docs/制作配方/制作执行Prompt.md'),
              'resources': [resource(root / 'docs/制作配方/视频制作工作流.md')],
              'quality_verified': False, 'production_authorized': False,
              'limitation': '绑定实际方法材料，不证明执行者遵循、动作适配、完整视听或首版质量。'}
    if content_format == 'knowledge-song':
        result['preview_stage'] = PREVIEW_STAGE
        result['resources'].append(resource(root / 'docs/制作配方/知识歌曲首版.md'))
        result['skills'] = [resource(root / '.agents/skills' / name / 'SKILL.md') for name in
                            ('self-media-studio', 'studio-motion-design', 'studio-video-review')]
        base = root / 'works/falling-footage-1117/authoring-v0013'
        freeze = base / 'source-freeze.json'
        files = json.loads(freeze.read_text())
        for name, expected in files.items():
            if hashlib.sha256((base / name).read_bytes()).hexdigest() != expected:
                raise ValueError('V13复用源码已偏离冻结版本：' + name)
        result['baseline'] = {
            'root': str(base), 'freeze': str(freeze),
            'freeze_sha256': hashlib.sha256(freeze.read_bytes()).hexdigest(),
            'files': files, 'status': 'source_hashes_verified',
            'reuse_map': {
                'music': 'engine/scene.js: musicClock / accent；beat-analysis.json；换曲须重测重音',
                'motion': 'engine/scene.js: phase / ease / near / reveal / twoViews；同一主体连续状态',
                'geometry': 'engine/scene.js: force / velocity / noGravity；仅本题物理语义成立',
                'render': 'engine/clip.html、render-shot.mjs、compose.py、shot.json / effective-spec.json',
                'assets': 'engine/assets 分层；新内容按机制替换，audio.m4a和subtitles.srt不当通用素材'},
            'scope': '冻结的本片工程；先核能力适配，再复制到本任务新目录。不是已登记的通用成熟模板。'}
    return result


def bind_prepared(data, brief, directory, root):
    if data.get('purpose') != 'self-media' and 'content_format' not in data:
        return
    if any(row['id'] == ASSET_ID for row in brief['inputs']):
        raise ValueError('制作方法素材 ID 已被占用')
    method = context(root, data.get('content_format', 'general'))
    if data.get('purpose') == 'self-media' and data.get('production_stage', 'full') != 'representative':
        method['representative_review'] = brief['representative_review'] = 1
    if method['format'] == 'knowledge-song':
        scope = data.get('production_stage', 'full')
        if scope not in {'full', 'representative'}:
            raise ValueError('不支持的知识歌曲制作范围')
        method['preview_scope'] = scope
        brief['content_format'] = method['format']
        if 'production_stage' in data:
            brief['production_stage'] = data['production_stage']
    path = Path(directory) / 'production-method.json'
    path.write_text(json.dumps(method, ensure_ascii=False, indent=2) + '\n')
    brief['inputs'].append({'id': ASSET_ID, 'kind': 'data', 'path': path.name,
                            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})


def inspect(brief, inputs):
    if ASSET_ID not in inputs:
        if brief.get('content_format') == 'knowledge-song':
            raise ValueError('知识歌曲缺少冻结制作方法')
        return {'status': 'legacy_unbound', 'quality_verified': False}
    kind, path = inputs[ASSET_ID]
    if kind != 'data':
        raise ValueError('制作方法必须为冻结 data 素材')
    method = json.loads(path.read_text())
    if (method.get('schema') != 1 or method.get('format') not in {'general', 'knowledge-song'}
            or method.get('quality_verified') is not False
            or method.get('production_authorized') is not False):
        raise ValueError('制作方法格式或质量声明无效')
    if (method.get('preview_stage') == PREVIEW_STAGE
            and (brief.get('content_format') != 'knowledge-song'
                 or method['format'] != 'knowledge-song'
                 or brief.get('production_stage', 'full') != method.get('preview_scope'))):
        raise ValueError('知识歌曲 brief 与冻结制作方法的形式或制作范围不一致')
    if brief.get('content_format') == 'knowledge-song' and method.get('preview_stage') != PREVIEW_STAGE:
        raise ValueError('知识歌曲缺少冻结预审方法')
    if method.get('representative_review') != brief.get('representative_review'):
        raise ValueError('brief 与冻结制作方法的代表段要求不一致')
    for row in [method['execution_prompt'], *method['resources'], *method.get('skills', [])]:
        if hashlib.sha256(row['text'].encode()).hexdigest() != row['source_sha256']:
            raise ValueError('制作方法正文与冻结哈希不符')
    return {**method, 'status': 'bound', 'artifact': str(path),
            'artifact_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def require_new(brief, inputs, *, existing):
    result = inspect(brief, inputs)
    if brief.get('purpose') == 'self-media' and not existing and result['status'] != 'bound':
        raise ValueError('新自媒体制作缺少冻结制作方法；沿 templates prepare 绑定，保留旧任务不迁移')
    return result
