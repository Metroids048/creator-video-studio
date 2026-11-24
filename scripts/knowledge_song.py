"""The same early editorial evidence contract for Studio and the V13 launcher."""
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess


STAGE = "knowledge-song-preview"
START_STAGE = "song-start"
BIN = Path(__file__).resolve().parents[1] / ".studio/bin"
ROLES = ("rough-cut", "opening", "mechanism", "ending")
QUALITY = {
    "vocal": ("rough-cut", "演唱与配乐"),
    "progression": ("rough-cut", "信息推进与副歌重复"),
    "sync": ("rough-cut", "关键词听辨与声画同步"),
    "hook": ("opening", "开头吸引力与主体辨识"),
    "mechanism": ("mechanism", "因果、方向与遮挡"),
    "continuity": ("ending", "动作、接触与跨镜连续性"),
    "payoff": ("ending", "结尾回收"),
}


def file_digest(path):
    with path.open("rb") as stream:
        sha = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(block)
        return sha.hexdigest()


def required(brief):
    return (brief.get("content_format") == "knowledge-song"
            and brief.get("production_stage") != "representative")


def check_diagnostic_scope(brief):
    if brief.get("content_format") != "knowledge-song" or brief.get("production_stage") != "representative":
        return
    fps = brief.get("fps")
    shots = brief.get("shots")
    if (brief.get("route", "code") != "code" or type(fps) not in (int, float) or not math.isfinite(fps) or fps <= 0
            or not isinstance(shots, list) or not shots
            or any(not isinstance(shot, dict) or type(shot.get("frames")) is not int
                   or shot["frames"] <= 0 for shot in shots)
            or sum(shot["frames"] for shot in shots) > 12 * fps):
        raise ValueError("知识歌曲代表段制作限 12 秒代码时间轴；整片须先确认 " + START_STAGE)


def soundtrack(brief):
    if brief.get("route") == "native-knowledge":
        spec = json.loads((Path(brief["native_root"]) / "composition.json").read_text())
        asset = spec.get("assets", {}).get("approved-audio", {})
        frozen = brief["native_inputs"]["files"].get(asset.get("file"))
        if frozen and frozen == asset.get("sha256"):
            return frozen, sum(shot["frames"] for shot in spec["shots"]) / spec["fps"]
    elif brief.get("route") == "editor":
        for item in brief.get("inputs", []):
            if item["id"] == brief.get("primary") and item.get("sha256"):
                return item["sha256"], None
    elif brief.get("audio", {}).get("mode") == "supplied":
        for item in brief.get("inputs", []):
            if item["id"] == brief["audio"]["asset"] and item.get("sha256"):
                return item["sha256"], sum(shot["frames"] for shot in brief["shots"]) / brief["fps"]
    raise ValueError("知识歌曲整片须先冻结实际歌曲输入及 SHA256")


def media_duration(ffprobe, path, role):
    probe = subprocess.run([str(ffprobe), "-v", "error", "-show_entries",
                            "format=duration:stream=codec_type,duration", "-of", "json", path],
                           capture_output=True, text=True)
    if probe.returncode:
        raise ValueError("知识歌曲预审素材无法探测：" + role)
    info = json.loads(probe.stdout)
    duration = float(info.get("format", {}).get("duration", 0))
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("知识歌曲预审素材无有效时长：" + role)
    tracks = {kind: [] for kind in ("audio", "video")}
    for stream in info.get("streams", []):
        kind = stream["codec_type"]
        if kind in tracks:
            tracks[kind].append(float(stream.get("duration", duration)))
    if not all(tracks.values()):
        raise ValueError("知识歌曲预审素材须含画面和音轨：" + role)
    # Ranges must be observable with both tracks, even if the container lasts longer.
    return min(duration, *(max(lengths) for lengths in tracks.values()))


def evidence_file(root, ref, label, *, media=False):
    if not isinstance(ref, dict) or not isinstance(ref.get("file"), str):
        raise ValueError("缺少听辨或对标证据：" + label)
    path = (root / ref["file"]).resolve()
    if ((not media and not path.is_relative_to(root)) or not path.is_file()
            or file_digest(path) != ref.get("sha256")):
        raise ValueError("听辨或对标证据已变更或缺失：" + label)
    return path


def compare_dimensions(comparison, dimensions, failures):
    for key, label in dimensions.items():
        row = comparison.get(key, {}) if isinstance(comparison, dict) else {}
        observation = row.get("observation", "") if isinstance(row, dict) else ""
        if not isinstance(observation, str) or not observation.strip():
            failures.append(label + "缺与同一基准的具体比较")
        elif row.get("status") != "comparable":
            failures.append(label + "未达对标（" + observation.strip() + "）")


