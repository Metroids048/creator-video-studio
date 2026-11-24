"""Same-artifact review evidence and delivery gate. No model requests or quality scoring."""
from pathlib import Path
import json
import math
import re
import tempfile


LAYERS = {"visual", "content", "playback", "listening"}
FPS = 2
AUDIO_HANDOFF = (
    "有音轨时把音频文件路径交给支持音频的审阅端，Codex 聊天只接收路径、SHA256 和文字观察。"
    "禁止通过 audio()、emitAudio 或音频 data URL 将原始声音送进聊天回合。"
)


def aistudio_observation(studio, version, base, packet, continuous):
    """Validate captured native AV input and independent listening, not model accuracy."""
    name = continuous.get('attestation')
    if name not in continuous.get('evidence', {}):
        return '待审：缺可核验的 AI 声画感知适配器回执'
    record = studio.load(local(base, name))
    if record.get('adapter') != 'aistudio_full_av_v1':
        return '待审：当前记录未使用已接入的 AI 声画感知适配器'
    checked_evidence(studio, base, record)
    if record.get('schema') != 1 or record.get('source') != packet['source']:
        return '待审：AI 视听回执不是本次成片'
    if record.get('unresolved_observation_conflicts') != []:
        return '待审：外部视听报告仍有未核实的观察分歧'
    names = [record.get(k) for k in ('capture', 'audio_capture', 'cross_check')]
    if any(n not in record['evidence'] for n in names):
        return '待审：AI 视听回执缺原始报告、独立听审或交叉核对'
    capture, audio = [studio.load(local(base, n)) for n in names[:2]]
    for item in (capture, audio):
        if (not item.get('url', '').startswith('https://aistudio.google.com/prompts/')
                or item.get('free') is not True or not item.get('model')
                or not item.get('report_turn') or not item.get('captured_at')
                or not item.get('run_state', '').rstrip().endswith('Response ready.')):
            return '待审：缺实际审片页面、模型、回复或免费模式记录'
    fields = capture.get('setup', {}).get('fields_after', [])
    values = {f.get('label', '').split(' ')[0]: f.get('value') for f in fields}

    def seconds(value):
        if not isinstance(value, str) or not re.fullmatch(r'(?:\d+m)?\d+(?:\.\d+)?s', value):
            return None
        parts = value[:-1].split('m')
        return float(parts[-1]) + (60 * float(parts[0]) if len(parts) == 2 else 0)

    duration = packet['duration_seconds']
    if (seconds(values.get('Start')) != 0 or seconds(values.get('End')) != duration
            or values.get('FPS') != '24'):
        return '待审：原生视频须交接完整范围和实际24fps设置，默认1fps不取得此资格'
    hashes = capture.get('hashes', {})
    received = {x.get('sha256') for x in hashes.get('files', [])}
    handed_audio = packet.get('audio_review')
    if handed_audio is not None:
        audio_name = handed_audio.get('file')
        audio_sha = handed_audio.get('sha256')
        if not audio_sha or packet['artifacts'].get(audio_name) != audio_sha:
            return '待审：独立听审文件未绑定到本版审查包'
    else:
        # Older review packets used the frozen version audio directly.
        audio_file = version / 'audio.m4a'
        audio_sha = studio.digest(audio_file) if audio_file.is_file() else None
    if not packet['has_audio'] or not audio_sha:
        return '待审：此适配器仅支持已交接完整独立主音轨的有声成片'
    if (hashes.get('state') != 'done' or packet['source']['video_sha256'] not in received
            or audio_sha not in received or audio.get('upload', {}).get('sha256') != audio_sha
            or audio.get('upload', {}).get('state') != 'uploaded_to_ui'):
        return '待审：页面实际输入不是同一成片和同源完整音轨'
    try:
        av_report, audio_report = [json.loads(x['code'][0]) for x in (capture, audio)]
    except (KeyError, IndexError, TypeError, ValueError):
        return '待审：原始模型回复缺完整结构化报告'
    if (av_report.get('range') != [0, duration] or av_report.get('speed') != 1
            or not {'video_frames', 'audio_track'}.issubset(av_report.get('modalities_received', []))
            or audio_report.get('modalities_received') != ['audio']):
        return '待审：报告未覆盖原速完整视频和独立音轨模态'
    # Keep model precision limits visible; whole-film AI review does not prove
    # human perception or observation of every source frame.
    if continuous.get('limitations') != av_report.get('limitations'):
        return '待审：正式记录遗漏或改写了原报告的感知局限'

    def covers(ranges):
        if any(len(span) != 2 or not all(isinstance(n, (int, float)) and math.isfinite(n)
                                        for n in span) for span in ranges):
            return False
        end = 0
        for start, stop in sorted(ranges):
            if start > end or start < 0 or stop <= start or stop > duration:
                return False
            end = max(end, stop)
        return end == duration

    visuals = av_report.get('segments', [])
    if not visuals or any(not all(s.get(k) for k in ('visual', 'audio', 'synchronization')) for s in visuals):
        return '待审：声画报告缺具体动作、声音或同步观察'
    ranges = [(s.get('start'), s.get('end')) for s in visuals]
    tail = av_report.get('tail', {})
    if tail.get('heard') and tail.get('visible'):
        ranges.append(tuple(tail.get('range', [])))
    if not covers(ranges):
        return '待审：声画观察在全片时间线上存在缺口'
    audio_ranges = []
    for segment in audio_report.get('segments', []):
        span = re.fullmatch(r'(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)秒', segment.get('time_range', ''))
        if not span or not segment.get('vocal_content') or not segment.get('accompaniment'):
            return '待审：独立听审缺具体声音或时间区间'
        audio_ranges.append(tuple(map(float, span.groups())))
    if not covers(audio_ranges):
        return '待审：独立听审未覆盖完整音轨'
    return None


