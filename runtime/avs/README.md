# AVS 本地配置

工作室通过 `scripts/avs.sh` 调用 AVS 的 Episode 状态与阶段合同。准备 macOS Apple Silicon、Python 3.13、Node.js 24、Chrome，以及第 6 版或更新的 FFmpeg 和 FFprobe。按根目录 README 配置这些工具，再从仓库根目录安装锁定的 AVS 依赖。

```sh
python3.13 -m venv runtime/avs-venv
runtime/avs-venv/bin/python -m pip install -r runtime/avs/requirements.macos.freeze.txt
npm ci --prefix runtime/avs
bash scripts/avs.sh runtime-check
```

如果需要直接打开 [离线动效组件](renderers/hyperframes/README.md)，按该页说明从本地 npm 依赖准备 GSAP 文件。工作室入口说明见 [阶段交接与局部返修](../../docs/阶段交接与局部返修.md)。真实 Episode 的素材与状态由使用者提供，完整媒体交付需要同版预览、审查与审批。