def audio_seconds(path):
    probe = subprocess.run([str(BIN / "ffprobe"), "-v", "error", "-select_streams", "a:0",
                            "-show_entries", "stream=duration", "-of", "csv=p=0", path],
                           capture_output=True, text=True)
    try:
        duration = float(probe.stdout.strip())
    except ValueError:
        duration = 0
    if probe.returncode or not math.isfinite(duration) or duration <= 0:
        raise ValueError("听辨输入须有可读的实际音轨：" + str(path))
    return duration


def pcm_digest(path):
    layout = subprocess.run([str(BIN / "ffprobe"), "-v", "error", "-select_streams", "a:0",
                             "-show_entries", "stream=sample_rate,channels", "-of", "csv=p=0", path],
                            capture_output=True, text=True)
    decode = subprocess.run([str(BIN / "ffmpeg"), "-nostdin", "-v", "error", "-i", path,
                             "-map", "0:a:0", "-c:a", "pcm_s16le",
                             "-f", "hash", "-hash", "sha256", "-"],
                            capture_output=True, text=True)
    if (layout.returncode or not re.fullmatch(r"\d+,\d+", layout.stdout.strip())
            or decode.returncode or not re.fullmatch(r"SHA256=[a-f0-9]{64}", decode.stdout.strip())):
        raise ValueError("听辨同源校验无法解码：" + str(path))
    return layout.stdout.strip(), decode.stdout.strip()


def audio_audition(path, *, required_mix=None, required_media=None, required_reports=(),
                   editorial=None, singing_method=None, required_reference=None, short=False):
    """Check blind lyric recognition separately from audio-based listening."""
    from song_listening import check as check_listening

    path = path.resolve(strict=True)
    report = json.loads(path.read_text())
    if not isinstance(report, dict):
        raise ValueError("首听报告须为 JSON 对象")
    mix = evidence_file(path.parent, report.get("mix"), "实际混音", media=True)
    mix_hash = report["mix"]["sha256"]
    if required_mix is not None and mix_hash != required_mix:
        raise ValueError("首听记录与本次冻结混音不一致")
    if required_media is not None and mix != required_media and pcm_digest(mix) != pcm_digest(required_media):
        raise ValueError("首听混音与代表段样片实际音轨不同源")
    duration = audio_seconds(mix)
    if short and not 6 <= duration <= 12.05:
        raise ValueError("开工验证须使用 6–12 秒的实际混音短样")
    reference = evidence_file(path.parent, report.get("reference"), "对标原片", media=True)
    if reference == mix or report["reference"]["sha256"] == mix_hash:
        raise ValueError("听辨候选与要求的对标原片必须分别观察")
    if required_reference and report["reference"]["sha256"] != required_reference:
        raise ValueError("听审对标与开工验证基准不一致")
    if singing_method and report.get("singing_method_sha256") != singing_method:
        raise ValueError("首听未绑定开工已验证的唱法，变更须先重开 " + START_STAGE)
    if singing_method:
        run = report.get("method_run")
        if (not isinstance(run, dict) or run.get("method_sha256") != singing_method
                or run.get("mix_sha256") != mix_hash):
            raise ValueError("缺唱法实际运行与本版混音的绑定")
        source = evidence_file(path.parent, run.get("source"), "唱法实际运行回执")
        if not source.stat().st_size:
            raise ValueError("唱法运行回执为空")
    targets = report.get("targets")
    if not isinstance(targets, list) or not targets:
        raise ValueError("首听前须标记承载内容的关键字句及时间窗")
    normalized = []
    for target in targets:
        if not isinstance(target, dict):
            raise ValueError("首听关键词须有明确文字与有效时间窗")
        forms = target.get("forms", [])
        window = target.get("range")
        start, end = window if isinstance(window, list) and len(window) == 2 else (None, None)
        if (not isinstance(forms, list) or not forms
                or any(not isinstance(form, str) or not re.fullmatch(r"[\u3400-\u9fff]+", form) for form in forms)
                or type(start) not in (float, int) or type(end) not in (float, int)
                or not 0 <= start < end <= duration + 0.12):
            raise ValueError("首听关键词须有明确文字与有效时间窗")
        normalized.append((forms, start, end))
    if short and (len({forms[0] for forms, _, _ in normalized}) < 2
                  or len({(start, end) for _, start, end in normalized}) < 2):
        raise ValueError("开工短样须标记开场与最难咬字的不同关键句及时间窗")

    failures = []
    listening = None
    try:
        captured = evidence_file(path.parent, report.get("listening_source"), "经盲测校准的实际听审")
        listening = check_listening(captured, mix, reference)
    except (OSError, ValueError) as error:
        failures.append(str(error))
    observers = report.get("observations")
    if not isinstance(observers, list) or len(observers) < 2:
        raise ValueError("实际混音须保留至少两路独立盲辨的原始回执")
    engines = set()
    files = set()
    for ref in observers:
        source = evidence_file(path.parent, ref, "混音盲辨")
        rows = [json.loads(line) for line in source.read_text().splitlines() if line.strip()]
        engine = ref.get("observer")
        if (not isinstance(engine, str) or not engine.strip() or engine in engines
                or ref["sha256"] in files):
            raise ValueError("混音盲辨须来自不同观察方法及原始回执")
        engines.add(engine)
        files.add(ref["sha256"])
        input_hash = mix_hash
        if "decoded_input" in ref:
            decoded = evidence_file(path.parent, ref["decoded_input"], "混音同源解码")
            if pcm_digest(decoded) != pcm_digest(mix):
                raise ValueError("盲辨使用的解码音轨与实际混音不同源")
            input_hash = ref["decoded_input"]["sha256"]
        valid = []
        for row in rows:
            if (not isinstance(row, dict) or row.get("sha256") != input_hash
                    or row.get("reference_provided") is not False):
                continue
            start_at, length = row.get("start"), row.get("duration")
            if start_at is None and length is None and ref.get("extent") == "full_file":
                start_at, length = 0, duration
            if (type(start_at) in (float, int) and type(length) in (float, int)
                    and 0 <= start_at < start_at + length <= duration + 0.12
                    and isinstance(row.get("text"), str)):
                valid.append((start_at, start_at + length, re.sub(r"[\W_]+", "", row["text"])))
        for forms, start, end in normalized:
            candidates = [transcript for a, b, transcript in valid if a <= start and b >= end]
            if not any(form in transcript for transcript in candidates for form in forms):
                failures.append(f"{engine} 在 {start:g}–{end:g} 秒未稳定辨出「{forms[0]}」")
    if any(digest not in files for digest in required_reports):
        failures.append("遗漏已保留的本版混音交叉盲辨结果")
    if editorial is not None:
        if not isinstance(editorial, dict) or editorial.get("reference_sha256") != report["reference"]["sha256"]:
            failures.append("画面叙事与混音须使用同一基准，明确对照开头、推进和结尾")
        else:
            compare_dimensions(editorial, {
                "hook": "开头看点", "progression": "新增信息及镜头推进", "payoff": "结尾回收",
            }, failures)
    if failures:
        prefix = "知识歌曲预审未通过：" if editorial is not None else "知识歌曲混音首听未通过："
        raise ValueError(prefix + "；".join(failures))
    return {"mix_sha256": mix_hash, "reference_sha256": report["reference"]["sha256"],
            "observers": sorted(engines), "checked_targets": len(normalized),
            "listening": listening, "verified": "blind_lyrics_and_calibrated_listening_receipts",
            "render_started": False}


