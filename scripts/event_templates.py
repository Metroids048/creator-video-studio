"""Compile the two tactile templates into the existing Vibe/brief/make route.

No model calls. One integer-frame event list owns motion, captions and contact
sounds. This compiler does not judge aesthetics or claim human listening.
"""
import json
import math
from pathlib import Path
import struct
import wave


IDS = {"object-assembly", "paper-cut-story"}


def validate(data):
    if data.get("template") not in IDS:
        raise ValueError("未登记的事件模板")
    if data.get("format", "9:16") not in {"9:16", "16:9"}:
        raise ValueError("事件模板只适配9:16和16:9")
    if type(data.get("frames")) is not int or not 150 <= data["frames"] <= 1800:
        raise ValueError("frames需为150–1800的整数")
    objects = data.get("objects", [])
    names = [o.get("id") for o in objects]
    if not names or any(not isinstance(n, str) or not n for n in names) or len(set(names)) != len(names):
        raise ValueError("对象需独立ID")
    number = lambda v: type(v) in (int, float) and math.isfinite(v)
    assembly = data["template"] == "object-assembly"
    shapes = {"box", "cylinder", "torus", "sphere"} if assembly else {"key", "headphones", "flower", "seal", "card", "letter", "hidden"}
    for obj in objects:
        if obj.get("shape") not in shapes:
            raise ValueError("模板只支持登记的小物形状，不支持人物表演")
        for field in ("from", "to"):
            if len(obj.get(field, [])) != (3 if assembly else 2) or not all(number(v) for v in obj[field]):
                raise ValueError("对象位置需为有限坐标")
        if assembly and (len(obj.get("size", [])) != 3 or not all(number(v) and v > 0 for v in obj["size"])):
            raise ValueError("装配对象需三个正尺寸")
    if not 1 <= len(data.get("title", "")) <= 16 or len(data.get("subtitle", "")) > 28:
        raise ValueError("标题1–16字、副标题不超过28字；保护手机可读性")
    seen = set()
    for event in data.get("events", []):
        keys = [event.get(k) for k in ("prepare", "contact", "result", "end")]
        if (any(type(k) is not int for k in keys) or not 0 <= keys[0] < keys[1] <= keys[2] < keys[3] <= data["frames"]
                or event.get("object") not in names or not event.get("id") or event.get("id") in seen):
            raise ValueError("事件需唯一ID、有效对象及准备<接触≤结果<结束的整数帧")
        seen.add(event["id"])
        caption_frame = event.get("captionFrame", keys[2])
        if type(caption_frame) is not int or not keys[2] <= caption_frame < keys[3]:
            raise ValueError("字幕不能先于结果揭晓")
        if not event.get("caption") or len(event["caption"]) > 20:
            raise ValueError("每个结果字幕为1–20字")
        if event.get("sound") not in {"paper", "wood", "metal", "switch", "stamp"}:
            raise ValueError("事件需有已支持的实际接触音效")
    if not seen:
        raise ValueError("模板必须有实际动作事件")
    camera = data.get("camera", [])
    if (len(camera) < 2 or camera[0].get("frame") != 0 or camera[-1].get("frame") != data["frames"]
            or any(a["frame"] >= b["frame"] for a, b in zip(camera, camera[1:]))
            or any(not k.get("reason") for k in camera)):
        raise ValueError("相机需覆盖整片，按帧递增并说明观看动机")
    for key in camera:
        if assembly:
            if len(key.get("position", [])) != 3 or not all(number(v) for v in key["position"]):
                raise ValueError("相机需有限三维位置")
        elif not number(key.get("zoom")) or not .8 <= key["zoom"] <= 1.15:
            raise ValueError("纸艺相机zoom需在0.8–1.15，保护文字与主体安全区")
    return data


def check_inputs(brief, inputs):
    """Run on the existing plan/make/repair entry, against exact bound inputs."""
    if brief.get("template", {}).get("id") not in IDS:
        return
    timeline = brief.get("eventTimeline", {})
    try:
        story = json.loads(inputs[timeline["story"]][1].read_text())
        sync = json.loads(inputs[timeline["sync"]][1].read_text())
        audio = inputs[timeline["audio"]][1]
    except (KeyError, TypeError, json.JSONDecodeError):
        raise ValueError("事件模板必须绑定故事、同步表和实际音轨") from None
    validate(story)
    dims = (1080, 1920) if story.get("format", "9:16") == "9:16" else (1920, 1080)
    if (story["template"] != brief["template"]["id"] or brief["fps"] != 30
            or (brief["width"], brief["height"]) != dims or len(brief["shots"]) != 1):
        raise ValueError("故事、模板、画幅和单镜头帧时间线不一致")
    shot = brief["shots"][0]
    cues = [{"start": e.get("captionFrame", e["result"]), "end": e["end"], "text": e["caption"]}
            for e in story["events"]]
    if shot["frames"] != story["frames"] or shot.get("cues") != cues:
        raise ValueError("字幕或片长偏离故事事件，禁止提前揭晓")
    prefix = "const EVENT_STORY = " + json.dumps(story, ensure_ascii=False) + ";\n"
    if not inputs[shot["sceneAsset"]][1].read_text().startswith(prefix):
        raise ValueError("渲染场景与绑定故事不是同一版本")
    expected = [{"id": e["id"], "frame": e["contact"], "sample": e["contact"] * 1600, "kind": e["sound"]}
                for e in story["events"]]
    from video_templates import sha
    if (sync.get("fps") != 30 or sync.get("events") != expected
            or sync.get("audio_sha256") != sha(audio)
            or brief.get("audio") != {"mode": "supplied", "asset": timeline["audio"]}):
        raise ValueError("音轨、接触帧或供给音轨设置发生漂移")
    with wave.open(str(audio)) as sound:
        if (sound.getframerate(), sound.getnchannels(), sound.getnframes()) != (48000, 2, story["frames"] * 1600):
            raise ValueError("实际音轨长度或采样时间线不匹配")


