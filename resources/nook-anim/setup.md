# Nook 本地配置

需要 Apple Silicon Mac、Python 3.13 和 [工作室根目录配置](../../README.md)中的 FFmpeg。

```sh
python3.13 -m venv runtime/nook-venv
python3.13 -c 'import json; print("\n".join(x["name"] + "==" + x["version"] for x in json.load(open("docs/nook-macos-arm64.lock.json"))))' \
  | runtime/nook-venv/bin/python -m pip install -r /dev/stdin
```

将 LXGW WenKai Medium、Shantell Sans Variable 和 Ma Shan Zheng Regular 分别保存为 `runtime/vibe/fonts/LXGWWenKai-Medium.ttf`、`runtime/vibe/fonts/ShantellSans-VF.ttf` 和 `runtime/vibe/fonts/MaShanZheng-Regular.ttf`，同时保留各字体的许可说明。运行 `python3 scripts/nook.py check` 核对引擎版本与字体，使用 `python3 scripts/nook.py plan <scene.py>` 检查场景接口。Nook 的 [源码许可](LICENSE)随仓库提供。