def review_start(artifacts, brief):
    if len(artifacts) != 2:
        raise ValueError("知识歌曲开工须依次绑定唱法配置和本版短样首听报告")
    method, audition = artifacts
    spec = json.loads(Path(method["path"]).read_text())
    if (not isinstance(spec, dict) or spec.get("project") != brief["id"]
            or not all(isinstance(spec.get(key), str) and spec[key].strip()
                       for key in ("engine", "version", "voice", "approach"))
            or not isinstance(spec.get("settings"), dict) or not spec["settings"]):
        raise ValueError("开工须冻结本作品的新唱法、引擎版本、声源和关键参数")
    return audio_audition(Path(audition["path"]), singing_method=method["sha256"], short=True)


def check_repaired_vocal(brief, report_path, sync, mixed_hash):
    if brief.get("route") != "native-knowledge":
        return
    spec = json.loads((Path(brief["native_root"]) / "composition.json").read_text())
    dry = spec["assets"].get("dry-vocal")
    if dry is None:
        return
    dry_hash = brief["native_inputs"]["files"].get(dry.get("file"))
    if not dry_hash or dry_hash != dry.get("sha256") or dry_hash == mixed_hash:
        raise ValueError("知识歌曲返修干声未冻结，或与成品音轨相同")
    blind = sync.get("blind_check") if isinstance(sync, dict) else None
    if not isinstance(blind, dict):
        raise ValueError("知识歌曲返修缺同版干声及混音的关键词盲辨回执")
    root = report_path.resolve().parent
    for role, media_hash in (("dry", dry_hash), ("mixed", mixed_hash)):
        evidence = blind.get(role)
        if not isinstance(evidence, dict) or not isinstance(evidence.get("file"), str):
            raise ValueError("知识歌曲返修缺关键词盲辨来源：" + role)
        path = (root / evidence["file"]).resolve()
        if not path.is_relative_to(root) or not path.is_file() or file_digest(path) != evidence.get("sha256"):
            raise ValueError("知识歌曲返修关键词盲辨回执已变更或缺失：" + role)
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        if not any(isinstance(row, dict) and row.get("sha256") == media_hash
                   and row.get("reference_provided") is False
                   and isinstance(row.get("text"), str) and row["text"].strip() for row in rows):
            raise ValueError("知识歌曲返修关键词盲辨未绑定本版音轨：" + role)
    if blind.get("unresolved") != []:
        raise ValueError("知识歌曲返修关键词仍有未解决的听辨分歧，或缺分歧记录")


