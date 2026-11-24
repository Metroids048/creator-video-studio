"""Photo-led films on the existing Vibe route; no provider or model calls."""
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import wave

IDS = {"photo-beat-montage", "tape-photo-essay"}


def validate(data):
    if data.get("template") not in IDS or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", data.get("id", "")):
        raise ValueError("无效图片模板或作品ID")
    if data.get("format", "9:16") not in {"9:16", "16:9"}:
        raise ValueError("图片模板只支持已重排的9:16或16:9")
    if type(data.get("frames")) is not int or not 150 <= data["frames"] <= 3600:
        raise ValueError("片长需为150–3600整数帧")
    end = 0
    for item in data.get("scenes", []):
        if item.get("start") != end or type(item.get("end")) is not int or item["end"] - end < 12:
            raise ValueError("图片段需连续，且每张至少12帧")
        if not item.get("photo") or not item.get("credit") or not item.get("license"):
            raise ValueError("每张图片需原文件、署名与许可")
        if len(item.get("caption", "")) > 26 or len(item.get("label", "")) > 12:
            raise ValueError("图文短句不超过26字，页签不超过12字")
        if any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1 for v in item.get("anchor", [.5, .5])) or len(item.get("anchor", [.5, .5])) != 2:
            raise ValueError("图片焦点需两个0–1坐标")
        if item.get("mirror", "none") not in {"none", "x", "xy"}:
            raise ValueError("镜像只能为none、x或xy")
        if item.get("fit", "cover") not in {"cover", "contain"}:
            raise ValueError("照片展示方式只能为cover或contain")
        maximum = min(12, (item["end"] - end) // 4)
        transition = item.get("transitionFrames", min(5, maximum))
        if type(transition) is not int or not 0 <= transition <= maximum:
            raise ValueError("转场需整数帧且保留至少一半清晰展示")
        end = item["end"]
    if len(data.get("scenes", [])) < 3 or end != data["frames"]:
        raise ValueError("至少三段图片，时间线需覆盖整片")
    if data["template"] == "photo-beat-montage":
        beats = data.get("beatFrames", [])
        if not beats or any(type(v) is not int for v in beats) or beats != sorted(set(beats)) or beats[0] < 0 or beats[-1] >= end:
            raise ValueError("卡点需递增的整数节拍帧")
        if any(s["start"] not in beats for s in data["scenes"]):
            raise ValueError("换图必须落在绑定的音乐节拍帧")
    if not data.get("audio", {}).get("path") or not data["audio"].get("credit") or not data["audio"].get("license"):
        raise ValueError("图片音乐模板需实际音轨和来源许可")


def prepare(data, output, root, base):
    from video_templates import check_binding, sha
    validate(data)
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("保留已准备目录，请使用新目录")
    dims = (1080, 1920) if data.get("format", "9:16") == "9:16" else (1920, 1080)
    binding = {"id": data["template"], "version": "1", "direction": data["direction"], "known_unresolved_issues": []}
    check_binding({"route": "code", "template": binding, "width": dims[0], "height": dims[1],
                   "shots": [{"kind": "code", "engine": "vibe", "sceneAsset": "scene"}]}, root)
    # Read and verify all supplied files before creating an output directory.
    photos = [(Path(base) / s["photo"]).resolve().read_bytes() for s in data["scenes"]]
    from PIL import Image
    import io
    for content in photos:
        with Image.open(io.BytesIO(content)) as image:
            if image.format not in {"JPEG", "PNG"}:
                raise ValueError("图片需为实际JPEG或PNG文件")
            image.verify()
    audio = (Path(base) / data["audio"]["path"]).resolve()
    audio_bytes = audio.read_bytes()
    with wave.open(str(audio)) as sound:
        if sound.getframerate() != 48000 or sound.getnframes() != data["frames"] * 1600:
            raise ValueError("音乐需48kHz WAV，长度与画面整数帧完全一致")
    renderer = (root / "templates/photo-sequence/scene.js").read_text()
    font = root / "runtime/vibe/fonts/LXGWWenKai-Medium.ttf"
    font_bytes = font.read_bytes()
    font_license = (font.parent / "OFL-WenKai.txt").read_bytes()
    output.mkdir(parents=True)
    (output / "story.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    (output / "music.wav").write_bytes(audio_bytes)
    (output / "font.ttf").write_bytes(font_bytes)
    (output / "OFL.txt").write_bytes(font_license)
    sources = [("story", "data", "story.json"), ("music", "audio", "music.wav"),
               ("photo-font", "font", "font.ttf"), ("font-license", "data", "OFL.txt")]
    rendered = json.loads(json.dumps(data))
    for index, (scene, content) in enumerate(zip(rendered["scenes"], photos)):
        from PIL import Image
        import io
        original = Image.open(io.BytesIO(content))
        ext = ".png" if original.format == "PNG" else ".jpg"
        name, filename = f"photo-{index}", f"photo-{index}{ext}"
        (output / filename).write_bytes(content)
        sources.append((name, "image", filename))
        scene["asset"] = name
        if data["template"] == "tape-photo-essay":
            page = _collage_page(output / filename, scene, output / f"page-{index}.png", dims, root, font)
            name = f"page-{index}"
            sources.append((name, "image", page.name))
            sources.append((f"motif-{index}", "image", page.stem + "-motif.png"))
            scene["asset"] = name
    if data["template"] == "tape-photo-essay":
        vendor = root / "resources/make-tape-collage/b5b400b3"
        for path, name, asset_id in ((vendor / "LICENSE", "COLLAGE-LICENSE.txt", "collage-license"), (vendor / "scripts/compose_direct_split.py", "compose_direct_split.py", "collage-compositor")):
            (output / name).write_bytes(path.read_bytes())
            sources.append((asset_id, "data", name))
    credits = {"photos": [{k: s[k] for k in ("photo", "credit", "license")} for s in data["scenes"]], "audio": data["audio"]}
    (output / "CREDITS.json").write_text(json.dumps(credits, ensure_ascii=False, indent=2) + "\n")
    sources.append(("credits", "data", "CREDITS.json"))
    (output / "scene.js").write_text("const PHOTO_STORY = " + json.dumps(rendered, ensure_ascii=False) + ";\n" + renderer)
    sources.append(("scene", "scene", "scene.js"))
    brief = {"id": data["id"], "title": data["title"], "request": data["request"], "route": "code", "template": binding,
             "width": dims[0], "height": dims[1], "fps": 30,
             "inputs": [{"id": n, "kind": k, "path": p, "sha256": sha(output / p)} for n, k, p in sources],
             "audio": {"mode": "supplied", "asset": "music"},
             "shots": [{"id": "photos", "kind": "code", "engine": "vibe", "accent": "#97a889", "sceneAsset": "scene", "frames": data["frames"],
                        "sceneAssets": [n for n, _, _ in sources if n not in {"scene", "music"}],
                        "cues": [{"start": s["start"], "end": s["end"], "text": s["caption"]} for s in data["scenes"] if s.get("caption")]}]}
    (output / "brief.json").write_text(json.dumps(brief, ensure_ascii=False, indent=2) + "\n")
    return {"brief": str(output / "brief.json"), "template": binding, "render_started": False,
            "next": "plan_then_workflow_then_authorized_make"}


def _collage_page(photo, scene, target, dims, root, font):
    """Use the upstream print compositor; motif and caption are local editable inputs."""
    from PIL import Image, ImageDraw, ImageFont
    motif = Image.new("RGBA", (800, 650))
    draw = ImageDraw.Draw(motif)
    colors = ["#97a889cf", "#c6b99edf", "#d9a981df", "#cad3b1cf"]
    for i in range(12):
        x, y = 110 + (i % 4) * 125 + (i % 2) * 19, 125 + (i // 4) * 105
        draw.polygon([(x, y), (x+137, y-22), (x+159, y+58), (x+15, y+72)], fill=colors[i % 4])
    motif_path = target.with_name(target.stem + "-motif.png")
    motif.save(motif_path)
    script = root / "resources/make-tape-collage/b5b400b3/scripts/compose_direct_split.py"
    subprocess.run([sys.executable, str(script), "--photo", str(photo), "--motif", str(motif_path),
                    "--output", str(target), "--final-aspect", "9:16" if dims[0] < dims[1] else "16:9",
                    "--photo-fraction", ".64", "--orientation", "top-bottom" if dims[0] < dims[1] else "left-right",
                    "--photo-position", "top" if dims[0] < dims[1] else "left", "--max-crop", ".2",
                    "--crop-mode", "none" if scene.get("fit") == "contain" else "auto",
                    "--motif-position", "lower-right", "--motif-area-fraction", ".08"], check=True, stdout=subprocess.DEVNULL)
    # Type is composited after print preparation to keep the short Chinese line legible.
    image = Image.open(target).convert("RGB").resize(dims, Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(image)
    portrait = dims[0] < dims[1]
    x, y = (88, 1405) if portrait else (1280, 390)
    draw.text((x, y), scene.get("label", ""), font=ImageFont.truetype(str(font), 27 if portrait else 24), fill="#8c7f6e")
    line = scene.get("caption", "")
    width = 12 if portrait else 9
    for row, start in enumerate(range(0, len(line), width)):
        draw.text((x, y + 70 + row * 80), line[start:start+width], font=ImageFont.truetype(str(font), 50 if portrait else 43), fill="#3c443c")
    image.save(target)
    # Motif is an input of the compositor; preserve it beside the source project.
    return target


def check_inputs(brief, inputs):
    """Bind frame edits, image changes and soundtrack to the same prepared story."""
    if brief.get("template", {}).get("id") not in IDS:
        return
    try:
        story = json.loads(inputs["story"][1].read_text())
        shot = brief["shots"][0]
        line = inputs[shot["sceneAsset"]][1].read_text().splitlines()[0]
        rendered = json.loads(line.removeprefix("const PHOTO_STORY = ").removesuffix(";"))
    except (KeyError, TypeError, json.JSONDecodeError):
        raise ValueError("图片模板必须绑定可解析的故事、场景和音乐") from None
    validate(story)
    for scene in rendered["scenes"]:
        if scene.get("asset") not in shot.get("sceneAssets", []) or inputs[scene["asset"]][0] != "image":
            raise ValueError("换图或画册页未在本镜声明")
        scene.pop("asset")
    dims = (1080, 1920) if story.get("format", "9:16") == "9:16" else (1920, 1080)
    expected = [{"start": s["start"], "end": s["end"], "text": s["caption"]} for s in story["scenes"] if s.get("caption")]
    if (rendered != story or story["template"] != brief["template"]["id"]
            or len(brief["shots"]) != 1 or brief["fps"] != 30 or (brief["width"], brief["height"]) != dims
            or shot["frames"] != story["frames"] or shot.get("cues") != expected
            or brief.get("audio") != {"mode": "supplied", "asset": "music"}):
        raise ValueError("图文、换图节拍、音轨或画幅与本版故事不一致")
    with wave.open(str(inputs["music"][1])) as sound:
        if sound.getframerate() != 48000 or sound.getnframes() != story["frames"] * 1600:
            raise ValueError("本版音乐时长与图片时间线不一致")
