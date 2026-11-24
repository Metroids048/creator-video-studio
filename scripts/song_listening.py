"""Check source-bound audio review and a blind calibration from the same listener."""
import hashlib
import json
import math
from pathlib import Path
from random import SystemRandom
import struct
import subprocess
import wave


SCHEMA = "song-listening/v1"
DIMENSIONS = ("vocal", "arrangement")
RATE = 16000
BYTES_PER_SECOND = RATE * 2
FFMPEG = Path(__file__).resolve().parents[1] / ".studio/bin/ffmpeg"


def pcm_sha256(pcm):
    return hashlib.sha256(pcm).hexdigest()


def listening_pcm(path, start=0, seconds=None):
    bounds = ["-ss", str(start), "-t", str(seconds)] if seconds is not None else []
    result = subprocess.run([str(FFMPEG), "-nostdin", "-v", "error", "-i", str(path),
                             *bounds, "-map", "0:a:0", "-ac", "1", "-ar", str(RATE),
                             "-f", "s16le", "-"], capture_output=True)
    if result.returncode or not result.stdout:
        raise ValueError("实际听审输入无法解码：" + str(path))
    return result.stdout


def muted_reference(pcm, start, end):
    left, right = (round(seconds * RATE) * 2 for seconds in (start, end))
    return pcm[:left] + bytes(right - left) + pcm[right:]


def audible_reference(pcm, start, end):
    left, right = (round(seconds * RATE) * 2 for seconds in (start, end))
    return all(any(abs(value) >= 128 for (value,) in struct.iter_unpack("<h", pcm[pos:pos + RATE]))
               for pos in range(left, right - RATE + 1, RATE))


def prepare(mix, reference, output, start, seconds):
    if not (number(start) and start >= 0 and number(seconds) and 6 <= seconds <= 12):
        raise ValueError("对标区间须在原片内取 6–12 秒")
    candidate = listening_pcm(mix)
    baseline = listening_pcm(reference, start, seconds)
    if abs(len(baseline) / BYTES_PER_SECOND - seconds) > 0.05:
        raise ValueError("实际听审对标区间超出原片")
    rng = SystemRandom()
    starts = [step / 4 for step in range(4, int((seconds - 3.5) * 4) + 1)
              if audible_reference(baseline, step / 4, step / 4 + 2.5)]
    if not starts:
        raise ValueError("对标原音在可用区间内缺持续可听信号，请选另一实际片段")
    mute_at = rng.choice(starts)
    bounds = [mute_at, mute_at + 2.5]
    samples = [candidate, baseline, muted_reference(baseline, *bounds)]
    if len({pcm_sha256(clip) for clip in samples}) != 3:
        raise ValueError("实际混音、干净对标和盲测对照须各有不同的音频")
    rng.shuffle(samples)
    output.mkdir()
    rows = []
    for index, pcm in enumerate(samples, 1):
        identifier = f"input-{index:02}"
        with wave.open(str(output / (identifier + ".wav")), "wb") as stream:
            stream.setparams((1, 2, RATE, 0, "NONE", "not compressed"))
            stream.writeframes(pcm)
        rows.append({"id": identifier, "pcm_sha256": pcm_sha256(pcm), "response": None})
    capture = {"schema": SCHEMA, "listener": None, "speed": 1, "reference_start": start,
               "reference_seconds": seconds, "control_mute": bounds, "samples": rows, "pair_response": None}
    path = output / "capture-template.json"
    path.write_text(json.dumps(capture, ensure_ascii=False, indent=2) + "\n")
    return {"inputs": [str(output / (row["id"] + ".wav")) for row in rows],
            "capture_template": str(path), "model_request_sent": False, "render_started": False}


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def note(value):
    return (isinstance(value, str) and len(value.strip()) >= 4
            and value.strip().lower().rstrip("。.!") not in
            {"不确定", "无法判断", "无法听出", "未能听出", "unclear", "unknown", "not sure"})


def raw_object(raw):
    if isinstance(raw, str):
        try:
            obj = json.loads(raw)
        except ValueError:
            obj = None
        if isinstance(obj, dict):
            return obj
    raise ValueError("实际听审缺可核查的原始结构化回执")