def review(artifacts, brief, *, singing_method=None, required_reference=None):
    if len(artifacts) != 5:
        raise ValueError("知识歌曲预审须依次绑定观察 JSON、全曲粗剪、开头、最难机制、回收四份视频")
    report_path = Path(artifacts[0]["path"])
    report = json.loads(report_path.read_text())
    if not isinstance(report, dict) or report.get("open_issues") != []:
        raise ValueError("知识歌曲预审仍有未关闭问题，或缺 open_issues 清单")
    checks = report.get("checks")
    if not isinstance(checks, dict) or checks.keys() != set(ROLES):
        raise ValueError("知识歌曲预审缺阶段观察")
    quality = report.get("quality")
    if not isinstance(quality, dict) or quality.keys() != QUALITY.keys():
        raise ValueError("知识歌曲预审缺独立质量观察项：" + "、".join(label for _, label in QUALITY.values()))
    if len({asset["sha256"] for asset in artifacts[1:]}) != len(ROLES):
        raise ValueError("四项预审须使用各自的实际视频")
    source_hash, expected_duration = soundtrack(brief)
    if report.get("source_audio_sha256") != source_hash:
        raise ValueError("知识歌曲预审音轨未绑定实际冻结的歌曲输入")
    check_repaired_vocal(brief, report_path, quality["sync"], source_hash)
    audition = evidence_file(report_path.parent, report.get("audio_audition"), "混音首听及基准对照")
    sync = quality["sync"]
    blind = sync.get("blind_check", {}) if isinstance(sync, dict) else {}
    if not isinstance(blind, dict) or not isinstance(blind.get("crosscheck_mix", {}), dict):
        raise ValueError("本版交叉盲辨记录无效")
    retained = [blind.get("mixed"), blind.get("earlier_mixed"), blind.get("crosscheck_mix", {}).get("report")]
    if any(ref is not None and (not isinstance(ref, dict) or not isinstance(ref.get("sha256"), str))
           for ref in retained):
        raise ValueError("本版交叉盲辨记录缺原始文件指纹")
    editorial = report.get("editorial_comparison")
    audio_audition(audition, required_mix=source_hash,
                   required_reports=[ref["sha256"] for ref in retained if ref is not None],
                   singing_method=singing_method,
                   required_reference=required_reference,
                   editorial=editorial if isinstance(editorial, dict) else {})
    ffprobe = Path(__file__).resolve().parents[1] / ".studio/bin/ffprobe"
    durations = {}
    for role, media in zip(ROLES, artifacts[1:]):
        row = checks[role]
        if (not isinstance(row, dict) or row.get("media_sha256") != media["sha256"]
                or row.get("status") != "pass"
                or not all(isinstance(row.get(key), str) and row[key].strip()
                           for key in ("timecode", "observation"))):
            raise ValueError("知识歌曲预审需同版通过和具体观察：" + role)
        durations[role] = media_duration(ffprobe, media["path"], role)
    if expected_duration is not None and abs(durations["rough-cut"] - expected_duration) > 0.12:
        raise ValueError("知识歌曲全曲粗剪时长与本次制作时间轴不一致")

    failures = []
    for name, (role, label) in QUALITY.items():
        row = quality[name]
        if not isinstance(row, dict):
            failures.append(label + "缺观察记录")
            continue
        start, end = row.get("start"), row.get("end")
        observation = row.get("observation")
        if (type(start) not in (float, int) or type(end) not in (float, int)
                or not 0 <= start < end <= durations[role]
                or not isinstance(observation, str) or not observation.strip()):
            failures.append(label + "缺素材内时间与具体观察")
            continue
        if name == "vocal" and row.get("delivery") != "sung":
            failures.append(label + "未证实歌曲演唱，节奏念白或待核不能放行")
        elif row.get("status") != "pass":
            failures.append(label + "未通过（" + observation.strip() + "）")
    if failures:
        raise ValueError("知识歌曲预审质量未就绪：" + "；".join(failures))
