"""Source-to-event adaptation consumed by existing briefs and scene inputs.

This verifies a traceable plan, not acting quality or runtime visibility. The
target is existing renderer data; no second storyboard/rendering system.
"""
import hashlib
import json
import zipfile
from pathlib import Path
from stage_handoff import fingerprint, select


def requirements(brief):
    rows = brief.get('requirements', [])
    if (not isinstance(rows, list) or not rows
            or any(not isinstance(r, dict) or not isinstance(r.get('id'), str) or not r['id'].strip()
                   or not isinstance(r.get('text'), str) or not r['text'].strip() for r in rows)
            or len({r['id'] for r in rows}) != len(rows)):
        raise ValueError('事件改编需保留逐项原要求 requirements（稳定 ID 和 text）')
    return rows


def inspect(brief, inputs):
    contract = brief.get('content_adaptation')
    required = brief.get('purpose') == 'self-media' and brief.get('route', 'code') == 'code'
    if contract is None and not required:
        return {'status': 'legacy_untracked', 'quality_verified': False}
    if not isinstance(contract, dict) or contract.get('schema') != 1:
        raise ValueError('自媒体新稿缺少事件改编 content_adaptation；风格外壳不能代替内容适配')
    script = brief.get('script')
    if (not isinstance(script, str) or not script.strip()
            or contract.get('script_sha256') != hashlib.sha256(script.encode()).hexdigest()):
        raise ValueError('事件改编与当前完整文案不一致')
    required_ids = {r['id'] for r in requirements(brief)}
    shots = {s['id']: s for s in brief.get('shots', [])}
    units = contract.get('units')
    if not isinstance(units, list) or not units:
        raise ValueError('事件改编缺少完整因果单元')
    seen, covered, used_shots, uncertain = set(), set(), set(), []
    for unit in units:
        if not isinstance(unit, dict):
            raise ValueError('事件改编单元必须为对象')
        for field in ('id', 'shot', 'goal', 'before', 'action', 'after', 'reaction', 'camera', 'preserve', 'changes'):
            if not isinstance(unit.get(field), str) or not unit[field].strip():
                raise ValueError('事件改编缺少 ' + field)
        if unit['id'] in seen or unit['shot'] not in shots:
            raise ValueError('事件 ID 重复或镜头不存在')
        seen.add(unit['id']); used_shots.add(unit['shot'])
        shot = shots[unit['shot']]
        span = unit.get('frames')
        if (not isinstance(span, list) or len(span) != 2 or any(type(n) is not int for n in span)
                or not 0 <= span[0] < span[1] <= shot['frames']):
            raise ValueError('事件须绑定实际镜头内有效帧范围')
        ids = unit.get('requirements')
        if not isinstance(ids, list) or not ids or any(not isinstance(x, str) or x not in required_ids for x in ids):
            raise ValueError('事件未绑定当前原要求')
        covered.update(ids)
        capability = unit.get('capability')
        if capability not in {'supported', 'unverified'}:
            raise ValueError('事件包含不支持的表演能力；先停止该路线')
        if capability == 'unverified':
            uncertain.append(unit['id'])
        for role in ('source', 'target'):
            ref = unit.get(role)
            if not isinstance(ref, dict) or ref.get('asset') not in inputs:
                raise ValueError('事件来源/目标须引用已冻结素材')
            path = inputs[ref['asset']][1]
            try:
                if ref.get('member'):
                    # Read directly from the frozen native ZIP; never extract.
                    with zipfile.ZipFile(path) as archive:
                        raw = archive.read(ref['member'])
                else:
                    raw = path.read_bytes()
                value = select(json.loads(raw), ref.get('pointer'))
            except (UnicodeError, json.JSONDecodeError, ValueError, KeyError, zipfile.BadZipFile) as exc:
                raise ValueError('事件来源/目标不是有效的可消费单元：' + str(exc)) from exc
            if fingerprint(value) != ref.get('sha256'):
                raise ValueError('事件内容已变化：' + unit['id'] + '/' + role)
            if role == 'target' and ref['asset'] not in [shot.get('sceneAsset'), *shot.get('sceneAssets', [])]:
                raise ValueError('目标事件未被对应镜头消费')
    if covered != required_ids:
        raise ValueError('事件改编遗漏原要求：' + ', '.join(sorted(required_ids - covered)))
    if used_shots != set(shots):
        raise ValueError('事件改编遗漏实际镜头：' + ', '.join(sorted(set(shots) - used_shots)))
    if uncertain and brief.get('production_stage') != 'representative':
        raise ValueError('存在未验证事件能力，只能进入代表段：' + ', '.join(uncertain))
    if brief.get('template', {}).get('id') == 'paper-ink-landscape':
        for shot in shots.values():
            scene = inputs[shot['sceneAsset']][1].read_text().splitlines()[0]
            try:
                rendered = json.loads(scene.removeprefix('const TEMPLATE_STORY = ').removesuffix(';'))
            except json.JSONDecodeError as exc:
                raise ValueError('纸墨事件没有进入既有场景编译器') from exc
            for unit in (u for u in units if u['shot'] == shot['id']):
                if fingerprint(select(rendered, unit['target']['pointer'])) != unit['target']['sha256']:
                    raise ValueError('纸墨实际场景与事件改编数据不一致')
    return {'status': 'bound', 'units': units, 'unverified_units': uncertain,
            'requirements': requirements(brief), 'quality_verified': False,
            'verified_here': 'source_target_data_and_shot_consumption_only'}