def requirements_for(brief):
    """Keep explicit requirements and editorial promises through review handoff."""
    values = [brief.get('request') or brief.get('title') or '对照本版本 brief、字幕、镜头与原始需求逐项核对']
    if 'requirements' in brief:
        from content_adaptation import requirements
        values.extend(r['text'] for r in requirements(brief))
    values.extend(p['text'] for p in brief.get('content_strategy', {}).get('topic', {}).get('promises', []))
    return list(dict.fromkeys(values))


def continuous_observation(studio, version, base, packet, reviewer, continuous):
    if reviewer['kind'] == 'ai':
        return aistudio_observation(studio, version, base, packet, continuous)
    name = continuous.get('attestation')
    if name not in continuous.get('evidence', {}):
        return '待审：真人连续审阅缺同版观察回执（不能由 AI 冒写）'
    try:
        record = studio.load(local(base, name))
    except (OSError, ValueError, TypeError):
        return '待审：完整观察回执不是可解析的记录'
    if (record.get('source') != packet['source'] or record.get('observer') != reviewer['name']
            or record.get('method') != 'human_normal_speed'
            or record.get('range') != [0, packet['duration_seconds']] or record.get('speed') != 1
            or record.get('limitations') != []
            or record.get('modalities') != (['visual', 'audio'] if packet['has_audio'] else ['visual'])
            or not isinstance(record.get('statement'), str) or not record['statement'].strip()):
        return '待审：真人回执的对象、观察范围或局限不满足完整审阅'
    return None


def binding(studio, version):
    receipt = studio.check_delivery(version)
    return {"project": receipt["project"], "version": receipt["version"],
            "video_sha256": receipt["delivery"]["video.mp4"],
            "receipt_sha256": studio.digest(version / "receipt.json")}


def folder(studio, version):
    source = binding(studio, version)
    return version.parents[1] / "reviews" / version.name / source["receipt_sha256"]


def local(base, name):
    if not isinstance(name, str):
        raise ValueError("审查证据必须为本审查目录内的文件")
    file = (base / name).resolve()
    if not file.is_relative_to(base.resolve()) or not file.is_file():
        raise ValueError(f"审查证据不存在或越界：{name}")
    return file