def write_audio(data, target):
    """Original short contact sounds, no music/sample/provider dependencies."""
    rate = 48000
    samples = [0.] * (data["frames"] * rate // 30)
    events = []
    for index, event in enumerate(data["events"]):
        kind = event["sound"]
        length = .28 if kind in {"paper", "stamp"} else .38
        start = event["contact"] * rate // 30
        seed = index + 3109
        previous = 0.
        for n in range(int(length * rate)):
            t = n / rate
            seed = (1664525 * seed + 1013904223) & 0xffffffff
            noise = (seed / 0xffffffff * 2 - 1)
            previous += .24 * (noise - previous)
            attack = min(1., t / .0015)
            if kind == "paper":
                value = previous * math.exp(-t * 18) * .36
            elif kind == "stamp":
                value = (math.sin(t * 2 * math.pi * 160) * math.exp(-t * 32) + previous * math.exp(-t * 45)) * .24
            elif kind == "switch":
                value = (noise * math.exp(-t * 150) * .18 + math.sin(t * 2 * math.pi * 880) * math.exp(-t * 18) * .08)
            else:
                base = 290 if kind == "wood" else 720
                value = (math.sin(t * 2 * math.pi * base) * math.exp(-t * 26)
                         + .38 * math.sin(t * 2 * math.pi * base * 2.71) * math.exp(-t * 38)
                         + previous * math.exp(-t * 70)) * .22
            if start + n < len(samples):
                samples[start + n] += value * attack
        events.append({"id": event["id"], "frame": event["contact"], "sample": start, "kind": kind})
    with wave.open(str(target), "wb") as output:
        output.setparams((2, 2, rate, 0, "NONE", "not compressed"))
        output.writeframes(b"".join(struct.pack("<hh", *([round(max(-.9, min(.9, v)) * 32767)] * 2)) for v in samples))
    return events


def write_material_audio(data, target, root, profile="wyzowl-material-v1"):
    """Use pinned CC0 material sounds; align each published sync point to contact."""
    import hashlib
    recorded = profile == "kenney-recorded-v1"
    if profile not in {"wyzowl-material-v1", "kenney-recorded-v1"}:
        raise ValueError("未登记的材质音效配置")
    library = root / ("resources/kenney-recorded-sfx" if recorded else "resources/wyzowl-sfx-kit")
    catalog = json.loads((library / ("provenance.json" if recorded else "selected-sounds.json")).read_text())
    rows = ({Path(row["local"]).stem: row for row in catalog["files"] if row["local"].endswith(".wav")}
            if recorded else {row["id"]: row for row in catalog["sounds"]})
    samples = [0.] * (data["frames"] * 1600)
    used = {}

    def place(name, at, gain=1.):
        row = rows[name]
        source = library / (row["local"] if recorded else Path(row["file"]).name)
        if hashlib.sha256(source.read_bytes()).hexdigest() != row["sha256"]:
            raise ValueError("材质音效与固定来源不符：" + name)
        with wave.open(str(source)) as sound:
            width = 2 if recorded else 3
            if (sound.getframerate(), sound.getnchannels(), sound.getsampwidth()) != (48000, 1, width):
                raise ValueError("材质音效采样格式与固定来源不一致")
            raw = sound.readframes(sound.getnframes())
        sync = {"at": 0, "basis": "upstream trimmed onset"} if recorded else row["sync"]
        start = round((at - sync["at"]) * 48000)
        for n in range(len(raw) // width):
            value = int.from_bytes(raw[n * width:(n+1) * width], "little", signed=True) / (2 ** (width * 8 - 1))
            if 0 <= start + n < len(samples):
                samples[start + n] += value * gain
        used[name] = {"sha256": row["sha256"], "sync": sync}

    for event in data["events"]:
        kind, contact = event["sound"], event["contact"] / 30
        if recorded:
            # Recorded foley keeps its natural envelope; no oscillator or transient synthesis.
            name, gain = {"paper": ("book-flip", .23), "stamp": ("card-place-2", .24),
                          "wood": ("book-place", .22), "metal": ("metal-clang", .10),
                          "switch": ("card-place-1", .18)}[kind]
            if kind == "paper":
                place("cloth-2", max(event["prepare"] / 30, contact - .35), .11)
            place(name, contact, gain)
        elif kind in {"paper", "stamp"}:
            # Sliding belongs to motion; the crinkle's peak belongs to contact.
            place("foley-paper-slide", max(event["prepare"] / 30, contact - .49), 1.)
            place("foley-paper-touch", contact, .8)
        elif kind == "wood":
            place("foley-wood-slide", max(event["prepare"] / 30, contact - .58), .7)
            place("foley-wood-touch", contact)
        else:
            place("mechanical-switch-light" if kind == "switch" else "mechanical-switch-heavy", contact)
    with wave.open(str(target), "wb") as sound:
        sound.setparams((2, 2, 48000, 0, "NONE", "not compressed"))
        sound.writeframes(b"".join(struct.pack("<hh", *([round(max(-.9, min(.9, v)) * 32767)] * 2)) for v in samples))
    return {"profile": profile, "revision": catalog["revision"],
            "license": catalog["license"], "sounds": used}


def prepare(data, output, root):
    from video_templates import check_binding, sha
    validate(data)
    dimensions = (1080, 1920) if data.get("format", "9:16") == "9:16" else (1920, 1080)
    binding = {"id": data["template"], "version": "1", "direction": data["direction"], "known_unresolved_issues": []}
    check_binding({"route": "code", "template": binding, "width": dimensions[0], "height": dimensions[1],
                   "shots": [{"kind": "code", "engine": "vibe", "sceneAsset": "scene"}]}, root)
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("准备目录已存在；保留父版，使用新目录")
    template = root / "templates" / data["template"] / "v1"
    renderer = (template / "scene.js").read_text()
    dependencies = [(root / "runtime/vibe/fonts/LXGWWenKai-Medium.ttf", "event-font", "font.ttf"),
                    (root / "runtime/vibe/fonts/OFL-WenKai.txt", "font-license", "OFL.txt"),
                    (root / "resources/mg-styles/LICENSE", "mg-license", "MG-LICENSE.txt")]
    if data["template"] == "object-assembly":
        vendor = root / "sources/zh-explainer/assets/three-0.181.2"
        dependencies += [(vendor / "build/three.module.min.js", "three-module", "three.module.min.js"),
                         (vendor / "build/three.core.min.js", "three-core", "three.core.min.js"),
                         (vendor / "LICENSE", "three-license", "THREE-LICENSE.txt"),
                         (root / "resources/mg-styles/demos/03-isometric/js/anim.js", "motion", "motion.mjs")]
    # Read all dependencies before any mutation.
    blobs = [(name, filename, path.read_bytes()) for path, name, filename in dependencies]
    output.mkdir(parents=True)
    (output / "story.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    (output / "scene.js").write_text("const EVENT_STORY = " + json.dumps(data, ensure_ascii=False) + ";\n" + renderer)
    for name, filename, content in blobs:
        (output / filename).write_bytes(content)
    events = write_audio(data, output / "events.wav")
    (output / "event-sync.json").write_text(json.dumps({"fps": 30, "events": events, "audio_sha256": sha(output / "events.wav"), "listening": "not-performed"}, indent=2))
    sources = [("scene", "scene", "scene.js"), ("story", "data", "story.json"),
               ("event-audio", "audio", "events.wav"), ("event-sync", "data", "event-sync.json")]
    sources += [(name, "data", filename) for name, filename, _ in blobs]
    inputs = [{"id": name, "kind": kind, "path": filename, "sha256": sha(output / filename)} for name, kind, filename in sources]
    brief = {"id": data["id"], "title": data["title"], "request": data["request"], "route": "code", "template": binding,
             "width": dimensions[0], "height": dimensions[1], "fps": 30, "inputs": inputs,
             "audio": {"mode": "supplied", "asset": "event-audio"},
             "eventTimeline": {"story": "story", "sync": "event-sync", "audio": "event-audio"},
             "shots": [{"id": "tactile", "kind": "code", "engine": "vibe", "accent": "#8b9a7a", "sceneAsset": "scene", "frames": data["frames"],
                        "sceneAssets": [name for name, _, _ in sources if name not in {"scene", "event-audio"}],
                        "cues": [{"start": e.get("captionFrame", e["result"]), "end": e["end"], "text": e["caption"]} for e in data["events"]]}]}
    (output / "brief.json").write_text(json.dumps(brief, ensure_ascii=False, indent=2) + "\n")
    return {"brief": str(output / "brief.json"), "template": binding, "render_started": False,
            "next": "plan_then_workflow_then_authorized_make"}
