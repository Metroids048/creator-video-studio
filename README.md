# 视频制作工作室

把脚本、参考形式和素材整理成可追溯的视频工程。工作室会根据内容匹配模板、生成分镜与可编辑工程，制作后保留素材哈希、版本和审查记录。局部返修可以从父版接续，只替换受影响的镜头或音轨。

## 快速开始

需要 Python 3.10+、Node.js 24，以及带有 `libx264` 的 FFmpeg 和 FFprobe。先把本机工具接到工作室的固定入口，再查看可用路线。这几条命令不会下载媒体或调用模型。

```sh
mkdir -p .studio/bin
ln -s "$(command -v node)" .studio/bin/node
ln -s "$(command -v ffmpeg)" .studio/bin/ffmpeg
ln -s "$(command -v ffprobe)" .studio/bin/ffprobe
python3 scripts/studio.py doctor
python3 scripts/studio.py templates list
python3 scripts/studio.py templates match '纸墨地形，讲一次练习如何带来反馈' --purpose engineering_validation
```

## 运行纸墨地形样例

仓库包含三段分镜、场景源码和 Vibe 渲染器。准备 Node.js 24 和本地 Chrome，然后在仓库根目录运行 `npm install --prefix runtime/vibe`。如果 Chrome 安装在其他位置，用 `CHROME_PATH` 指定可执行文件。

在 `runtime/vibe/fonts/` 放入 `SmileySans-Oblique.ttf` 和 `OFL-SmileySans.txt`。在 `runtime/lanshu-fonts/notoserifsc/` 放入 Noto Serif SC 可变字体与 `OFL.txt`。字体来源和校验信息见 [字体许可](docs/font-license-provenance.json)和 [Noto 下载清单](docs/lanshu-font-downloads.json)。

在仓库根目录操作，新一轮使用新的样例目录。

```sh
mkdir -p samples/paperink
python3 - <<'PY'
import json
from pathlib import Path

example = Path("templates/paper-ink-landscape/v1/example.json")
story = json.loads(example.read_text())
script = "\n".join(scene["caption"] for scene in story["scenes"]) + "\n"
Path("samples/paperink/script.txt").write_text(script)
PY

topic='paper-ink-landscape 纸墨地形 16:9，给总在囤积课程的上班族做一段成年人学习方法短片，先练习一次再根据反馈决定学什么。'
python3 scripts/studio.py --mode development templates match "$topic" \
  --script-file samples/paperink/script.txt --select paper-ink-landscape \
  --purpose engineering_validation --save samples/paperink/selection.json

python3 - "$topic" <<'PY'
import json
from pathlib import Path
import sys

sample = Path("samples/paperink")
story = json.loads(Path("templates/paper-ink-landscape/v1/example.json").read_text())
story.update(topic=sys.argv[1], script=(sample / "script.txt").read_text(),
             routing=json.loads((sample / "selection.json").read_text()))
(sample / "story.json").write_text(json.dumps(story, ensure_ascii=False))
PY

python3 scripts/studio.py --mode development templates prepare samples/paperink/story.json \
  --to samples/paperink/prepared
python3 scripts/studio.py plan samples/paperink/prepared/brief.json
python3 scripts/studio.py --mode production make samples/paperink/prepared/brief.json
python3 scripts/studio.py status paperink-feedback-example
python3 scripts/studio.py inspect-bundle works/paperink-feedback-example/versions/v0001/editable.zip
```

样例生成 12 秒无声视频。初版在 `works/paperink-feedback-example/versions/v0001/`，含成片、封面、字幕、可编辑工程包和制作回执。审查保留待完成状态，完成同版审查后才能交付。

## 本地剪辑与可选引擎

专注计时器示例展示保留片段、插入静帧、增加音轨和字幕。前两条命令安装锁定的剪辑依赖并生成测试图形和音频。第三条命令验证时间线方案。

```sh
npm ci --prefix runtime/editor
bash examples/make-focus-media.sh
python3 scripts/studio.py plan examples/briefs/focus.json
```

- AVS 的 Python 源码、Episode 合同、分阶段入口及本地动效模板随仓库提供。按 [AVS 本地配置](runtime/avs/README.md) 安装后，用 `bash scripts/avs.sh runtime-check` 核对运行条件。
- Nook 的场景引擎随仓库提供。按 [Nook 本地配置](resources/nook-anim/setup.md) 安装依赖和字体，再运行 `python3 scripts/nook.py check`。

## 代码与文档

- `scripts/studio.py` 提供路由、制作、恢复、返修和交付入口。 `adapters/` 对接各路线的渲染器和编辑器。
- `runtime/vibe/` 包含逐帧渲染入口，`runtime/editor/lib/` 包含剪辑路线使用的时间线、转场规则和媒体渲染。剪辑路线执行 `npm ci --prefix runtime/editor` 安装锁定依赖。
- `templates/` 提供模板清单、场景源码和匹配规则。[能力清单](docs/capability-index.json)列出了各路线所需的本地依赖。
- `.agents/skills/`、`docs/制作配方/` 和 [阶段交接与局部返修](docs/阶段交接与局部返修.md)记录从选题到交付的操作约定。
- 历史成片、原始素材、生成结果、已安装运行时和本地凭据由使用者在本地管理。

工作室自身代码采用 MIT。随附组件按各自目录的许可使用。