def checked_evidence(studio, base, item):
    refs = item.get("evidence") if isinstance(item, dict) else None
    if not isinstance(refs, dict) or not refs:
        raise ValueError("已有观察须绑定实际证据文件及 SHA256")
    for name, sha in refs.items():
        if studio.digest(local(base, name)) != sha:
            raise ValueError(f"审查证据已变化：{name}")
    if not isinstance(item.get("observation"), str) or not item["observation"].strip():
        raise ValueError("已有观察须记录具体观察，不能用文件存在冒充质量通过")


def manifest(studio, version):
    base = folder(studio, version)
    data = studio.load(base / "frames.json")
    if data.get("schema") != 1 or data.get("source") != binding(studio, version):
        raise ValueError("审查包绑定已过期")
    brief_path = version / 'brief.json'
    if brief_path.is_file():
        brief = studio.load(brief_path)
        if 'requirements' in brief and data.get('requirements') != requirements_for(brief):
            raise ValueError('审查包遗漏当前逐项原要求或内容承诺')
    duration = data["duration_seconds"]
    if not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration <= 0:
        raise ValueError("审查包缺少完整片长")
    expected = [round(n / FPS, 6) for n in range(math.ceil(duration * FPS))]
    if data.get("fps") != FPS or [x["at"] for x in data["frames"]] != expected:
        raise ValueError("抽帧范围未覆盖完整成片")
    for frame in data["frames"]:
        if studio.digest(local(base, frame["file"])) != frame["sha256"]:
            raise ValueError("抽帧文件已变化，旧观察失效")
    for name, sha in data["artifacts"].items():
        if studio.digest(local(base, name)) != sha:
            raise ValueError(f"审查辅助证据已变化：{name}")
    audio = data.get('audio_review')
    if audio is not None and (not data['has_audio'] or not isinstance(audio, dict)
                              or not isinstance(audio.get('file'), str) or not audio.get('sha256')
                              or data['artifacts'].get(audio['file']) != audio['sha256']):
        raise ValueError('独立听审文件未绑定到本版审查包')
    return base, data


