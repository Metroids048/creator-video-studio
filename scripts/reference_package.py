"""Read an existing rea-video package; never run its code, models or remake jobs."""
import hashlib
import json
from pathlib import Path


TOPICS = ("timeline", "content", "cast", "sound", "look", "packaging", "remake")


def inspect(package, topic=None, shot=None):
    if topic is not None and shot is not None:
        raise ValueError("参考主题与单镜读取须择一")
    root = Path(package).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("参考拆片包须为本地目录；视频链接先沿工作室研究流程取得证据")

    def file_record(name, include_text=False, required=False):
        path = root / name
        if not path.exists():
            if required:
                raise ValueError(f"参考拆片包缺少 {name}")
            return None
        path = path.resolve(strict=True)
        if root not in path.parents or not path.is_file():
            raise ValueError(f"参考拆片文件越出包目录或不是文件：{name}")
        raw = path.read_bytes()
        return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(),
                **({"text": raw.decode("utf-8")} if include_text else {})}

    card = file_record("VIDEO.md", required=True)
    data = file_record("breakdown.json", include_text=True, required=True)
    b = json.loads(data.pop("text"))
    if not isinstance(b, dict) or not isinstance(b.get("tool"), dict) or b["tool"].get("name") != "rea-video":
        raise ValueError("仅支持 rea-video 的实际 breakdown.json，不将普通稿件当拆片包")
    source, analysis, shots = b.get("source"), b.get("analysis"), b.get("shots")
    if not isinstance(source, dict) or not isinstance(analysis, dict) or not isinstance(shots, list):
        raise ValueError("参考拆片包缺少 source / analysis / shots")
    if not all(isinstance(row, dict) and type(row.get("index")) is int for row in shots):
        raise ValueError("参考镜头缺少整数 index")
    if len({row["index"] for row in shots}) != len(shots):
        raise ValueError("参考镜头 index 重复")
    vlm = analysis.get("vlm") or {}
    if not isinstance(vlm, dict):
        raise ValueError("参考模型状态格式错误")
    fallbacks = [{"shot": row["index"], "fallback": row["vlm"]["_fallback"]}
                 for row in shots if isinstance(row.get("vlm"), dict) and row["vlm"].get("_fallback")]
    files = [record for name in (f"video/{part}.md" for part in TOPICS)
             if (record := file_record(name))]
    selected = None
    if topic is not None:
        if topic not in TOPICS:
            raise ValueError("未知参考主题")
        selected = file_record(f"video/{topic}.md", include_text=True, required=True)
    elif shot is not None:
        row = next((row for row in shots if row["index"] == shot), None)
        if row is None:
            raise ValueError(f"参考包中不存在镜头 {shot}")
        selected = {"shot": row, "file": file_record(f"video/shots/{shot:02d}.md", include_text=True, required=True)}
    else:
        selected = file_record("VIDEO.md", include_text=True, required=True)
    consumed = selected["file"] if shot is not None else selected
    return {
        "package": str(root), "producer": b["tool"], "card": card, "breakdown": data,
        "source_recorded": source, "source_media_verified": False,
        "source_hash_scope": "breakdown.sha256_head 仅源文件前64MiB；本入口不读取其外部source.path，也不将其当全文件校验",
        "shot_count": len(shots), "files": files, "selected": selected,
        "observation": {"producer_vlm": vlm, "shot_fallbacks": fallbacks,
                        "whole_response_present": bool(b.get("whole_video_vlm")),
                        "complete_av_verified": False,
                        "limitation": "生产者状态及回答不证明完整音轨已被感知；按完整视听记录另核，静音/图片降级不算完整音画"},
        "handoff": {"artifacts": list(dict.fromkeys([card["path"], data["path"], consumed["path"]])),
                    "use": "由Codex将实际消费的主题/单镜文件加入原workflow阶段artifacts；不创建新任务、不自动确认阶段",
                    "adaptation": "原片秒数仅为参考；新歌词与定版音轨通过现有content_adaptation及scene-context交给镜头"},
        "model_request_sent": False, "render_started": False, "state_written": False,
    }