def check(report_path, mix, reference):
    report = json.loads(report_path.read_text())
    if not isinstance(report, dict) or report.get("schema") != SCHEMA:
        raise ValueError("实际听审回执协议无效")
    listener = report.get("listener")
    if (not isinstance(listener, dict) or listener.get("kind") not in {"human", "audio-model"}
            or not isinstance(listener.get("endpoint"), str) or not listener["endpoint"].strip()
            or type(report.get("speed")) not in (int, float) or report["speed"] != 1):
        raise ValueError("实际听审须有真人或音频评审端的原速回执")
    start, seconds = report.get("reference_start"), report.get("reference_seconds")
    if (not number(start) or start < 0 or not number(seconds) or not 6 <= seconds <= 12):
        raise ValueError("实际听审缺对标原片内 6–12 秒的定位")
    candidate = listening_pcm(mix)
    baseline = listening_pcm(reference, start, seconds)
    if abs(len(baseline) / BYTES_PER_SECOND - seconds) > 0.05:
        raise ValueError("实际听审对标区间超出原片")
    bounds = report.get("control_mute")
    if (not isinstance(bounds, list) or len(bounds) != 2 or not all(map(number, bounds))
            or not 1 <= bounds[0] < bounds[1] <= seconds - 1 or bounds[1] - bounds[0] < 2):
        raise ValueError("实际听审缺对标音频内的静音盲测设置")
    if not audible_reference(baseline, *bounds):
        raise ValueError("听审静音对照须从本来有可听信号的区间生成")
    control = muted_reference(baseline, *bounds)
    expected = [pcm_sha256(clip) for clip in (candidate, baseline, control)]
    if len(set(expected)) != 3:
        raise ValueError("实际混音、干净对标和盲测对照须各有不同的音频")
    rows = report.get("samples")
    if (not isinstance(rows, list) or len(rows) != 3
            or any(not isinstance(row, dict) or not isinstance(row.get("pcm_sha256"), str)
                   or not isinstance(row.get("id"), str) or not row["id"].strip() for row in rows)
            or len({row["id"] for row in rows}) != 3
            or {row["pcm_sha256"] for row in rows} != set(expected)):
        raise ValueError("实际听审回执与本版混音、对标原音或静音对照不同源")
    by_hash = {row["pcm_sha256"]: row for row in rows}
    mix_row, clean_row, muted_row = (by_hash[digest] for digest in expected)
    clean = raw_object(clean_row.get("response"))
    muted = raw_object(muted_row.get("response"))
    if "silence" not in clean or clean["silence"] is not None:
        raise ValueError("听审校准失败：干净对标被误判静音或未作答")
    detected = muted.get("silence")
    if (not isinstance(detected, list) or len(detected) != 2
            or not all(number(x) and abs(x - y) <= 0.75 for x, y in zip(detected, bounds))
            or detected[1] - detected[0] < 1):
        raise ValueError("听审校准失败：未辨出盲测对照内已知静音区间")

    for label, row, duration in (("实际混音", mix_row, len(candidate) / BYTES_PER_SECOND),
                                 ("对标原音", clean_row, seconds)):
        response = raw_object(row.get("response"))
        for dimension in DIMENSIONS:
            detail = response.get(dimension)
            if (not isinstance(detail, dict) or not number(detail.get("time"))
                    or not 0 <= detail["time"] < duration or not note(detail.get("observation"))):
                raise ValueError(label + "缺音频端可定位的主唱或编曲观察")
    pair = raw_object(report.get("pair_response"))
    if (pair.get("candidate") != mix_row["id"] or pair.get("reference") != clean_row["id"]):
        raise ValueError("听感对比原始回执须绑定同一候选与对标输入")
    for dimension, label in zip(DIMENSIONS, ("主唱听感", "编曲听感")):
        judgement = pair.get(dimension)
        if not isinstance(judgement, dict) or not note(judgement.get("observation")):
            raise ValueError(label + "缺实际对照判断")
        if judgement.get("status") != "comparable":
            raise ValueError(label + "未达对标：" + judgement["observation"])
    return {"endpoint": listener["endpoint"], "kind": listener["kind"]}