def prepare(studio, version):
    """Extract the entire film at 2 fps; reuse the exact packet on recovery."""
    source = binding(studio, version)
    target = folder(studio, version)
    if target.exists():
        base, data = manifest(studio, version)
        return {**status(studio, version, prepared=(base, data)), "reused": True, "audio_handoff": AUDIO_HANDOFF,
                "review_inputs": review_inputs(studio, version, target, data)}
    media = studio.probe(version / "video.mp4")
    duration = float(media["format"]["duration"])
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("无法确定完整片长，不生成审查包")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".review-", dir=target.parent) as tmp:
        base = Path(tmp) / "packet"
        (base / "frames").mkdir(parents=True)
        studio.run(studio.BIN / "ffmpeg", "-v", "error", "-i", version / "video.mp4",
                   "-vf", f"fps={FPS}:round=up", "-fps_mode", "passthrough",
                   base / "frames" / "%06d.png")
        frames = [{"file": str(p.relative_to(base)), "at": round(n / FPS, 6),
                   "sha256": studio.digest(p)} for n, p in enumerate(sorted((base / "frames").glob("*.png")))]
        if len(frames) != math.ceil(duration * FPS):
            raise ValueError("实际抽帧数量与全片覆盖不符")
        # Contact sheets locate problems; individual full-resolution frames judge typography.
        studio.run(studio.BIN / "ffmpeg", "-v", "error", "-framerate", str(FPS),
                   "-i", base / "frames" / "%06d.png", "-vf",
                   "scale=480:-1,drawtext=text='%{n}':x=8:y=8:fontsize=24:fontcolor=red,tile=6x6:padding=4:margin=4",
                   base / "contact-%03d.jpg")
        (base / "preview.html").write_text(
            '<meta charset="utf-8"><title>待审原片</title><p>诊断预览；未经质量交付验收。</p>'
            f'<video controls style="width:100%;max-height:85vh;object-fit:contain" src="../../..'
            f'/versions/{version.name}/video.mp4"></video>', encoding="utf-8")
        # Some video review surfaces ingest pictures without the embedded sound.
        # Hand off the full primary audio separately, bound to this same video.
        # This supplies input; it does not attest that any reviewer heard it.
        audio_streams = [s for s in media['streams'] if s.get('codec_type') == 'audio']
        audio_review = None
        if audio_streams:
            copy_aac = audio_streams[0].get('codec_name') == 'aac'
            audio_file = base / ('audio-review.m4a' if copy_aac else 'audio-review.wav')
            studio.run(studio.BIN / 'ffmpeg', '-v', 'error', '-i', version / 'video.mp4',
                       '-map', '0:a:0', '-vn', '-c:a', 'copy' if copy_aac else 'pcm_f32le', audio_file)
            audio_review = {'file': audio_file.name, 'sha256': studio.digest(audio_file),
                            'source_stream_index': audio_streams[0]['index'],
                            'stream_count': len(audio_streams),
                            'mode': 'stream_copy' if copy_aac else 'decoded_pcm',
                            'scope': 'full_primary_audio_not_listening_attestation'}
        brief = studio.load(version / "brief.json") if (version / "brief.json").is_file() else {}
        requirements = requirements_for(brief)
        artifacts = {p.name: studio.digest(p) for p in base.iterdir() if p.is_file()}
        data = {"schema": 1, "source": source, "duration_seconds": duration, "fps": FPS,
                "has_audio": any(s.get("codec_type") == "audio" for s in media["streams"]),
                "audio_review": audio_review,
                "requirements": requirements, "frames": frames, "artifacts": artifacts,
                "limits": "2fps不证明帧间运动无缺陷；仍需全片连续播放及有音轨时真实听审。"}
        studio.save(base / "frames.json", data)
        pending = {"schema": 1, "source": source, "packet_sha256": studio.digest(base / "frames.json"),
                   "reviewer": {"kind": "ai", "name": "Codex", "method": "pending"},
                   "frames": [{"file": f["file"], "status": "pending"} for f in frames],
                   "requirements": [{"text": requirement, "status": "pending"} for requirement in requirements],
                   "checks": [{"layer": layer, "status": "pending", "range": [0, duration]}
                              for layer in sorted(LAYERS)], "findings": []}
        studio.save(base / "draft.json", pending)
        # Editable editorial record, like draft.json; frozen diagnostic artifacts stay immutable.
        (base / "cross-check.md").write_text(
            "# 交叉核对表（待核对）\n\n"
            f"作品：{source['project']} / {source['version']}\n\n"
            f"成片 SHA256：{source['video_sha256']}\n\n"
            f"回执 SHA256：{source['receipt_sha256']}\n\n"
            "报告附件及 SHA256、实际输入范围和观察方法：待填写；未使用外部报告须说明。\n\n"
            "| ID | 报告原结论与时间码 | 源码／成片帧／独立音轨证据及 SHA256 | 采信／丢弃／待核对及理由 | 对应 finding ID／复验范围 |\n"
            "|---|---|---|---|---|\n\n"
            "每条结论单列；证据不足保持待核对。源码意图不能代替成片效果，"
            "字幕争议须核对未提供目标歌词的实际盲听，分歧原样保留。\n\n"
            "有音轨时同时交接完整视频与 audio_review 指向的完整主音轨；先核审阅端实际接收的模态，"
            "不得根据字幕推断已听到声音。多音轨只提取第一条，其余须另核；"
            "音轨文件、模型自述与分段报告都不自动取得连续视听放行资格。\n\n"
            f"{AUDIO_HANDOFF}\n\n"
            "助手观察单列，不作为质量放行。采信的问题写入 draft.json 的 issue/open findings；"
            "review-save 保存同版结论。此表不是自动审片或放行回执。\n",
            encoding="utf-8")
        manifest_source = binding(studio, version)
        if manifest_source != source:
            raise ValueError("抽帧期间源版本变化，拒绝提交审查包")
        base.rename(target)
    return {**status(studio, version), "reused": False, "audio_handoff": AUDIO_HANDOFF,
            "review_inputs": review_inputs(studio, version, target, data)}


