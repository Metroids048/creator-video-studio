"""Synthetic review contracts for unit tests; never real-video quality evidence."""
import video_review


def reviewed_contract(studio, version):
    base = video_review.folder(studio, version)
    base.mkdir(parents=True, exist_ok=True)
    for name in ("frame0.png", "frame1.png", "fixture.txt"):
        (base / name).write_text("synthetic contract fixture, not a viewed video")
    frames = [{"file": f"frame{i}.png", "at": i / 2, "sha256": studio.digest(base / f"frame{i}.png")}
              for i in range(2)]
    packet = {"schema": 1, "source": video_review.binding(studio, version), "duration_seconds": 1,
              "fps": 2, "has_audio": True, "requirements": ["contract requirement"],
              "frames": frames, "artifacts": {"fixture.txt": studio.digest(base / "fixture.txt")}}
    studio.save(base / "frames.json", packet)
    observed = {"status": "pass", "observation": "synthetic contract only",
                "evidence": {"fixture.txt": studio.digest(base / "fixture.txt")}}
    review = {"schema": 1, "source": packet["source"], "packet_sha256": studio.digest(base / "frames.json"),
              "reviewer": {"kind": "human", "name": "synthetic human fixture, no real observer", "method": "synthetic contract"},
              "frames": [{"file": f["file"], **observed} for f in frames],
              "requirements": [{"text": "contract requirement", **observed}],
              "checks": [{"layer": layer, "range": [0, 1], **observed} for layer in sorted(video_review.LAYERS)],
              "findings": []}
    studio.save(base / 'attestation.json', {'source': packet['source'], 'observer': review['reviewer']['name'],
        'method': 'human_normal_speed', 'range': [0, 1], 'speed': 1, 'limitations': [],
        'modalities': ['visual', 'audio'], 'statement': 'Synthetic schema fixture; no real video or human observation.'})
    review["continuous_review"] = {**observed, "method": "human_normal_speed", "range": [0, 1],
        "speed": 1, "limitations": [], "video_sha256": packet["source"]["video_sha256"],
        "visual_observed": True, "audio_observed": True, 'attestation': 'attestation.json',
        'evidence': {'attestation.json': studio.digest(base / 'attestation.json')}}
    studio.save(base / "draft.json", review)
    video_review.save(studio, version, base / "draft.json")
    return base, review
