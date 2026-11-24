"""Nook shot adapter for the existing studio version/cache/native-bundle flow."""
import shutil
import subprocess

from nook import plan


def validate_scene(path, shot, brief):
    report = plan(path)
    if report["unresolved_constants"] or report["host_specific_paths"]:
        raise ValueError("Nook 场景配置未闭合或仍有其他宿主路径")
    config = report["literal_config"]
    if ((config["W"], config["H"], config["FPS"]) !=
            (brief["width"], brief["height"], brief["fps"])
            or abs(config["DUR"] * brief["fps"] - shot["frames"]) > 0.000001):
        raise ValueError("Nook 场景的画幅、帧率或时长与工作室镜头不一致")
    return report


def prepare(studio, shot, brief, project, native, previous=None):
    scene = studio.verified_input(brief, project, shot["sceneAsset"])
    validate_scene(scene, shot, brief)
    native.mkdir(parents=True)
    # A revision keeps its parent's engine and fonts. A later source upgrade must
    # not silently change the other properties of a picture-only revision.
    if previous is not None:
        if not (previous / "scene.py").is_file():
            raise ValueError("Nook 父版没有匹配的原生场景")
        for folder in ("scripts", "fonts"):
            shutil.copytree(previous / folder, native / folder)
        for name in ("ENGINE-LICENSE", "dependencies.lock.json"):
            shutil.copyfile(previous / name, native / name)
    else:
        source = studio.ROOT / "resources/nook-anim"
        scripts = source / "nook-anim/scripts"
        for path in sorted(scripts.rglob("*.py")):
            if path.is_symlink():
                raise ValueError("Nook 引擎快照不能包含符号链接")
            target = native / "scripts" / path.relative_to(scripts)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
        shutil.copyfile(source / "LICENSE", native / "ENGINE-LICENSE")
        shutil.copyfile(studio.ROOT / "docs/nook-macos-arm64.lock.json", native / "dependencies.lock.json")
        (native / "fonts").mkdir()
        for name in ("LXGWWenKai-Medium.ttf", "ShantellSans-VF.ttf", "MaShanZheng-Regular.ttf",
                     "OFL-WenKai.txt", "OFL-ShantellSans.txt", "OFL-MaShanZheng.txt"):
            shutil.copyfile(studio.VIBE / "fonts" / name, native / "fonts" / name)
    shutil.copyfile(scene, native / "scene.py")
    assets = {}
    for name in shot.get("sceneAssets", []):
        source = studio.verified_input(brief, project, name)
        relative = "assets/" + name + source.suffix.lower()
        (native / "assets").mkdir(exist_ok=True)
        shutil.copyfile(source, native / relative)
        assets[name] = relative
    studio.save(native / "assets.json", assets)
    studio.save(native / "shot.json", shot)
    studio.save(native.parent / "scene-source.json", {
        "engine": "nook", "asset": shot["sceneAsset"], "sha256": studio.digest(native / "scene.py"),
        "files": {p.relative_to(native).as_posix(): studio.digest(p)
                  for p in sorted(native.rglob("*")) if p.is_file()},
        "font_policy": "project substitutions with bundled OFL; docs/font-license-provenance.json",
    })


def render(studio, shot, native, target):
    """Called only after studio's production-mode guard, on an isolated cache copy."""
    from nook import runtime_environment

    env = runtime_environment()
    env.update({"PYTHONDONTWRITEBYTECODE": "1",
                "NOOKANIM_FONT_UI": str(native / "fonts/LXGWWenKai-Medium.ttf"),
                "NOOKANIM_FONT_HAND_EN": str(native / "fonts/ShantellSans-VF.ttf"),
                "NOOKANIM_FONT_HAND_ZH": str(native / "fonts/MaShanZheng-Regular.ttf")})
    # Upstream may exit zero even when FFmpeg fails. The caller must verify the
    # returned file's actual media metadata before promoting it to a cache hit.
    subprocess.run([studio.ROOT / "runtime/nook-venv/bin/python", "-B", native / "scripts/run.py",
                    "render", native / "scene.py", "video", "--out", target],
                   cwd=native, env=env, check=True)