def review_inputs(studio, version, base, packet):
    audio = packet.get('audio_review')
    if audio:
        audio = {'file': str(local(base, audio['file'])), 'sha256': audio['sha256']}
    elif packet['has_audio'] and (version / 'audio.m4a').is_file():
        legacy_audio = version / 'audio.m4a'
        audio = {'file': str(legacy_audio), 'sha256': studio.digest(legacy_audio)}
    return {'full_video': {'file': str(version / 'video.mp4'),
                           'sha256': packet['source']['video_sha256']},
            'independent_full_audio': audio, 'range': [0, packet['duration_seconds']],
            'playback_speed': 1, 'aistudio_input_fps': 24, 'review_attested': False}


def evaluate(studio, version, file, *, prepared=None):
    base, packet = prepared if prepared is not None else manifest(studio, version)
    review = studio.load(file)
    if (review.get("schema") != 1 or review.get("source") != packet["source"]
            or review.get("packet_sha256") != studio.digest(base / "frames.json")):
        raise ValueError("审查结论绑定了其他版本或抽帧包")
    reviewer = review.get("reviewer", {})
    if reviewer.get("kind") not in {"ai", "human"} or not reviewer.get("name") or not reviewer.get("method"):
        raise ValueError("审查者、观察类型和实际方法必须明确")
    blockers = []
    # Sampling and playback telemetry remain useful diagnostics, not full perception.
    continuous = review.get("continuous_review", {})
    if not continuous:
        blockers.append("待审：缺同版正常速度连续全片声画观察；抽帧和播放遥测不能替代")
    elif (continuous.get("status") != "pass"
            or continuous.get("method") != {"human": "human_normal_speed", "ai": "ai_normal_speed_av"}[reviewer["kind"]]
            or continuous.get("range") != [0, packet["duration_seconds"]]
            or continuous.get("speed") != 1
            or (reviewer['kind'] == 'human' and continuous.get('limitations') != [])
            or continuous.get("video_sha256") != packet["source"]["video_sha256"]
            or continuous.get("visual_observed") is not True
            or (packet["has_audio"] and continuous.get("audio_observed") is not True)):
        blockers.append("待审：连续视听范围、速度、同版绑定或感知能力不满足完整审阅")
    else:
        checked_evidence(studio, base, continuous)
        limitation = continuous_observation(studio, version, base, packet, reviewer, continuous)
        if limitation:
            blockers.append(limitation)
    frames = review.get("frames", [])
    if [f.get("file") for f in frames] != [f["file"] for f in packet["frames"]]:
        raise ValueError("审查未逐一覆盖本次全片抽帧")
    requirements = review.get("requirements", [])
    if [r.get("text") for r in requirements] != packet["requirements"]:
        raise ValueError("审查遗漏原始需求")
    checks = review.get("checks", [])
    if len(checks) != len(LAYERS) or {c.get("layer") for c in checks} != LAYERS:
        raise ValueError("审查须区分视觉、内容、连续播放、真实听审")
    for item in [*frames, *requirements, *checks]:
        state = item.get("status")
        if state not in {"pending", "pass", "issue", "not_applicable"}:
            raise ValueError("审查状态无效；看过不等于通过")
        if state == "not_applicable":
            if item.get("layer") != "listening" or packet["has_audio"]:
                raise ValueError("只有经探测无音轨才可免听审")
        elif state == "pending":
            blockers.append(f"待审：{item.get('layer', item.get('file', '需求'))}")
        else:
            checked_evidence(studio, base, item)
            if state == "issue":
                blockers.append(f"存在问题：{item.get('layer', item.get('file', '需求'))}")
        if "layer" in item and item.get("range") != [0, packet["duration_seconds"]]:
            raise ValueError("分层审查必须声明完整成片范围，局部通过不能替代全片")
    findings = review.get("findings")
    if not isinstance(findings, list):
        raise ValueError("须保留缺陷清单")
    ids = set()
    for finding in findings:
        key = finding.get("id")
        if not isinstance(key, str) or not key.strip() or key in ids:
            raise ValueError("缺陷ID缺失或重复")
        ids.add(key)
        if finding.get("status") not in {"open", "resolved"}:
            raise ValueError("缺陷必须明确未解决或已解决")
        checked_evidence(studio, base, finding)
        if finding["status"] == "open":
            blockers.append(f"未解决缺陷：{key}")
    user_rejections = [review["user_rejection"]] if "user_rejection" in review else []
    # Previous findings must remain explicit, even when a subsequent observer disagrees.
    for old in sorted(base.glob("r[0-9][0-9][0-9][0-9].json")):
        previous = studio.load(old)
        if any(f["id"] not in ids for f in previous.get("findings", [])):
            raise ValueError("新审查遗漏历史缺陷；须逐项保留并附解决证据")
        if "user_rejection" in previous and previous["user_rejection"] not in user_rejections:
            user_rejections.append(previous["user_rejection"])
    for rejection in user_rejections:
        checked_evidence(studio, base, rejection)
        if rejection.get("video_sha256") != packet["source"]["video_sha256"]:
            raise ValueError("用户否决须绑定所反馈的确切成片")
    if user_rejections:
        blockers.insert(0, "用户已否决本版成片")
    blockers.sort(key=lambda message: 0 if message.startswith("未解决缺陷") else
                  1 if message.startswith("存在问题") else 2)
    incomplete = any(message.startswith('待审') for message in blockers)
    return {"status": "blocked" if blockers else "reviewed", "blockers": blockers,
            "review_completion": "incomplete" if incomplete else "complete",
            "quality_status": "unverified" if incomplete else "issues" if blockers else "pass",
            "observation_scope": ("ai_full_video_24fps_and_independent_full_audio" if reviewer['kind'] == 'ai'
                                  and not incomplete else "human_normal_speed" if reviewer['kind'] == 'human'
                                  and not incomplete else "incomplete"),
            "source": packet["source"], "reviewer": reviewer,
            "observation_limits": continuous.get('limitations', ['No complete observation record']),
            "verified_here": "binding_coverage_and_recorded_decisions_only",
            "user_acceptance": "rejected" if user_rejections else "not_implied", "packet": str(base)}