def bind_prepared(data, brief, source_base):
    """Normalize prepared filenames to stable asset IDs; preserve source bytes."""
    if 'requirements' in data:
        brief['requirements'] = data['requirements']
    if 'content_adaptation' not in data:
        return
    for field in ('script', 'production_stage'):
        if field in data:
            brief[field] = data[field]
    contract = json.loads(json.dumps(data['content_adaptation']))
    for item in data.get('adaptation_inputs', []):
        path = (source_base / item['path']).resolve(strict=True)
        if hashlib.sha256(path.read_bytes()).hexdigest() != item.get('sha256'):
            raise ValueError('改编来源素材哈希不符')
        brief['inputs'].append({**item, 'path': str(path)})
    by_name = {}
    for item in brief['inputs']:
        by_name.setdefault(Path(item['path']).name, []).append(item['id'])
    for unit in contract.get('units', []):
        for role in ('source', 'target'):
            ref = unit[role]
            if 'file' in ref:
                matches = by_name.get(ref.pop('file'), [])
                if len(matches) != 1:
                    raise ValueError('事件文件须唯一匹配准备后的素材')
                ref['asset'] = matches[0]
    brief['content_adaptation'] = contract


def scene_context(brief, inputs, shot_id):
    report = inspect(brief, inputs)
    shots = brief.get('shots', [])
    index = next((i for i, s in enumerate(shots) if s['id'] == shot_id), None)
    if index is None:
        raise ValueError('镜头不存在：' + shot_id)
    nearby = [s['id'] for s in shots[max(0, index - 1):index + 2]]
    return {'shot': shot_id, 'context_shots': nearby,
            'events': [u for u in report.get('units', []) if u['shot'] in nearby],
            'requirements': report.get('requirements', []), 'quality_verified': False}


def record_consumption(brief, shot, native):
    """Record what the actual native preparer supplied before rendering/caching.

    Files supplied to a renderer are not proof that a character performed well.
    """
    path = native.parent / 'scene-source.json'
    receipt = json.loads(path.read_text())
    assets = {shot.get('sceneAsset'), *shot.get('sceneAssets', [])}
    receipt['consumption'] = {
        'inputs': {i['id']: i['sha256'] for i in brief.get('inputs', []) if i['id'] in assets},
        'events': {u['id']: fingerprint(u) for u in brief.get('content_adaptation', {}).get('units', [])
                   if u['shot'] == shot['id']},
        'files': {p.relative_to(native).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in native.rglob('*') if p.is_file()},
        'scope': 'prepared_native_files; runtime_visibility_and_acting_not_verified'}
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
