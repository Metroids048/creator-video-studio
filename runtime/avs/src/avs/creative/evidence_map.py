"""Build and validate the narration -> fact -> asset -> ROI trace."""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import jsonschema

_SCHEMA = Path(__file__).resolve().parents[3] / "schemas" / "evidence-map.schema.json"


def _asset_is_continuous(asset: dict[str, Any], ref: dict[str, Any]) -> bool:
    marker = ref.get("continuous_recording", asset.get("continuous_recording"))
    metadata = asset.get("metadata") or {}
    if marker is None:
        marker = metadata.get("continuous_recording")
    if marker is not None:
        return bool(marker)
    return asset.get("source_type") in {"recording"} or metadata.get("source_type") == "recording"


def _copy_temporal_contract(ref: dict[str, Any], asset: dict[str, Any], requested_duration: float) -> None:
    start = ref.get("source_start")
    end = ref.get("source_end")
    if start is None and end is None:
        if _asset_is_continuous(asset, ref):
            raise ValueError(f"{ref.get('asset_id')} 是连续录屏，必须提供完整 source_start/source_end")
        return
    if start is None or end is None:
        raise ValueError("source_start/source_end 必须成对提供")
    try:
        start_f, end_f = float(start), float(end)
    except (TypeError, ValueError) as exc:
        raise ValueError("source_start/source_end 必须为 float seconds") from exc
    if not math.isfinite(start_f) or not math.isfinite(end_f) or start_f < 0 or end_f <= start_f:
        raise ValueError("source_start 必须 >= 0 且 source_end 必须 > source_start")
    duration = asset.get("duration") or (asset.get("metadata") or {}).get("duration")
    if duration is not None and end_f > float(duration) + 1e-6:
        raise ValueError(f"source_end={end_f} 超过素材时长 {duration}")
    if abs((end_f - start_f) - requested_duration) > 0.01:
        raise ValueError(
            f"源区间时长 {end_f - start_f:.3f}s 与 segment duration {requested_duration:.3f}s 不匹配"
        )
    ref["source_start"] = start_f
    ref["source_end"] = end_f


def build_evidence_map(
    episode_id: str,
    script: dict[str, Any],
    *,
    intelligence: dict[str, Any],
) -> dict[str, Any]:
    by_id = {asset["asset_id"]: asset for asset in intelligence.get("assets", [])}
    known = set(by_id)
    segments: list[dict[str, Any]] = []
    for segment in script.get("segments", []):
        refs = []
        for raw_ref in segment.get("asset_refs", []):
            ref = dict(raw_ref)
            asset = by_id.get(ref.get("asset_id"), {})
            source_type = asset.get("metadata", {}).get("source_type")
            if source_type:
                ref["source_type"] = source_type
            elif asset.get("source_type"):
                ref["source_type"] = asset["source_type"]
            _copy_temporal_contract(ref, asset, float(segment.get("duration_seconds", 1.0)))
            refs.append(ref)
        if segment.get("evidence_required"):
            if not refs or any(ref.get("asset_id") not in known for ref in refs):
                raise ValueError(f"{segment.get('segment_id')} 缺少真实素材证据")
        segments.append({
            "segment_id": segment["segment_id"],
            "spoken_text": segment.get("spoken_text", segment.get("text", "")),
            "purpose": segment.get("purpose", ""),
            "duration_seconds": float(segment.get("duration_seconds", 1.0)),
            "evidence_required": bool(segment.get("evidence_required", False)),
            "asset_refs": refs,
            "reference_pattern_ids": list(segment.get("reference_pattern_ids", [])),
        })
    result = {"episode_id": episode_id, "segments": segments}
    jsonschema.Draft7Validator(json.loads(_SCHEMA.read_text(encoding="utf-8"))).validate(result)
    return result
