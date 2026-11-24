---
name: studio-template-watercolor-music
description: 将真实演唱的逐句歌词变为水彩场景、对象与动作，按完整新视觉稿换稿。
---

当前调用工程为同目录 `native-lyrics/`，从《送别》v0004冻结复制；旧 `native/` 和36秒器乐稿保留历史，不用于证明歌词能力。先读 project.json、story.json、main.js、draw.js。主题与完整文案由Codex读懂，歌曲已有真实演唱，逐句含义映射具体对象、动作和跨句情绪关系，再与演唱时点绑定。不能把字幕贴在静态背景上或用器乐替代歌曲。

当前完整新视觉稿：长亭/古道→芳草→柳树→夕阳→远舟→故人→酒杯→月夜。成片 `works/lyrics-songbei-1114/versions/v0004/video.mp4`，55秒16:9，SHA256 `bc2e4834478a9cbf9a2aa9e320f7bdcd09e042ed9c866a4647ac02f49eb9c32f`。这是117秒原录音16–71秒的完整一节，不是整首。工程ZIP和brief位于同版目录。音源信息见本套 music-source.json；图书馆公开可听不代表取得公开传播许可。

新稿输入：主题、完整歌词及视觉稿、实际演唱音轨、逐句时间表、目标画幅。执行 `studio.py intent '<主题>' --script-file <全文>` 和 `templates match '<主题>' --script-file <全文> --format 16:9`。本套市场仅1/2，不进入默认高流量生产首选；已授权工程验证使用development模式 `templates match ... --purpose engineering_validation --select studio-watercolor-music --save <新选择.json>`。复制native-lyrics到新任务，重写main.js/story.json的场景、动作、关系和时间，更新project.json.content_promise及changed_files哈希，将选择回执放入story.routing，经prepare→plan/workflow→已授权make，不覆盖父版。

音轨更换必须重新对齐，不能复制《送别》的时间。当前首句约6.64秒起，后段“知交半零落”37.5秒、“一壶浊酒”42.7秒、“今宵别梦寒”49秒，均为本音源本截取范围；已知歌词强制对齐不等于独立识别。看完整输出、听完整实际音轨，分别记录视觉、音频感知与播放范围。

v1→v2修演唱起点，v2→v3改7–13秒重复开头，v3→v4改芳草近景、柳枝拂水、友人渐散和透明叠化；父版及失败保留。v0004完整2fps与关键帧已看、实际音轨AI感知和1x播放已做，薄层水彩与人物表现仍有差距，连续视觉及最终质量待验，不能据解码或模型分数宣布验收。

市场参考：https://www.douyin.com/video/7690199228575960339 ，632,835赞；第二条同形式≥20万赞仍缺。若卿书法道具技术流和像素歌词片是独立分支，不能借填本套双对标。仅16:9；无真实手部表演、书法操作或真人连续性能力。
