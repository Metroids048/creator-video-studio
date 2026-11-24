---
name: studio-template-music-score
description: 逐音符乐谱光点，完整换稿，沿现有原生制作入口调用。
---

参考原帖：https://www.douyin.com/video/7685167835231849770。

保留：完整可演奏乐谱→同一音符事件驱动演奏与双色光点→镜头沿谱行跟随→终止式与尾韵。

换稿时必须重做：完整曲谱与声部、实际演奏音轨、音符时间表、谱面排版与镜头轨迹、曲名与尾句。读取native/story.json及main.js；所有画面和时点来自新数据。notes数组同时供本地钢琴演奏和谱面，不能给不匹配的MP3贴假乐谱；目前仅白键C大调原生谱面，复杂乐谱须另适配真实记谱。更新project.json中全部changed_files哈希；经studio.py templates prepare→plan→workflow→授权make。审完整最终MP4的画面、声音、连续性与结尾，不以解码/文件存在代替审美。
