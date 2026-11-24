"""Consume verified Overlay renders as actual image/video layers, without regenerating them."""
import json
import shutil
from pathlib import Path


def compose(studio, material, background, output):
    material = Path(material).resolve(strict=True)
    background = Path(background).resolve(strict=True)
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError("保留已有版本：" + str(output))
    receipt = json.loads((material / "receipt.json").read_text())
    if receipt.get("engine") != "overlay":
        raise ValueError("visual-compose 只消费 Overlay 渲染材料")
    required = {"still.png", "material.webm", "native.zip"}
    records = {item["path"]: item["sha256"] for item in receipt["outputs"]}
    if not required <= records.keys():
        raise ValueError("需要同版 PNG、WebM 与源码 ZIP")
    for name in required:
        if studio.digest(material / name) != records[name]:
            raise ValueError("图层与原渲染回执不符：" + name)
    if not background.is_file() or background.suffix.lower() not in {
            ".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov", ".webm", ".m4v"}:
        raise ValueError("背景需为本地图片或视频")
    info = studio.probe(background)
    if not any(s.get("codec_type") == "video" for s in info["streams"]):
        raise ValueError("背景没有可读画面")
    width, height, fps, duration = (receipt[k] for k in ("width", "height", "fps", "duration"))
    if (width, height, fps) != (1920, 1080, 30) or not 0 < duration <= 600:
        raise ValueError("图层规格超出已验证范围")
    still_time = receipt["still_time"]
    if not 0 <= still_time < duration:
        raise ValueError("关键画面时刻无效")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir()  # Never replace a parent or failed candidate.
    image = background.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    bg_input = ["-loop", "1"] if image else ["-stream_loop", "-1"]
    fit = (f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
           f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=0x181c20,setsar=1")
    graph = f"[0:v]{fit},fps={fps},setpts=PTS-STARTPTS[bg];[1:v]setpts=PTS-STARTPTS[fg];[bg][fg]overlay=0:0:shortest=1"
    commands = []

    def render(*args):
        commands.append([str(a) for a in args])
        studio.run(studio.BIN / "ffmpeg", "-nostdin", "-v", "error", *args)

    render(*bg_input, "-i", background, "-c:v", "libvpx-vp9", "-i", material / "material.webm",
           "-filter_complex", graph, "-t", duration, "-an", "-c:v", "libx264", "-preset", "fast",
           "-crf", 18, "-pix_fmt", "yuv420p", "-movflags", "+faststart", output / "composite.mp4")
    # A separate lossless PNG consumes the actual transparent PNG, not a compressed video frame.
    render(*bg_input, "-ss", still_time if not image else 0, "-i", background,
           "-i", material / "still.png", "-filter_complex", f"[0:v]{fit}[bg];[bg][1:v]overlay=0:0",
           "-frames:v", 1, output / "composite.png")
    shutil.copyfile(material / "native.zip", output / "native.zip")
    inputs = [{"id": "visual-native", "kind": "native", "path": str(output / "native.zip"),
               "sha256": studio.digest(output / "native.zip")}]
    for name, kind in [("composite.png", "image"), ("composite.mp4", "video")]:
        inputs.append({"id": "visual-" + kind, "kind": kind, "path": str(output / name),
                       "sha256": studio.digest(output / name), "nativeAsset": "visual-native"})
    studio.save(output / "studio-inputs.json", {"inputs": inputs})
    result = {"schema": 1, "engine": "overlay-composite", "material": str(material),
              "material_receipt_sha256": studio.digest(material / "receipt.json"),
              "background": str(background), "background_sha256": studio.digest(background),
              "duration": duration, "still_time": still_time, "commands": commands,
              "adapter_sha256": studio.digest(Path(__file__)), "outputs": inputs,
              "quality_status": "unreviewed_material",
              "limitations": "只合成画面；背景按需循环，不保留音轨。原作品音轨继续沿锁轨入口处理。"}
    studio.save(output / "receipt.json", result)
    return result