def save(studio, version, file):
    report = evaluate(studio, version, file)
    base = folder(studio, version)
    existing = sorted(base.glob("r[0-9][0-9][0-9][0-9].json"))
    number = int(existing[-1].stem[1:]) + 1 if existing else 1
    target = base / f"r{number:04d}.json"
    studio.save(target, studio.load(file))
    return {**report, "record": str(target)}


def status(studio, version, *, prepared=None):
    try:
        base, packet = prepared if prepared is not None else manifest(studio, version)
        records = sorted(base.glob("r[0-9][0-9][0-9][0-9].json"))
        if not records:
            return {"status": "pending", "review_completion": "incomplete",
                    "blockers": ["缺少实际审查结论"], "packet": str(base)}
        return {**evaluate(studio, version, records[-1], prepared=(base, packet)), "record": str(records[-1])}
    except (OSError, ValueError, KeyError, TypeError) as error:
        return {"status": "pending", "review_completion": "incomplete",
                "blockers": [f"缺少有效同版审查：{error}"]}


def require(studio, version):
    brief_path = version / "brief.json"
    brief = studio.load(brief_path) if brief_path.is_file() else {}
    if (brief.get("content_format") == "knowledge-song"
            and brief.get("production_stage") == "representative"):
        raise ValueError("知识歌曲代表段只供诊断，不能作为整片通过交付审查")
    report = status(studio, version)
    if report["status"] != "reviewed":
        complete = report.get('review_completion') == 'complete'
        raise ValueError(("审阅已完成，质量交付被阻止：" if complete else "质量交付被阻止：")
                         + "；".join(report["blockers"][:8])
                         + ("。须修复实际问题后复审；保留版可查看，但不标记为合格。" if complete else
                            "。先 review-prepare / review-save；待审原片可诊断预览。"))
    return report
